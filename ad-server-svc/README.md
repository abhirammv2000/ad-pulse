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

If Redis loses the totals, an ad reads as having spent nothing until its next billable
event writes the true total back from MongoDB, so the same in-flight bound applies.

## Layout

- `api/adserve.go`: the `/adserve` handler: collects eligible ads across every
  active campaign, then ranks and bids once.
- `api/bids.go`: matches ranked ads against the impressions on offer and
  builds the OpenRTB-ish bid response.
- `util/helper.go`: targeting rules (flight dates, ad unit, day, hour) and
  ranking.
- `cache/`: the Redis-backed `Store` interface and the JSON shapes cached
  there (shared with what ad-manager-svc writes).
