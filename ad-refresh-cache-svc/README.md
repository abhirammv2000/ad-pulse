# ad-refresh-cache-svc

A small poller. Every 15 seconds it calls ad-manager-svc's `/cache/campaigns`,
`/cache/ads` and `/cache/creatives` endpoints. Those calls rebuild the Redis
cache that ad-server-svc reads from, so this service only supplies the timer.

Each request has a 10 second timeout. If one call fails it is logged and the
next one still runs. The service exits cleanly on SIGTERM.

## Configuration

| Variable | Purpose |
|---|---|
| `AD_MANAGER_URL` | Base URL of ad-manager-svc (required) |
| `REFRESH_INTERVAL_SECONDS` | Seconds between refreshes (default 15) |

## Running

```
pip install -r requirements.txt
export AD_MANAGER_URL=http://localhost:5000
python refresh_cache.py
```

## Testing

```
python -m unittest discover -s tests -p "*_test.py"
```
