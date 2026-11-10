# adpulse-engagement-subscriber-svc

Background worker: subscribes to the click and render Pub/Sub topics that
adpulse-engagement-svc publishes to, and counts each event exactly once into a
`{click, render}` row per ad id in MongoDB's `reports` collection, the data
ad-manager-svc's `/reports` endpoints serve to the dashboard.

## Counting each event once

Pub/Sub delivers at least once, and can deliver a message again even after it was
acked. A tracking URL can also be opened many times. So each event has an id, its
type and the id of the bid it belongs to (`click:<bid id>` or `render:<bid id>`),
and counting happens in two steps.

**Recording.** Each message is inserted into the `inbox` collection with the event
id as its `_id`, with what it adds to the counts: its ad, campaign, serve time and
price. A second copy fails on the unique `_id` and is only acked, so a replay or a
redelivery is never recorded twice. If the worker dies after the insert but before
the ack, the redelivery finds the record. Recording writes one new document per
event and nothing else, so events never wait on each other, however many one ad
gets.

**Folding.** A loop in the same process takes up to 1,000 recorded events that are
not folded yet, oldest first, and in one MongoDB transaction:

1. adds them up, and applies one `$inc` per `reports` row and per spend total;
2. marks them folded.

An event is counted only by the transaction that marks it, so it is counted exactly
once. A fold that fails part way leaves nothing behind, and the next one picks the
same events up. Two subscribers folding at the same time collide on the events
they both picked, and the second retries without them. When a fold finds fewer
than 1,000 events, the loop waits half a second.

**Why two steps.** The first version counted each event in its own transaction.
Every render of a busy ad then updated the same few documents, the transactions
kept conflicting and retrying, and one hot ad was counted at about 65 events a
second, while it rendered 200 a second. Recording plus folding counts the same hot
ad at about 1,700 a second, because a batch touches each total once. The
measurements are in [docs/DESIGN.md](../docs/DESIGN.md#10-capacity-and-a-measured-run).

Records written by the first version have no `folded` field, so they are never
folded again: they were counted when they were written.

The inbox can't grow forever, so a TTL index deletes each record after 72 hours.
Two limits make sure a deleted record can never let an event count twice:

- adpulse-engagement-svc refuses an event whose ad was served more than 24 hours ago.
- This service only counts an event served less than 48 hours ago, and acks and
  logs anything older.

An event is counted at or after its serve time, so its record lasts until at least
72 hours after it. A copy that arrives after that is more than 48 hours old and is
refused. The 24 hours between the limits cover clocks on different machines that
disagree. The serve time is in the signed iid, so it can't be faked. The cost is
that an event stuck in a backlog for over 48 hours is not counted.

## Spend

A billable event is a render of a CPM ad or a click of a CPC ad. Its price, set by the
ad server and carried in the signed iid as `pricenanos`, is kept on its inbox record
and added by the fold, in the same transaction as the counts, to four totals in the
`spend` collection: the ad's and the campaign's, overall and for the UTC day the ad
was served. Using the serve day means a redelivered event always lands on the same day.

After each fold commits, the new totals are copied to Redis (`spend:ad:<id>`,
`spend:ad:<id>:<day>` and the same for the campaign), where the ad server checks
budgets. A small Lua script writes a total only if it is larger than what is there.
Totals only grow, so the larger value is right in whatever order two copies arrive, and
the values are compared as text, because Lua numbers are doubles and lose whole numbers
past 2^53 nanos (about $9 million). If Redis fails after a fold, MongoDB still has the
right totals, and the next fold that touches the same ad copies them. Until then the ad
looks like it has more budget than it does, so it keeps serving and its next event
brings the fold that repairs it. Daily
totals expire from Redis after 48 hours and overall totals 30 days after they last
grew. MongoDB keeps them all.

## Frequency cap counters

An event of a capped ad carries the user id and the counters it feeds, such as
`AD:CSC` for renders of the ad. After the commit it is added to each matching Redis
sorted set, `fc:<AD or CAMPAIGN>:<id>:<CSC or CLK>:<user id>`, with the bid id as the
member and the serve time as the score, which the ad server's caps count. Adding the same
event again changes nothing, so the redelivery after a Redis failure is safe. Each set
drops events more than a week older than the newest one, keeps at most 1,000, and
expires eight days after its last write. A week and 1,000 are the longest window and
the highest count ad-manager-svc accepts, so trimming never changes a cap's answer.

**MongoDB has to be a replica set**, because a standalone server does not run
transactions. The service checks this when it starts and exits with a message if
it is not. One member is fine for development, and the Compose stack runs one.
Use three in production. Managed MongoDB (Atlas) is always a replica set.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GCP_PROJECT_ID` | none (required) | Pub/Sub project |
| `GOOGLE_APPLICATION_CREDENTIALS` | none | Path to a service account key; unset in the cluster where Workload Identity applies instead |
| `CLICK_SUBSCRIPTION_ID` | `click-service-topic-sub` | Pub/Sub subscription for clicks |
| `CSC_SUBSCRIPTION_ID` | `csc-service-topic-sub` | Pub/Sub subscription for renders |
| `MONGODB_URI` | none (required) | MongoDB connection string, for a replica set |
| `MONGODB_DATABASE` | `ad_pulse` | Mongo database name |
| `REDIS_HOST` | `localhost` | Redis the ad server reads spend from |
| `REDIS_PORT`, `REDIS_USERNAME`, `REDIS_PASSWORD` | `6379`, none, none | Redis connection |
| `METRICS_PORT` | `9102` | Port of the Prometheus `/metrics` endpoint: `subscriber_events_total{event, result}` (recorded, duplicate, too_old, malformed, failed), `subscriber_serve_to_count_seconds`, how long after serving an event was folded into the counts, and `subscriber_fold_failures_total` |

## Running

```
pip install -r requirements.txt
export GCP_PROJECT_ID=your-project
export MONGODB_URI=mongodb://localhost:27017/?replicaSet=rs0
python app.py
```

There is no HTTP endpoint here. It's a long-running consumer that exits
cleanly on SIGTERM/SIGINT.

A message that can't be parsed, or has no `adid`, `bidid` or `requesttimestamp`,
is acknowledged and dropped, because redelivering it would never help. A database
error leaves it unacknowledged so Pub/Sub sends it again.

## Testing

```
python -m unittest discover -s tests -p "*_test.py"
```

Most tests use fake messages and need nothing else. The exactly-once tests need a
real replica set and the spend tests also need Redis. Both skip without them:

```
docker run -d --name mongo -p 27017:27017 mongo:7 --replSet rs0 --bind_ip_all
docker exec mongo mongosh --eval "rs.initiate({_id: 'rs0', members: [{_id: 0, host: 'localhost:27017'}]})"
docker run -d --name redis -p 6379:6379 redis:7-alpine
MONGODB_TEST_URI="mongodb://localhost:27017/?replicaSet=rs0" REDIS_TEST_URL="redis://localhost:6379/0" \
  python -m unittest discover -s tests -p "*_test.py"
```

They record a replayed event, an event delivered again after it was recorded, and
the same event arriving on twelve threads at once, and check that each is counted
once. One fails a fold part way and checks that nothing was left behind, and one
runs four folds over the same 600-event backlog at once and checks every event is
counted exactly once. The spend tests check that a replay is never charged twice,
that twelve events of one ad at once add up exactly, that a failed copy to Redis is
repaired by the next fold, and that a later, smaller total never overwrites a larger
one, including past 2^53. CI runs them against the same kind of replica set and
Redis.
