# Ad Pulse: budgets, frequency caps, exactly-once counting and ranking

This is the design of the parts of Ad Pulse that involve money. It was written before
the code, reviewed, and then corrected to match what was built. Where the build differs
from the first plan, it says so and why.

## 1. Why this work

Before it, Ad Pulse served ads and counted clicks and renders, but:

- Budgets were stored and never checked. An ad kept serving after it had spent its budget.
- Frequency caps were stored and never checked.
- A click or render could be counted more than once. Pub/Sub delivers at least once and
  can redeliver a message even after it was acked
  ([Pub/Sub docs](https://docs.cloud.google.com/pubsub/docs/exactly-once-delivery)), and a
  real tracking URL could be opened again and counted again.
- Ranking was a sort on `adpriority` alone. Price played no part.

Reading the code also found bugs the new work depended on. Each was checked by running
it, not by reading alone:

| Bug | Effect |
|---|---|
| The dashboard sent budget and bid as strings (`"10"`, or `""` when left empty) | Go could not decode the ad and skipped it. No ad created in the dashboard ever served |
| With no ad unit picked, the dashboard sent `ad_unit_targeted: [[]]` | The same decode failure |
| The whole campaign list was decoded as one value | One unreadable campaign made every ad request a 500 |
| The dashboard offered hours 1 to 24, the server compared against 0 to 23 | Hour 24 never matched, hour 0 could not be chosen |
| Flight dates were typed in local time and read as UTC | A campaign set in Denver ran 6 or 7 hours off |

The manager validated none of this, so any shape was stored and failed later, silently, in
another service.

## 2. Goals and non-goals

Goals:

1. Every billable event is counted exactly once, including replays and redeliveries.
2. An ad or campaign stops serving once it has spent its budget, with a stated bound on overspend.
3. Daily budgets are spread over the day.
4. Per-user frequency caps are enforced.
5. Ads compete on price within a priority.
6. The serve path stays as fast as before or gets faster, measured.
7. Bad input is refused at the manager with a 400 that names the field.

Non-goals, decided before building:

- **No overspend at all.** That needs a reservation at serve time, settled or released
  later. Google Ads lets a day spend up to twice its daily budget and caps the month instead
  ([Google Ads help](https://support.google.com/google-ads/answer/1704443?hl=en)). A stated
  bound is the normal trade.
- **Caps across all users** (`userCap: false`). That is a delivery limit, and the budget
  already limits delivery. Refused at validation.
- **CPD pricing.** Nothing charges per event under CPD, so budgets and eCPM have nothing to
  work with. Refused at validation and removed from the dashboard.
- **More than one currency.** USD only, because nothing converts currencies.
- **A learned click model.** CPC ads use a smoothed rate from their own counts (section 7).
- **Multi-region.**

## 3. The flow

```
ad request (user.id)
   |
   v
ad-server-svc
   1. filter by flight dates and targeting (dates parsed once, when the ad was decoded)
   2. budget check: one MGET of spend for every budgeted ad and campaign
   3. frequency caps: one pipelined ZCOUNT round trip, only if a candidate has a cap
   4. rank: priority, then eCPM, from a heap
   5. price = the bid (first price). The signed iid carries the bid id, price, bid type,
      serve time, and for a capped ad the user id and its counters
   |
   v
adpulse-engagement-svc: check the signature, refuse an ad served over 24 h ago or in the future, publish
   |
   v
Pub/Sub (at least once)
   |
   v
adpulse-engagement-subscriber-svc
   record: insert inbox record "<click or render>:<bid id>" with its ad, campaign, serve
           time and price   <- the _id already exists: a duplicate
           add the event to the user's cap counters, then ack
   fold, a loop, in one MongoDB transaction per batch of up to 1,000 recorded events:
           $inc each report row and each spend total (in nanos) once for the whole batch
           mark the events folded
           commit, then copy the new spend totals to Redis
```

ad-manager-svc's cache job, every 15 seconds, also puts each CPC ad's clicks and renders
into its cached JSON, for ranking.

## 4. Exactly-once counting

**Event identity.** The ad server puts the bid's id in the signed iid. Both tracking URLs of
a bid carry it, so an event's id is its type plus the bid id, and one served bid can count
for at most one click and one render. The iid is signed, so none of it can be changed by
the browser. It is also URL-escaped: base64 can contain `+`, which a query string reads as a
space.

**Recording.** The subscriber inserts each event into an `inbox` collection with the event id
as its `_id`, along with what the event adds: its ad, campaign, serve time and price. A
second copy fails on the unique `_id`, so a replay or a redelivery is never recorded twice.
The insert happens before the ack, so if the worker dies in between, the redelivery finds
the record and is only acked. Recording writes one new document per event and nothing else.

**Folding.** A loop takes up to 1,000 recorded events that are not folded yet, oldest first,
and in one MongoDB transaction adds them up, applies one `$inc` per report row and spend
total, and marks them folded. An event is counted only by the transaction that marks it:

| Failure | What happens |
|---|---|
| A fold fails before its commit | Nothing was written. The next fold takes the same events |
| Two folds pick the same events | They collide on those records. One commits, the other retries without them |
| A fold commits, then copying to Redis fails | MongoDB is right. The next fold of that ad copies the totals |

PyMongo's `with_transaction` may run its callback again after a transient error such as a
write conflict, so the callback only writes inside the transaction.

**Why two steps, a change found by the load test.** The first build did the dedupe, the count
and the spend in one transaction per event. Every event of a busy ad then updated the same
few documents, so concurrent events conflicted and retried, about 4 attempts each, and one
hot ad could be counted at only 65 events a second. Recording plus folding takes the conflict
out of the path every event goes through: an insert never conflicts with another event's
insert, and a fold of 1,000 events touches each total once. Section 10 has both
measurements. Records written by the first build have no `folded` field, so a fold never
picks them up: they were counted when they were written.

MongoDB has to be a replica set, because a standalone server does not run transactions
([MongoDB docs](https://www.mongodb.com/docs/manual/core/transactions-production-consideration/)).
Compose, the local Kubernetes manifests and CI run a one-member set. Production should run
three. The subscriber checks at startup and exits if it is not one.

**Bounded memory.** Inbox records expire after 72 hours through a TTL index. The engagement
service refuses an event served more than 24 hours ago, and the subscriber only counts an
event served less than 48 hours ago. An event is counted at or after its serve time, so its
record lasts until at least 72 hours after it, and any copy that arrives later is more than
48 hours old and refused. So no event is counted twice. The 24 hours between the limits
cover clock skew. The cost is that an event stuck in a backlog for over 48 hours is dropped,
and `subscriber_events_total{result="too_old"}` shows it.

## 5. Budgets and pacing

**Money** is integer **nanos** inside the system (a thousandth of a micro). The first plan
said micros. Nanos were chosen while building because a CPM render costs a thousandth of
the bid: with micros, a $0.0015 CPM bid would be charged 1 micro a render instead of 1.5.
The JSON API keeps decimal dollars. Go reads them with `big.Rat` straight from the JSON text,
never through a float. Validation caps amounts at 1,000,000,000 with at most 6 decimals,
which keeps nanos far inside an int64.

**Price.** The auction is first price, the model Google Ad Manager moved to in 2019. A CPM
render costs bid / 1000, and a CPC click costs the bid. The price and bid type are fixed in
the signed iid at serve time, so editing a bid never re-prices events already served.

**Where spend lives.** MongoDB holds the record: four `spend` documents per ad (ad and
campaign, overall and for the UTC serve day), added to by the fold. After each fold commits,
the new totals go to Redis through a Lua script that only ever raises a value. Totals only
grow, so the larger value is right whatever order two copies arrive in. The script compares
the values as text, because Lua numbers are doubles and lose whole numbers past 2^53 nanos,
about $9 million. If a copy fails, or Redis loses the totals, the ad reads as having spent
less than it has, so it keeps serving, and the fold of its next event writes the true totals
back.

**The check.** Before ranking, the ad server reads the spend of every budgeted candidate in
one `MGET`. Unbudgeted ads cost no read. It skips an ad if the ad or its campaign has spent
its total or today's budget, or is ahead of pace: today's spend above the daily budget times
the share of the day gone by, plus an hour. Pacing uses a float, since it is a target, not
money. An unreadable spend value stops only its own ad.

**Overspend bound.** Spend is recorded when the render or click arrives, so the ad keeps
serving while its last events are in flight:

```
overspend <= price per event x events in flight
events in flight ~= the ad's serve rate x (time until the render or click + pipeline delay)
```

`subscriber_serve_to_count_seconds` measures the pipeline delay. The bound only holds while
the subscriber keeps up: section 10 has a load test where the first build fell behind and
spent 368% over budget, and the same test after the change, at 7.9%. A reservation at serve
time would bring overspend near zero whatever the delay.

## 6. Frequency caps

The request's OpenRTB `user.id` is the user, and the server used to drop it while decoding.
A cap counts `CSC` (renders) or `CLK` (clicks) of an ad, or of any ad in a campaign, in a
window of at most a week, with `maxCount` of at most 1,000.

**Counting** uses a sliding window log: a Redis sorted set per user, entity and event type,
`fc:<AD|CAMPAIGN>:<id>:<CSC|CLK>:<user>`, with the bid id as the member and the serve time as
the score. That was chosen over counters:

| | Fixed window counter | Sliding window log |
|---|---|---|
| Exact | No, up to 2x across a window edge | Yes |
| Redelivered event | Counted twice | No change: same member, same score |
| Memory | One number | One entry per event, bounded below |

Each set drops events more than a week older than its newest one, keeps at most 1,000, and
expires 8 days after its last write. Those are the longest window and the highest count the
manager accepts, so trimming never changes an answer.

**Only capped ads feed counters.** The ad server puts the user id and the counters an event
feeds, such as `AD:CSC`, in the signed iid of capped ads only. Other ads' URLs carry no user
id, and Redis memory grows only with capped traffic.

**The check** counts every window of every remaining capped ad with `ZCOUNT` in one pipelined
round trip. This is a second round trip after the budget's `MGET`, and only when a candidate
has a cap. The first plan had one shared read. Merging them would have meant reworking the
budget code for about 0.2 ms, and that trade was not worth it. A capped ad is not sent to a
request with no user id (or one over 128 characters), because the cap can't be checked. Caps
lag by the same pipeline delay as spend. If Redis loses the sets, caps start again from zero,
which is accepted: caps protect the user, they are not billing.

## 7. Ranking

Priority first, lowest number first, the way Google Ad Manager puts guaranteed deals ahead of
open competition ([Ad Manager help](https://support.google.com/admanager/answer/177279)).
Then eCPM, highest first. Then ad id, so the order never changes.

```
CPM:  eCPM = bid
CPC:  eCPM = bid x expected CTR x 1000
expected CTR = (clicks + 0.01 x 100) / (renders + 100)
```

The rate is the mean of a Beta prior of 1% worth a hundred renders: a new ad starts at the
prior and its own record takes over. The first plan had the subscriber copy counts to Redis
for the ad server to read. Built instead: ad-manager-svc's cache job adds each CPC ad's
clicks and renders from MongoDB to its cached JSON every refresh. That costs no read on the
serve path, and 15 seconds is fresh enough for a rate. If MongoDB is down, those ads rank on
the prior. A known weakness: an ad whose rate starts low gets few renders and may not recover.
A small share of exploration traffic would fix it, and is not built.

**Speed.** Profiling showed ranking (`sort.SliceStable` moving 344-byte ads) at 22% of a
request and date parsing at 15%. Now candidates go into a heap, built in O(n), and the bidder
takes the best one left in O(log n) only while it has slots to fill, usually one or two of
hundreds. Dates are parsed once when an ad is decoded. Old and new builds, run in turn on one
machine, medians of four:

| | before | sorted keys | heap |
|---|---|---|---|
| 50 campaigns x 20 ads | 1.71 ms | 1.76 ms | 1.27 ms |
| the same, every ad budgeted | 2.70 ms | 2.77 ms | 2.14 ms |

Sorting small keys was the first try and made no difference. The heap is about 25% faster.

## 8. Failure handling

Every Redis call of a request shares one deadline, `REDIS_TIMEOUT` (default 100 ms). Past it
the request fails with a 500 and nothing is served. The first plan said a 204. A 500 is what
the server already answered for any Redis error, and either way nothing is served.

| Failure | Effect |
|---|---|
| Redis down or slow | No ads: requests fail inside the deadline |
| Redis lost its data | Spend reads as zero until each ad's next event: overspend as in section 5. Caps restart |
| Pub/Sub or the subscriber down | Events wait in Pub/Sub (7 day default retention). Spend stops moving, so ads keep serving: overspend grows with the outage |
| MongoDB down | The subscriber nacks and Pub/Sub redelivers. The cache job caches CPC ads without counts |
| Engagement service down | Those clicks and renders are lost. Browsers don't retry pixels. Under-billing, not over-billing |
| One unreadable ad, campaign or spend value | Only that ad stops serving |

## 9. Metrics

| Service | Metric | Labels |
|---|---|---|
| ad-server-svc, `/metrics` | `adserver_requests_total` | `result`: bid, no_bid, bad_request, error |
| | `adserver_request_duration_seconds` | histogram |
| | `adserver_ads_skipped_total` | `reason`: total_budget, daily_budget, pacing, spend_unreadable, frequency_cap, no_user_id, unusable_cap |
| adpulse-engagement-svc, `/metrics` | `engagement_events_total` | `event`: click, render. `result`: accepted, bad_signature, too_old, bad_request, publish_failed, error |
| adpulse-engagement-subscriber-svc, `:9102/metrics` | `subscriber_events_total` | `event`, `result`: recorded, duplicate, too_old, malformed, failed |
| | `subscriber_serve_to_count_seconds` | histogram, serve to folded: the pipeline delay in the overspend bound |
| | `subscriber_fold_failures_total` | folds that failed and are retried |

Every label has a fixed set of values, so no request can create a series. `duplicate` above
zero shows the exactly-once logic doing its job. `too_old` above zero, a rising
`subscriber_fold_failures_total`, or a serve-to-count delay of more than a few seconds
should alert: the last means the folds are falling behind and budgets will overshoot.

## 10. Capacity and a measured run

At 1,000 ad requests a second, every bid rendered and a 1% click rate, the pipeline carries
about 1,010 events a second. The inbox then holds 1,010 x 259,200 seconds (72 hours) = about
262 million records, roughly 40 GB with the index. That is fine for one replica set at this
project's scale and too much to ignore above it. The levers, in order: turn on Pub/Sub
exactly-once delivery so the inbox only has to cover replays, shorten the windows, or shard
the inbox by event id.

Measured with `loadtest.py` against the Compose stack on one laptop: 16 threads ask for one
CPM ad ($1 CPM, $1 total budget, so 1,000 renders) and render every ad they are served, until
it stops serving. The first build, counting each event in its own transaction, then the
same test after the change to recording and folding:

| | one transaction per event | record, then fold |
|---|---|---|
| bids before the budget stopped the ad | 4,678 over 23.9 s, 196 a second | 1,079 over 4.8 s, 226 a second |
| latency, every request | p50 57 ms, p95 74 ms, p99 88 ms | p50 52 ms, p95 63 ms, p99 67 ms |
| renders sent and counted | 4,678 and 4,678 | 1,079 and 1,079 |
| serve to counted (`subscriber_serve_to_count_seconds`) | mean 28 s, the slowest about 60 s | mean 0.8 s, all within 2 s |
| spent against the $1 budget | $4.68, **368% over** | $1.079, **7.9% over** |

Latency is mostly the Python client and Docker networking on one laptop. In both runs every
render was counted exactly once.

**What the first run found.** The overspend was far past the bound because the delay grew
to a minute: the subscriber could not keep up. Every render of the one ad updated the same
spend documents and report row inside its own transaction, so the worker threads kept
hitting write conflicts and retrying. Measured directly against the same MongoDB, 2,000
billable renders from 10 threads, before and after the change:

| | one transaction per event | record, then fold |
|---|---|---|
| all for one ad | 65 events a second, 4.23 transaction attempts each | 1,711 events a second, recorded to counted |
| spread over 2,000 ads | 280 events a second, 1.00 attempts each | 1,251 events a second |

A busy ad is now the fast case, because a batch touches each of its totals once. After the
change the overspend matches the bound: 226 bids a second with under a second of delay
allows a couple of hundred renders in flight, and 79 went over. The totals came out exact in
every run.

The first run also found that a manager answering 500 (its database dropped connections
under the load) was reported by the ad server as "publisher not found". It is now a 502.

**The same test on Google Cloud.** The chart was installed on GKE (two e2-standard-2 nodes) with
Cloud SQL Postgres, Memorystore Redis, real Pub/Sub reached through Workload Identity, and
MongoDB as a one-member replica set on a persistent disk. `integration_test.py` and
`loadtest.py` ran from a laptop against the public addresses, so the latencies include the
internet and say little about the services. It was torn down afterwards and is not running.

| | $1 budget | $5 budget, every subscriber pod force-killed 15 s in |
|---|---|---|
| bids a second | 108 | 104 |
| latency, every request | p50 59 ms, p95 79 ms, p99 132 ms | p50 64 ms, p95 109 ms, p99 198 ms |
| renders sent and counted | 1,022 and 1,022 | 5,029 and 5,029 |
| spent against the budget | $1.022, 2.2% over | $5.017, 0.3% over |

The overspend is smaller than on the laptop because the cloud stack serves fewer bids a
second, so fewer renders are in flight when the budget runs out. After the kill the count read
5,017 when the load test stopped waiting, and reached 5,029 once Pub/Sub redelivered the
messages the dead pods had not acknowledged (the ack deadline is 60 seconds). No render was
lost or counted twice. A test that checks counts after a failure has to wait longer than the
ack deadline. This is one run on small machines, not a capacity figure.

## 11. Tests that prove the guarantees

- **Exactly once:** the subscriber's tests run against a real replica set in CI. A replay
  (5 times), a redelivery after recording, and the same event on 12 threads at once are each
  counted once. A fold that fails part way leaves nothing behind, and four folds running over
  the same 600-event backlog at once count every event exactly once. Not marking events
  folded, or folding outside a transaction, makes these fail.
- **Spend:** a replay is never charged twice, 12 concurrent events of one ad add up exactly, a
  failed Redis copy is repaired by the next fold of that ad, and a later smaller total never
  wins, including past 2^53. Each of these was checked against a deliberately broken copy.
- **Caps:** the window edge to the second, per user, per campaign, no user id, and the 1,000
  event bound.
- **End to end**, through the Compose stack in CI: replayed URLs count once, an ad with a
  one-render budget stops serving after that render, and a user capped at one render an hour
  stops getting the ad while another user still does.
- **The race detector** runs on every Go test.

## 12. Delivery

Each step was built, tested and merged by itself, in this order.

| Step | Contents |
|---|---|
| 1 | Validation of the JSON fields the ad server reads, dashboard fixes, money read exactly, one bad campaign no longer fails every request |
| 2 | Exactly-once counting: bid id in the iid, age limits, the transactional inbox, MongoDB as a replica set |
| 3 | Budgets and pacing |
| 4 | Frequency caps |
| 5 | Ranking by price, the heap, dates parsed once, Redis deadlines |
| 6 | Metrics, the load test and this document |
| 7 | Recording and folding, after the load test showed a busy ad outrunning per-event transactions |

## 13. What is not built

- A reservation at serve time, which would bring overspend near zero.
- Exploration traffic for CPC ads whose rate starts low.
- Caps across all users, CPD pricing, more than one currency.
- Spend shown in the dashboard. It is in MongoDB's `spend` collection.
- A campaign form in the dashboard. Campaigns are created through the API.
- Pub/Sub exactly-once delivery, which would let the inbox shrink.
