# Ad Pulse

An ad-serving platform built from six small services. An ad manager lets you create publishers, advertisers, campaigns, ads and creatives. An ad server picks the best ad for a page slot. An engagement pipeline counts clicks and renders for each ad.

```
ad-manager-frontend -> ad-manager-svc -> Postgres
                            |
                            v
                      Redis cache  <- ad-refresh-cache-svc (rebuilds it every 15 s)
                            |
                            v
                      ad-server-svc  (filters, ranks, returns a bid with click and render URLs)
                            |
                   browser hits the URLs
                            v
              adpulse-engagement-svc -> Pub/Sub -> adpulse-engagement-subscriber-svc -> MongoDB
                                                                                         |
                                                              ad-manager-svc /reports <--+
```

| Service | Language | What it does |
|---|---|---|
| [ad-manager-svc](ad-manager-svc/) | Python, Flask | CRUD for the six entities, the cache refresh endpoints, and `/reports` |
| [ad-manager-frontend](ad-manager-frontend/) | React | Dashboard for the above, plus a page that requests and shows a live ad |
| [ad-server-svc](ad-server-svc/) | Go, Gin | Filters cached ads by flight dates and targeting, ranks them, returns bids |
| [ad-refresh-cache-svc](ad-refresh-cache-svc/) | Python | Calls the manager's cache endpoints on a timer |
| [adpulse-engagement-svc](adpulse-engagement-svc/) | Go, Gin | Takes click and render pings and publishes them to Pub/Sub |
| [adpulse-engagement-subscriber-svc](adpulse-engagement-subscriber-svc/) | Python | Reads Pub/Sub and keeps click and render counts per ad in MongoDB |
| [ad-devops](ad-devops/) | Helm, Docker Compose | The Kubernetes chart and the local stack |

## Run it

```
docker compose -f ad-devops/deployments/docker-compose.yaml up --build
```

This starts Postgres, Redis, MongoDB, a local Pub/Sub emulator and all six services, so nothing needs a cloud account. The frontend is on http://localhost:3000, the manager on :5000 and the ad server on :8080.

With it running, `integration_test.py` walks the whole flow (create, cache, serve, click, render, report):

```
AD_MANAGER_HOST=http://localhost:5000 AD_SERVER_HOST=http://localhost:8080 \
  python -m unittest integration_test -v
```

Each service reads its settings from environment variables, and its own README lists them.

## Tests

```
cd ad-manager-svc && python -m unittest discover -s app/test -p "*_test.py"
cd adpulse-engagement-subscriber-svc && python -m unittest discover -s tests -p "*_test.py"
cd ad-refresh-cache-svc && python -m unittest discover -s tests -p "*_test.py"
cd ad-server-svc && go vet ./... && go test -race ./...
cd adpulse-engagement-svc && go vet ./... && go test -race ./...
cd ad-manager-frontend && npm test -- --watchAll=false
helm lint ad-devops/helm/ad-pulse
```

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs all of these on every push and pull request. The unit tests mock the database, Redis and Pub/Sub, so they need none of them. The full stack is tested separately: `integration_test.py` against the Docker Compose stack, with signed tracking URLs turned on.

## Deploying

The Helm chart in [ad-devops/helm/ad-pulse](ad-devops/helm/ad-pulse/) deploys every service. Credentials never go in `values.yaml`. Pass them from a values file that isn't committed, or with `--set-string` from CI secrets:

```
helm upgrade --install adpulse ./ad-devops/helm/ad-pulse \
  --namespace adpulse -f my-values-secrets.yaml
```

The `stage` and `main` branches deploy through `build_push.yml` and `main.yaml`. They read their secrets from the repo's Actions secrets (`DATABASE_URL_STAGE` and `_PROD`, `MONGODB_URI_*`, `REDIS_*`, `SUPABASE_*`, `GCP_SA_KEY_PROD`) and need a GKE cluster. The production deploy in `main.yaml` only runs when the repo variable `DEPLOY_ENABLED` is `true` (or when you start it by hand), so a fork without those secrets doesn't show a failing build. The services' public URLs are read from repo variables (`AD_SERVER_URL_PROD`, `AD_MANAGER_URL_PROD`, `ENGAGEMENT_URL_PROD`, and the same with `_STAGE`). If a variable isn't set the workflow falls back to the address it used before.

## Known gaps

I would fix these next, roughly in this order:

- **Click and render URLs can be replayed.** They are signed when `TRACKING_SECRET` is set (the compose stack sets it), so nobody can make up an event for an ad. A real URL can still be hit many times, and each hit counts. Without the secret the URLs are not checked at all.
- **The manager API has no authentication,** and CORS is open unless `CORS_ALLOWED_ORIGINS` is set.
- **The ad server asks the manager about the publisher and ad unit.** A confirmed one is remembered for 30 seconds, so a deleted publisher can keep serving for up to that long. Each call has a 3 second timeout.
- **There are no database migrations.** The manager creates missing tables on startup and never alters existing ones.
- **The six entity services repeat the same create and update code.**
- **Names are lowercase and run together** (`adunitid`, `campaignstate`) in the database and the JSON API. The ad server and dashboard depend on them, so they would need a versioned change.

## History

Ad Pulse began as a team project for CSCI 5828 (Software Engineering Methods) at CU Boulder. This repository is a later rework. It removed the credentials that were committed, fixed the ad-serving and caching logic, rebuilt the frontend image for real deployment, added health checks and a schema bootstrap, wired real tests into CI, and added a Docker Compose stack with a Pub/Sub emulator so the whole thing runs on a laptop.
