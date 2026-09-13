# adpulse-engagement-subscriber-svc

Background worker: subscribes to the click and render Pub/Sub topics that
adpulse-engagement-svc publishes to, and aggregates a `{click, render}` count
per ad id into MongoDB's `reports` collection — the data ad-manager-svc's
`/reports` endpoints serve to the dashboard.

Counts are updated with an atomic `$inc` upsert, so concurrent messages for
the same ad can't clobber each other's counts the way a read-then-write would.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GCP_PROJECT_ID` | — (required) | Pub/Sub project |
| `GOOGLE_APPLICATION_CREDENTIALS` | — | Path to a service account key; unset in the cluster where Workload Identity applies instead |
| `CLICK_SUBSCRIPTION_ID` | `click-service-topic-sub` | Pub/Sub subscription for clicks |
| `CSC_SUBSCRIPTION_ID` | `csc-service-topic-sub` | Pub/Sub subscription for renders |
| `MONGODB_URI` | — (required) | MongoDB connection string |
| `MONGODB_DATABASE` | `ad_pulse` | Mongo database name |

## Running

```
pip install -r requirements.txt
export GCP_PROJECT_ID=your-project
export MONGODB_URI=mongodb://localhost:27017
python app.py
```

There is no HTTP endpoint here — it's a long-running consumer that exits
cleanly on SIGTERM/SIGINT.
