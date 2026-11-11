# ad-server-svc

Go/Gin service that answers `POST /adserve?adunit_id=...&publisher_id=...`: it
validates the publisher and ad unit against ad-manager-svc, reads the active
campaigns/ads out of Redis (kept warm by ad-manager-svc's cache endpoints),
filters them by flight dates and targeting rules, ranks the survivors, and
returns a bid per matching impression along with click/render tracking URLs.

## Configuration

Environment variables, or an `app.env` file in the working directory (see
`app.env.example`); either works, and the environment wins if both are set.

| Variable | Default | Purpose |
|---|---|---|
| `SERVER_ADDRESS` | `0.0.0.0:8080` | Address to listen on |
| `AD_MANAGER_ADDRESS` | `http://localhost:5000` | ad-manager-svc base URL |
| `AD_MANAGER_API_KEY` | (empty) | Sent to ad-manager-svc as `X-API-Key` when it checks a publisher or ad unit. Must match the manager's `API_KEY`. If the manager rejects it (401) the ad server logs that and answers 502, not "not found" |
| `REDIS_HOST` | `localhost` | Redis host for the serving cache |
| `REDIS_PORT` | `6379` | |
| `REDIS_USERNAME`, `REDIS_PASSWORD` | (empty) | |
| `REDIS_TIMEOUT` | `100ms` | How long all of one request's Redis calls may take together. Past it the request fails with a 500 and nothing is served. `0` means no limit |
| `CLICK_URL`, `RENDER_URL` | `http://localhost:8081/engagement/...` | adpulse-engagement-svc endpoints embedded in every bid |
| `TRACKING_SECRET` | (empty) | Signs the click and render URLs with an HMAC. Use the same value as adpulse-engagement-svc. Empty means unsigned URLs |

## Running

```
cp app.env.example app.env   # fill in real values
make server                  # go run main.go
```

## Testing

```
go test -v -race -cover ./...
```

## Notes

- Every request checks the publisher and the ad unit with ad-manager-svc. Each
  check has a 3 second timeout. If the manager can't be reached the answer is
  a 502.
- If the cache has not been filled yet there is nothing to serve, so the
  answer is 204 and not an error.
- Day and hour targeting use UTC, like the flight dates.
- A cached ad or campaign that can't be decoded is logged and skipped, and the
  rest still serve. ad-manager-svc checks these fields before storing them.
- Bids and budgets are read as micros (millionths of the currency) straight from
  the JSON text, never through a float, see `cache/money.go`.
- Errors from Redis are logged. The caller only sees "internal error".

## Budgets and pacing

An ad and its campaign can each have a total and a daily budget. Before ranking, the
server reads what every budgeted candidate has spent, in one `MGET`, and skips an ad if
it or its campaign:

- has spent its total budget, or today's budget (days are UTC), or
- is ahead of pace: today's spend is more than the daily budget times the share of the
  day gone by, plus one hour. That spreads a daily budget over the day instead of
  spending it by mid-morning, and the hour lets each day start.

Ads and campaigns with no budget are not read at all. With a budget on all 1,000 ads of
the 50 x 20 benchmark (`BenchmarkAdserveWithBudgets`), a request costs about 0.7 ms more
CPU and one more Redis call, 53 instead of 52.

The auction is first price: the winner pays its bid. A render of a CPM ad costs a
thousandth of the bid, and a click of a CPC ad costs the whole bid. That price goes into
the signed tracking URLs, so editing an ad's bid never changes what its earlier events
cost. adpulse-engagement-subscriber-svc adds it up, exactly once per event, and copies
the totals into Redis as `spend:ad:<id>`, `spend:ad:<id>:<yyyy-mm-dd>` and the same for
the campaign. Money is counted in nanos, a thousandth of a micro, so the price of a CPM
render is always a whole number.

**An ad can overspend a little.** Spend is recorded when a render or click arrives, not
when the ad is served. Between serving the ad that reaches the budget and that event
being counted, the ad keeps serving:

```
overspend <= price per event x events in flight
events in flight ~= the ad's serve rate x (time until the render or click + pipeline delay)
```

For a $1 CPM ad serving 1,000 times a second, with a second from serve to counted
spend, that is about 1,000 x $0.001 = $1. A CPC ad can overspend more, because a click
can come minutes after the ad was served. Google Ads makes the same kind of trade: a day
can spend up to twice the daily budget, and the month is capped. Getting closer to zero
would mean reserving the price when the ad is served and releasing what never renders.

**That bound assumes the subscriber keeps up, and the load test checks it.** `loadtest.py`
serves one CPM ad with a $1 budget as fast as 16 threads can ask, and renders every ad it
gets. Against the first subscriber, which counted each event in its own transaction, the
ad spent between $2.54 and $3.72 in three runs: every render of one ad updated the same
spend documents, the transactions kept conflicting, the subscriber fell to about 120 events
a second, and the delay grew to tens of seconds. The subscriber now records each event on
its own and folds them into the totals in batches. The same test spends $1.02 to $1.12 (2%
to 12% over, median 5%) in five runs, with under a second from serve to counted. How far it
overspends depends on how fast the subscriber folds: in a cloud test, one subscriber replica
overspent by 94% to 120% and eight by about 1%. The results, every run and the run that went
wrong, are in [docs/DESIGN.md](../docs/DESIGN.md#10-capacity-and-a-measured-run).

If Redis loses the totals, an ad reads as having spent nothing until its next billable
event writes the true total back from MongoDB, so the same in-flight bound applies.

## Frequency caps

A cap limits how many renders (`CSC`) or clicks (`CLK`) one user may have of an ad, or
of any ad in a campaign, within a window, such as one render an hour. Caps can be set on
an ad and on its campaign, and both apply. The user is the request's OpenRTB `user.id`.

The subscriber keeps each user's events in a Redis sorted set per entity and event type,
`fc:<AD or CAMPAIGN>:<id>:<CSC or CLK>:<user id>`, with the bid id as the member and the
serve time as the score. After the budget check, the server counts the members inside
every window of every remaining capped ad with `ZCOUNT`, all in one pipelined round trip,
and skips the ads the user has reached a cap on. Ads with no caps cost no read, so the
second round trip only happens when a candidate has a cap.

A capped ad is only sent to a request with a user id, because without one the cap can't
be checked. A user id longer than 128 characters counts as none. A capped ad's tracking
URLs carry the user id and the counters its events feed, such as `AD:CSC`, so the
subscriber only keeps sets for capped ads. Other ads' URLs carry no user id at all.

Like spend, events count when they arrive, so a user who loads several pages within a
second can see a capped ad a little more often than the cap. If Redis loses the sets,
the caps start again from zero. That is accepted, because a cap protects the user's
experience and is not billing.

## Ranking

Ads are ordered by priority first, lowest number first, the way Google Ad Manager puts
guaranteed deals ahead of open competition. Within a priority they compete on eCPM, what
a thousand impressions are expected to pay:

```
CPM:  eCPM = bid
CPC:  eCPM = bid x expected click-through rate x 1000
```

Ties go to the lower ad id, so the order is the same on every request. A new CPC ad has
no history, and one click in two renders is not a 50% rate, so its rate is blended with
a prior: `(clicks + 0.01 x 100) / (renders + 100)`. That is the mean of a Beta prior of 1%
worth a hundred renders. A new ad starts at 1%, and its own record takes over as renders
add up. ad-manager-svc's cache job adds the clicks and renders of every CPC ad to its
cached JSON, so ranking reads nothing more from Redis. If MongoDB is down during a
refresh, those ads rank on the prior until the next one. A known weakness: an ad whose
rate starts low gets few renders and may never earn enough to recover. A small share of
exploration traffic would fix that, and is not built.

Nothing is sorted up front. A request usually fills one or two slots from hundreds of
candidates, so the candidates go into a heap, built in O(n), and the bidder takes the
best one left, in O(log n), only while it still has slots to fill. Flight dates are also
parsed once when an ad is decoded, not on every request.

Measured with the benchmarks, old and new run in turn on one machine, medians of four:

| | before | sorted keys | heap |
|---|---|---|---|
| 50 campaigns x 20 ads | 1.71 ms | 1.76 ms | 1.27 ms |
| the same, a budget on every ad | 2.70 ms | 2.77 ms | 2.14 ms |

Sorting small keys instead of the ads themselves, the first try, made no difference:
building every key and copying every ad into order cost what the sort saved. The heap,
which orders only the ads the bidder asks for, is about 25% faster.

## Metrics

`GET /metrics` serves Prometheus metrics: `adserver_requests_total{result}` (bid, no_bid,
bad_request, error), `adserver_request_duration_seconds`, and
`adserver_ads_skipped_total{reason}`, which counts the candidates the budget and cap checks
left out (total_budget, daily_budget, pacing, spend_unreadable, frequency_cap, no_user_id,
unusable_cap). Every label has a fixed set of values.

## Layout

- `api/adserve.go`: the `/adserve` handler: collects eligible ads across every
  active campaign, filters them by budget and frequency cap, then ranks and bids once.
- `api/budget.go`, `api/caps.go`, `api/ranking.go`: the budget and pacing check, the
  frequency caps, and the ranking, each described above.
- `api/bids.go`: takes ads from the ranking, best first, matches them against the
  impressions on offer and builds the OpenRTB-ish bid response.
- `util/helper.go`: targeting rules (flight dates, ad unit, day, hour).
- `cache/`: the Redis-backed `Store` interface and the JSON shapes cached
  there (shared with what ad-manager-svc writes), including money in micros
  (`money.go`) and flight dates parsed once (`flight.go`).
