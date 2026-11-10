"""Consumes click and render events from Pub/Sub and counts each one exactly once.

Pub/Sub delivers at least once, and can deliver a message again even after it
was acked. A tracking URL can also be opened many times. So every event has an
id, its type plus the id of the bid it belongs to.

Counting happens in two steps:

1. record_event writes the event to the `inbox` collection, with the event id as
   its _id. A second copy can't be written, which is the dedupe, and two events
   never write the same document, so recording doesn't slow down when one ad gets
   many events at once.
2. fold, which runs in a loop, adds recorded events to the totals in batches: in
   one transaction it adds up a batch, applies one $inc per report row and spend
   total, and marks the events folded. An event is only counted by the
   transaction that marks it, so it is counted exactly once.

Counting each event in its own transaction, the first design, had every event
of a busy ad update the same few documents, and they kept conflicting. The load
test in docs/DESIGN.md shows the difference.

Counts land in the `reports` collection, which the ad manager's /reports
endpoints serve. A billable event (a render of a CPM ad, a click of a CPC ad)
also adds its price to what the ad and its campaign have spent, and the new
totals are copied to Redis, where the ad server checks budgets.
"""

import json
import logging
import os
import signal
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Event, Thread

import redis
from google.cloud import pubsub_v1
from prometheus_client import Counter, Histogram, start_http_server
from pymongo import MongoClient, UpdateOne
from pymongo.errors import CollectionInvalid, DuplicateKeyError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
CLICK_SUBSCRIPTION = os.getenv("CLICK_SUBSCRIPTION_ID", "click-service-topic-sub")
CSC_SUBSCRIPTION = os.getenv("CSC_SUBSCRIPTION_ID", "csc-service-topic-sub")
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "ad_pulse")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_USERNAME = os.getenv("REDIS_USERNAME") or None
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None
METRICS_PORT = int(os.getenv("METRICS_PORT", "9102"))

# Prometheus metrics, served on METRICS_PORT. Both labels have fixed values.
EVENTS = Counter(
    "subscriber_events_total",
    "Click and render messages by event and result: recorded, duplicate, too_old, malformed or failed.",
    ["event", "result"],
)
# How far behind the counts are. Budgets and caps overshoot by what is in flight for this long.
SERVE_TO_COUNT = Histogram(
    "subscriber_serve_to_count_seconds",
    "Seconds from serving an ad to folding its click or render into the counts.",
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 300, 1800, 3600, 86400),
)
FOLD_FAILURES = Counter("subscriber_fold_failures_total", "Folds that failed and will be tried again.")

# A fold adds up at most this many events, and when it finds fewer, the loop waits
# this long before the next one.
FOLD_BATCH = 1000
FOLD_INTERVAL = 0.5

# Both event types share one row per ad, so a new row needs a zero for the
# counter that did not fire.
EVENT_TYPES = ("click", "render")

# The engagement service refuses events served more than 24 hours ago. Here an
# event is only counted if it was served less than COUNT_WINDOW ago, and the
# record that it was counted is kept for INBOX_TTL. A record always outlives the
# time in which a copy of its event could still be counted, so nothing is
# counted twice. The 24 hour gap between the two also covers clocks that disagree.
COUNT_WINDOW = timedelta(hours=48)
INBOX_TTL = timedelta(hours=72)

# Which event a bid type pays for.
BILLABLE_EVENT = {"CPM": "render", "CPC": "click"}

# How long Redis keeps a copy of a spend total after it last went up. A day's
# total is only read on that day. A missing total reads as nothing spent, and the
# next event for that ad writes it back.
DAILY_SPEND_TTL = timedelta(hours=48)
TOTAL_SPEND_TTL = timedelta(days=30)

COUNTER_EVENT = {"render": "CSC", "click": "CLK"}  # how frequency caps name the two event types
KNOWN_COUNTERS = {f"{entity}:{event}" for entity in ("AD", "CAMPAIGN") for event in ("CSC", "CLK")}

# A user's events for one ad or campaign are kept in a Redis sorted set, scored by
# serve time, for the ad server's frequency caps. A week is the longest cap window,
# and ad-manager-svc caps a count at 1,000, so neither limit can change an answer.
COUNTER_KEEP = timedelta(days=7)
COUNTER_TTL = timedelta(days=8)
COUNTER_MAX_EVENTS = 1000

# Raises a spend total in Redis, and never lowers it. Totals only grow, so keeping
# the larger value is right in whatever order the writes arrive, and writing the
# same value twice changes nothing. The values are whole numbers of nanos, and are
# compared as text: Lua numbers are doubles, which lose whole numbers past 2^53.
RAISE_SPEND = """
local current = redis.call('GET', KEYS[1])
local new = ARGV[1]
if current and (#current > #new or (#current == #new and current >= new)) then
  return 0
end
redis.call('SET', KEYS[1], new, 'EX', ARGV[2])
return 1
"""


class BadEvent(ValueError):
    """A message that can never be counted, so it is acked and dropped."""


@dataclass(frozen=True)
class Engagement:
    """One click or render, as the ad server described it in the signed iid."""

    ad_id: str
    campaign_id: str
    bid_id: str
    served_at: datetime
    bid_type: str
    price_nanos: int
    user_id: str = ""
    counters: tuple = ()  # such as ("AD:CSC",): the frequency cap counters this event feeds


def parse_event(data):
    """Return the Engagement in a message body, or raise BadEvent."""
    try:
        payload = json.loads(data.decode())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BadEvent(f"not JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise BadEvent("not a JSON object")

    for key in ("adid", "campaignid", "bidid"):
        if not isinstance(payload.get(key), str) or not payload[key]:
            raise BadEvent(f"no {key}")
    served = payload.get("requesttimestamp")
    if isinstance(served, bool) or not isinstance(served, int):
        raise BadEvent("no requesttimestamp")
    try:
        served_at = datetime.fromtimestamp(served, tz=timezone.utc)
    except (OverflowError, OSError, ValueError) as exc:
        raise BadEvent(f"requesttimestamp out of range: {served}") from exc

    # An ad with no bid has no price, so these two may be missing.
    bid_type = payload.get("bidtype") or ""
    price = payload.get("pricenanos", 0)
    if not isinstance(bid_type, str):
        raise BadEvent("bidtype is not text")
    if isinstance(price, bool) or not isinstance(price, int) or price < 0:
        raise BadEvent(f"pricenanos is not a whole number of nanos: {price!r}")

    # Only a capped ad's events carry these.
    user_id = payload.get("userid") or ""
    counters = payload.get("counters") or []
    if not isinstance(user_id, str):
        raise BadEvent("userid is not text")
    if not isinstance(counters, list) or not all(counter in KNOWN_COUNTERS for counter in counters):
        raise BadEvent(f"counters are not known counter names: {counters!r}")

    return Engagement(
        payload["adid"], payload["campaignid"], payload["bidid"], served_at, bid_type, price, user_id, tuple(counters)
    )


def counter_keys(event_type, event):
    """The sorted sets this event goes into: one per counter of its type, for its user.

    The names match the ones the ad server counts from, such as
    fc:AD:<ad id>:CSC:<user id> for this user's renders of the ad.
    """
    if not event.user_id:
        return []
    code = COUNTER_EVENT[event_type]
    keys = []
    for counter in event.counters:
        entity, counter_event = counter.split(":")
        if counter_event == code:
            entity_id = event.campaign_id if entity == "CAMPAIGN" else event.ad_id
            keys.append(f"fc:{entity}:{entity_id}:{code}:{event.user_id}")
    return keys


def charge(event_type, event):
    """What this event costs in nanos: its price if it is the one its bid type pays for, else 0."""
    return event.price_nanos if BILLABLE_EVENT.get(event.bid_type) == event_type else 0


def spend_totals(ad_id, campaign_id, served):
    """The spend totals one billable event adds to, and how long Redis keeps each.

    Each id is a MongoDB _id in the spend collection and, after "spend:", a Redis
    key the ad server reads. The day is the UTC day the ad was served (served is
    in Unix seconds), so a redelivered event always lands on the same day.
    """
    day = datetime.fromtimestamp(served, tz=timezone.utc).strftime("%Y-%m-%d")
    totals = []
    for kind, entity_id in (("ad", ad_id), ("campaign", campaign_id)):
        totals.append((f"{kind}:{entity_id}", TOTAL_SPEND_TTL))
        totals.append((f"{kind}:{entity_id}:{day}", DAILY_SPEND_TTL))
    return totals


def prepare_database(database):
    """Create the collections and the indexes counting needs. Safe to run on every start.

    The collections are made here, outside any transaction, so two transactions
    never race to create one.
    """
    for name in ("reports", "inbox", "spend"):
        try:
            database.create_collection(name)
        except CollectionInvalid:
            pass  # it already exists
    # MongoDB deletes an inbox record this long after it was written.
    database.inbox.create_index("seen_at", expireAfterSeconds=int(INBOX_TTL.total_seconds()))
    # fold reads the oldest events not folded yet.
    database.inbox.create_index([("folded", 1), ("seen_at", 1)])


def record_event(database, redis_client, event_type, event, now):
    """Record one event at most once. fold() adds it to the counts later.

    Returns "recorded", "duplicate" or "too_old".
    """
    if now - event.served_at > COUNT_WINDOW:
        return "too_old"

    try:
        database.inbox.insert_one({
            "_id": f"{event_type}:{event.bid_id}",
            "seen_at": now,
            "folded": False,
            "type": event_type,
            "ad": event.ad_id,
            "campaign": event.campaign_id,
            "served": int(event.served_at.timestamp()),
            "nanos": charge(event_type, event),
        })
        result = "recorded"
    except DuplicateKeyError:
        result = "duplicate"

    # Written again for a duplicate too, in case Redis failed the first time.
    add_to_counters(redis_client, counter_keys(event_type, event), event)
    return result


def fold(client, database, redis_client, now, batch=FOLD_BATCH):
    """Add up to `batch` recorded events to the counts and spend totals. Returns how many.

    One transaction reads the oldest events not folded yet, adds them up, applies
    one $inc per report row and spend total, and marks the events folded. Two folds
    that pick the same events collide on them, and the second retries without them.
    """
    def apply(session):
        events = list(database.inbox.find({"folded": False}, sort=[("seen_at", 1)], limit=batch, session=session))
        if not events:
            return [], {}

        counts = defaultdict(lambda: {"click": 0, "render": 0})
        spent = defaultdict(int)
        ttls = {}
        for event in events:
            counts[event["ad"]][event["type"]] += 1
            if event["nanos"]:
                for spend_id, ttl in spend_totals(event["ad"], event["campaign"], event["served"]):
                    spent[spend_id] += event["nanos"]
                    ttls[spend_id] = ttl

        database.reports.bulk_write(
            [UpdateOne({"_id": ad}, {"$inc": added}, upsert=True) for ad, added in counts.items()],
            ordered=False,
            session=session,
        )
        if spent:
            database.spend.bulk_write(
                [UpdateOne({"_id": spend_id}, {"$inc": {"nanos": nanos}}, upsert=True) for spend_id, nanos in spent.items()],
                ordered=False,
                session=session,
            )
        ids = [event["_id"] for event in events]
        marked = database.inbox.update_many({"_id": {"$in": ids}, "folded": False}, {"$set": {"folded": True}}, session=session)
        if marked.modified_count != len(ids):
            # A snapshot transaction can't see an event as unfolded and then fail to
            # mark it, so this means something is badly wrong. Abort rather than count.
            raise RuntimeError(f"marked {marked.modified_count} of {len(ids)} events as folded")
        return events, ttls

    # with_transaction runs apply() again after a transient error such as a write
    # conflict with another fold. That is safe because it only writes inside the
    # transaction.
    with client.start_session() as session:
        events, ttls = session.with_transaction(apply)
    if not events:
        return 0

    for event in events:
        SERVE_TO_COUNT.observe(now.timestamp() - event["served"])
    # After the commit, copy the new totals to Redis. If this fails the counts are
    # still right in MongoDB, and the next fold that touches the same ad copies them.
    totals = {row["_id"]: row["nanos"] for row in database.spend.find({"_id": {"$in": list(ttls)}})} if ttls else {}
    copy_spend_to_redis(redis_client, totals, ttls)
    return len(events)


def fold_forever(client, database, redis_client, stop):
    """Fold recorded events until stop is set. A failed fold is logged and tried again."""
    while not stop.is_set():
        try:
            folded = fold(client, database, redis_client, datetime.now(timezone.utc))
        except Exception:
            log.exception("fold failed, trying again")
            FOLD_FAILURES.inc()
            folded = 0
        if folded < FOLD_BATCH:
            stop.wait(FOLD_INTERVAL)


def add_to_counters(redis_client, keys, event):
    """Add the event to its user's frequency cap counters, and drop what no cap can reach.

    The bid id is the member and the serve time the score, so writing the same event
    again changes nothing. A failure here nacks the message, and the redelivery, a
    duplicate, writes it again.
    """
    if not keys:
        return
    served = int(event.served_at.timestamp())
    oldest = served - int(COUNTER_KEEP.total_seconds())
    pipe = redis_client.pipeline(transaction=False)
    for key in keys:
        pipe.zadd(key, {event.bid_id: served})
        pipe.zremrangebyscore(key, "-inf", f"({oldest}")
        pipe.zremrangebyrank(key, 0, -(COUNTER_MAX_EVENTS + 1))
        pipe.expire(key, int(COUNTER_TTL.total_seconds()))
    pipe.execute()


def copy_spend_to_redis(redis_client, spent, ttls):
    """Write new spend totals to Redis for the ad server, never lowering one."""
    if not spent:
        return
    raise_spend = redis_client.register_script(RAISE_SPEND)
    pipe = redis_client.pipeline(transaction=False)
    for spend_id, nanos in spent.items():
        raise_spend(
            keys=[f"spend:{spend_id}"],
            args=[str(nanos), int(ttls[spend_id].total_seconds())],
            client=pipe,
        )
    pipe.execute()


def make_callback(database, redis_client, event_type):
    def callback(message):
        try:
            event = parse_event(message.data)
        except BadEvent as exc:
            # It will never succeed, so ack it to stop the redeliveries.
            log.error("dropping unusable %s message: %s", event_type, exc)
            EVENTS.labels(event_type, "malformed").inc()
            message.ack()
            return

        try:
            result = record_event(database, redis_client, event_type, event, datetime.now(timezone.utc))
        except Exception:
            # Anything else (MongoDB or Redis down) is worth retrying.
            log.exception("failed to record %s message", event_type)
            EVENTS.labels(event_type, "failed").inc()
            message.nack()
            return

        EVENTS.labels(event_type, result).inc()
        if result == "too_old":
            log.warning(
                "not counting %s for ad %s: it was served at %s, too long ago", event_type, event.ad_id, event.served_at
            )
        else:
            log.info("%s %s for ad %s", result, event_type, event.ad_id)
        message.ack()

    return callback


def main():
    if not PROJECT_ID:
        sys.exit("GCP_PROJECT_ID is not set")
    if not MONGODB_URI:
        sys.exit("MONGODB_URI is not set")

    mongo = MongoClient(MONGODB_URI)
    if "setName" not in mongo.admin.command("hello"):
        sys.exit("MongoDB has to be a replica set: events are folded into the counts in transactions, which a standalone server does not run")
    database = mongo[MONGODB_DATABASE]
    prepare_database(database)

    redis_client = redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, username=REDIS_USERNAME, password=REDIS_PASSWORD, decode_responses=True
    )
    redis_client.ping()

    # This is a queue consumer with no HTTP server of its own, so the metrics get one.
    start_http_server(METRICS_PORT)

    stop = Event()
    folder = Thread(target=fold_forever, args=(mongo, database, redis_client, stop), daemon=True)
    folder.start()

    # Credentials come from Application Default Credentials; set
    # GOOGLE_APPLICATION_CREDENTIALS to a key file for local development.
    subscriber = pubsub_v1.SubscriberClient()
    futures = [
        subscriber.subscribe(
            subscriber.subscription_path(PROJECT_ID, CLICK_SUBSCRIPTION),
            callback=make_callback(database, redis_client, "click"),
        ),
        subscriber.subscribe(
            subscriber.subscription_path(PROJECT_ID, CSC_SUBSCRIPTION),
            callback=make_callback(database, redis_client, "render"),
        ),
    ]
    log.info("listening on %s and %s", CLICK_SUBSCRIPTION, CSC_SUBSCRIPTION)

    shutdown = Event()
    signal.signal(signal.SIGTERM, lambda *_: shutdown.set())
    signal.signal(signal.SIGINT, lambda *_: shutdown.set())

    shutdown.wait()

    log.info("shutting down")
    for future in futures:
        future.cancel()
    subscriber.close()
    stop.set()
    folder.join(timeout=10)
    mongo.close()
    redis_client.close()


if __name__ == "__main__":
    main()
