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
- Errors from Redis are logged. The caller only sees "internal error".

## Layout

- `api/adserve.go`: the `/adserve` handler: collects eligible ads across every
  active campaign, then ranks and bids once.
- `api/bids.go`: matches ranked ads against the impressions on offer and
  builds the OpenRTB-ish bid response.
- `util/helper.go`: targeting rules (flight dates, ad unit, day, hour) and
  ranking.
- `cache/`: the Redis-backed `Store` interface and the JSON shapes cached
  there (shared with what ad-manager-svc writes).
