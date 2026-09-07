# ad-refresh-cache-svc

Tiny poller: every 15 seconds it calls ad-manager-svc's
`/cache/campaigns`, `/cache/ads` and `/cache/creatives` endpoints, which is
what actually rebuilds the Redis cache ad-server-svc reads from. This service
just supplies the timer.

## Configuration

| Variable | Purpose |
|---|---|
| `AD_MANAGER_URL` | Base URL of ad-manager-svc (required) |

## Running

```
pip install -r requirements.txt
export AD_MANAGER_URL=http://localhost:5000
python refresh-cache.py
```
