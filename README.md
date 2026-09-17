# Ad Pulse

Ad Pulse is a small ad-serving platform: an ad manager for creating publishers,
advertisers, campaigns, ads and creatives; an ad server that picks and returns
an ad for a given ad unit; and an engagement pipeline that records clicks and
renders back into per-ad reports.

## How it fits together

```
ad-manager-frontend  →  ad-manager-svc  →  Postgres (campaigns/ads/creatives/etc.)
                              │
                              ▼
                        Redis (serving cache, refreshed by ad-refresh-cache-svc)
                              │
                              ▼
                        ad-server-svc  →  picks & ranks an ad, returns a bid
                              │
                     click / render URLs
                              ▼
                adpulse-engagement-svc  →  Pub/Sub  →  adpulse-engagement-subscriber-svc
                                                              │
                                                              ▼
                                                        MongoDB (reports)
```

| Service | Language | Responsibility |
|---|---|---|
| [ad-manager-svc](ad-manager-svc/) | Python / Flask | CRUD for publishers, advertisers, campaigns, ads, creatives; the serving cache refresh endpoints; `/reports` |
| [ad-manager-frontend](ad-manager-frontend/) | React | Dashboard for the above, plus a demo page that requests and renders a live ad |
| [ad-server-svc](ad-server-svc/) | Go / Gin | Given an ad unit + publisher, filters the cached ads by flight dates and targeting, ranks them, and returns a bid with tracking URLs |
| [ad-refresh-cache-svc](ad-refresh-cache-svc/) | Python | Polls ad-manager-svc's cache endpoints on a timer so the Redis cache stays warm |
| [adpulse-engagement-svc](adpulse-engagement-svc/) | Go / Gin | Receives click/render pings from the tracking URLs and publishes them to Pub/Sub |
| [adpulse-engagement-subscriber-svc](adpulse-engagement-subscriber-svc/) | Python | Consumes those Pub/Sub messages and aggregates click/render counts per ad in MongoDB |
| [ad-devops](ad-devops/) | Helm / Docker Compose | Kubernetes chart and local Kafka/Zookeeper compose file |

## Running locally

The fastest way to see the whole thing working end to end, including the
click/render pipeline, is:

```
docker compose -f ad-devops/deployments/docker-compose.yaml up --build
```

This starts Postgres, Redis, MongoDB, a local Pub/Sub emulator (so the
engagement pipeline works with no real GCP project), and all six services.
Frontend at http://localhost:3000, ad-manager-svc at :5000, ad-server-svc at
:8080. With it running, the root `integration_test.py` exercises the full
create → cache → serve → click/render → report flow:

```
AD_MANAGER_HOST=http://localhost:5000 AD_SERVER_HOST=http://localhost:8080 \
  python -m unittest integration_test -v
```

To run a single service against your own infra instead, each service reads
its configuration from environment variables, nothing is hardcoded, so you
point it at your own Postgres, Redis, MongoDB and GCP project.

**ad-manager-svc**
```
cd ad-manager-svc
pip install -r requirements.txt
export DATABASE_URL=postgresql://user:pass@localhost:5432/adpulse
export MONGODB_URI=mongodb://localhost:27017
export REDIS_HOST=localhost
python run.py   # http://localhost:5000, health check at /health
```

**ad-server-svc**
```
cd ad-server-svc
cp app.env.example app.env   # fill in REDIS_HOST etc., or export the same vars
make server                  # http://localhost:8080
```

**ad-manager-frontend**
```
cd ad-manager-frontend
npm ci
REACT_APP_API_BASE_URL=http://localhost:5000 \
REACT_APP_API_AD_SERVER_URL=http://localhost:8080 \
npm start                    # http://localhost:3000
```
The production Docker image is a static build served by nginx; the same two
variables are baked into `public/config.js` by the container's entrypoint at
startup, so one built image can be promoted from stage to prod without a
rebuild.

**adpulse-engagement-svc** and **adpulse-engagement-subscriber-svc** need a
GCP project with a Pub/Sub topic/subscription pair for clicks and one for
renders (see `GCP_PROJECT_ID`, `CLICK_TOPIC_ID`/`CSC_TOPIC_ID` and
`CLICK_SUBSCRIPTION_ID`/`CSC_SUBSCRIPTION_ID`). Locally, authenticate with
`gcloud auth application-default login` or point
`GOOGLE_APPLICATION_CREDENTIALS` at a service account key; in the cluster this
should be a Workload Identity binding rather than a key file.

## Deploying

The Helm chart in [ad-devops/helm/ad-pulse](ad-devops/helm/ad-pulse/) deploys
every service. Credentials are never checked into `values.yaml` — they go into
the chart's `Secret` (see `templates/secrets.yaml`) via a values file you don't
commit, or via `--set-string` from CI secrets:

```
helm upgrade --install adpulse ./ad-devops/helm/ad-pulse \
  --namespace adpulse \
  -f my-values-secrets.yaml   # databaseUrl, mongodbUri, redis*, supabase*, gcpProjectId
```

`.github/workflows/build_push.yml` (branch `stage`) and `main.yaml` (branch
`main`) build, tag and deploy every changed service, then run the upgrade
above with secrets pulled from the repo's Actions secrets — add
`DATABASE_URL_STAGE`/`_PROD`, `MONGODB_URI_STAGE`/`_PROD`,
`REDIS_HOST_STAGE`/`_PROD` (+ `_PORT`/`_USERNAME`/`_PASSWORD`), `SUPABASE_URL`,
`SUPABASE_KEY` there before relying on CI to deploy.

## Contributing

Run each service's tests before opening a PR:
```
cd ad-manager-svc && python -m unittest discover -s app/test -p "*_test.py"
cd ad-server-svc && go test ./...
cd adpulse-engagement-svc && go test ./...
cd ad-manager-frontend && npm test
```

## History

Ad Pulse started as a team project for CSCI 5828 (Software Engineering
Methods) at CU Boulder. This repository is a solo rework done afterward:
removing credentials that had been committed to the codebase, fixing the
ad-serving and caching logic, rebuilding the frontend for a real deployment
instead of the CRA dev server, adding the schema bootstrap and health checks
the services were missing, wiring real tests into CI in place of stubs that
never ran, and adding a local Docker Compose stack, including a Pub/Sub
emulator, so the whole thing runs end to end on a laptop with no cloud
project required.
