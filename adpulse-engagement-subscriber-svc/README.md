# adpulse-engagement-subscriber-svc

Background worker: subscribes to the click and render Pub/Sub topics that
adpulse-engagement-svc publishes to, and counts each event exactly once into a
`{click, render}` row per ad id in MongoDB's `reports` collection, the data
ad-manager-svc's `/reports` endpoints serve to the dashboard.

## Counting each event once

Pub/Sub delivers at least once, and can deliver a message again even after it was
acked. A tracking URL can also be opened many times. So each event has an id, its
type and the id of the bid it belongs to (`click:<bid id>` or `render:<bid id>`),
and one MongoDB transaction does both writes:

1. Upsert the id into the `inbox` collection. If it was already there, the event
   was counted before. Nothing else is written, and the message is acked.
2. `$inc` the click or render count on the ad's `reports` row.

Either both writes happen or neither does, so a crash at any point is safe. If it
crashes before the commit, nothing was written and the redelivered message is
counted normally. If it crashes after the commit but before the ack, the
redelivered message finds its id and is only acked. Two workers given the same
message at once collide on the inbox id: one commits, and the other retries and
finds it.

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
ad server and carried in the signed iid as `pricenanos`, is added in the same
transaction to four totals in the `spend` collection: the ad's and the campaign's,
overall and for the UTC day the ad was served. Using the serve day means a redelivered
event always lands on the same day.

After the commit the new totals are copied to Redis (`spend:ad:<id>`,
`spend:ad:<id>:<day>` and the same for the campaign), where the ad server checks
budgets. A small Lua script writes a total only if it is larger than what is there.
Totals only grow, so the larger value is right in whatever order two copies arrive, and
the values are compared as text, because Lua numbers are doubles and lose whole numbers
past 2^53 nanos (about $9 million). If Redis fails, the message is nacked, and its
redelivery is a duplicate that copies the totals again without charging twice. Daily
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

They count a replayed event, an event delivered again after its commit, and the
same event arriving on twelve threads at once, and check that each is counted
once. One also fails the second write mid-transaction and checks that the first
is rolled back. The spend tests check that a replay is never charged twice, that
twelve events of one ad at once add up exactly, that a failed copy to Redis is
repaired by the redelivery, and that a later, smaller total never overwrites a
larger one, including past 2^53. CI runs them against the same kind of replica
set and Redis.
