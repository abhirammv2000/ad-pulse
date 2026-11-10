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
adpulse-engagement-subscriber-svc, in one MongoDB transaction:
   upsert inbox record "<click or render>:<bid id>"   <- already there: a duplicate, stop
   $inc the report's click or render count
   $inc spend, in nanos, for the ad and the campaign, overall and for the serve day
   commit, then copy spend to Redis, add the event to the user's cap counters, then ack
```

ad-manager-svc's cache job, every 15 seconds, also puts each CPC ad's clicks and renders
into its cached JSON, for ranking.

## 4. Exactly-once counting

**Event identity.** The ad server puts the bid's id in the signed iid. Both tracking URLs of
a bid carry it, so an event's id is its type plus the bid id, and one served bid can count
for at most one click and one render. The iid is signed, so none of it can be changed by
the browser. It is also URL-escaped: base64 can contain `+`, which a query string reads as a
space.

**The transactional inbox.** The subscriber upserts the event id into an `inbox` collection
with `$setOnInsert`, and only if it was new adds the count and the spend. All of it is one
MongoDB transaction, committed before the ack:

| Crash point | What the redelivery does |
|---|---|
| Before the commit | Nothing was written. It is counted normally |
| After the commit, before the ack | It finds the inbox record and is only acked |

PyMongo's `with_transaction` may run its callback again after a transient error such as a
write conflict, so the callback only writes inside the transaction. Redis is never touched
inside it. Two workers given the same message collide on the inbox id: one commits, the
other retries and finds it.

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

**Where spend lives.** MongoDB holds the record: four `spend` documents per event (ad and
campaign, overall and for the UTC serve day), written in the counting transaction. After the
commit, the new totals go to Redis through a Lua script that only ever raises a value. Totals
only grow, so the larger value is right whatever order two copies arrive in. The script
compares the values as text, because Lua numbers are doubles and lose whole numbers past
2^53 nanos, about $9 million. A failed copy nacks the message, and the redelivery is a
duplicate that copies again without charging twice. If Redis loses the totals, the next
event for that ad writes them back.

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

`subscriber_serve_to_count_seconds` measures the pipeline delay. The bound holds only while
the subscriber keeps up. Section 10 has a load test where one hot ad outran it and spent
368% over budget, and the cause. A reservation at serve time would bring overspend near zero
whatever the delay.

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
| adpulse-engagement-subscriber-svc, `:9102/metrics` | `subscriber_events_total` | `event`, `result`: counted, duplicate, too_old, malformed, failed |
| | `subscriber_serve_to_count_seconds` | histogram, the pipeline delay in the overspend bound |

Every label has a fixed set of values, so no request can create a series. `duplicate` above
zero shows the exactly-once logic doing its job. `too_old` above zero should alert.

## 10. Capacity and a measured run

At 1,000 ad requests a second, every bid rendered and a 1% click rate, the pipeline carries
about 1,010 events a second. The inbox then holds 1,010 x 259,200 seconds (72 hours) = about
262 million records, roughly 40 GB with the index. That is fine for one replica set at this
project's scale and too much to ignore above it. The levers, in order: turn on Pub/Sub
exactly-once delivery so the inbox only has to cover replays, shorten the windows, or shard
the inbox by event id.

Measured with `loadtest.py` against the Compose stack on one laptop: 16 threads ask for one
CPM ad ($1 CPM, $1 total budget, so 1,000 renders) and render every ad they are served, until
it stops serving.

| | |
|---|---|
| requests | 5,581 in 23.9 s of serving, 196 bids a second, then 903 answered with no bid |
| latency, every request | p50 57 ms, p95 74 ms, p99 88 ms (mostly the Python client and Docker networking on one laptop) |
| renders sent and counted | 4,678 and 4,678, so nothing was lost or counted twice |
| spent against the budget | $4.68 against $1.00: **368% over** |
| serve to counted (`subscriber_serve_to_count_seconds`) | mean 28 s, half over 30 s, the slowest about 60 s |

**What the run found.** The overspend is far past the bound's estimate because the pipeline
delay was not a second but grew to a minute. The subscriber could not keep up: every render
of this one ad updates the same four spend documents and the same report row inside a
transaction, so its worker threads keep hitting write conflicts and retrying. Measured
directly against the same MongoDB, with the subscriber's own `record_event` on 10 threads:

| 2,000 billable renders | events a second | transaction attempts per event |
|---|---|---|
| all for one ad | 65 | 4.23 |
| spread over 2,000 ads | 280 | 1.00 |

So the bound in section 5 holds only while the subscriber keeps up. One hot ad above about 65
renders a second outruns it, the backlog grows, and so does the overspend. The fix is a known
pattern and is not built yet: count in small batches, so one transaction applies many events
and their totals with one `$inc` per document, or split each hot total into shards that are
summed when read. Either keeps exactly-once, because the inbox records stay in the same
transaction as the counts.

The run also found that a manager answering 500 (its database dropped connections under the
load) was reported by the ad server as "publisher not found". It is now a 502.

## 11. Tests that prove the guarantees

- **Exactly once:** the subscriber's tests run against a real replica set in CI. A replay
  (5 times), a redelivery after the commit, and the same event on 12 threads at once are each
  counted once. A failure between the two writes leaves nothing behind. Removing the duplicate
  check, or the transaction, makes these fail.
- **Spend:** a replay is never charged twice, 12 concurrent events of one ad add up exactly, a
  failed Redis copy is repaired by the redelivery, and a later smaller total never wins,
  including past 2^53. Each of these was checked against a deliberately broken copy.
- **Caps:** the window edge to the second, per user, per campaign, no user id, and the 1,000
  event bound.
- **End to end**, through the Compose stack in CI: replayed URLs count once, an ad with a
  one-render budget stops serving after that render, and a user capped at one render an hour
  stops getting the ad while another user still does.
- **The race detector** runs on every Go test.

## 12. Delivery

Each step was one pull request, complete and tested by itself.

| PR | Contents |
|---|---|
| #6 | Validation of the JSON fields the ad server reads, dashboard fixes, money read exactly, one bad campaign no longer fails every request |
| #7 | Exactly-once counting: bid id in the iid, age limits, the transactional inbox, MongoDB as a replica set |
| #8 | Budgets and pacing |
| #9 | Frequency caps |
| #10 | Ranking by price, the heap, dates parsed once, Redis deadlines |
| #11 | Metrics, the load test and this document |

## 13. What is not built

- Batched or sharded counting in the subscriber, so one hot ad can't outrun it (section 10).
- A reservation at serve time, which would bring overspend near zero.
- Exploration traffic for CPC ads whose rate starts low.
- Caps across all users, CPD pricing, more than one currency.
- Spend shown in the dashboard. It is in MongoDB's `spend` collection.
- A campaign form in the dashboard. Campaigns are created through the API.
- Pub/Sub exactly-once delivery, which would let the inbox shrink.
