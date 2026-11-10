"""Consumes click and render events from Pub/Sub and counts each one exactly once.

Pub/Sub delivers at least once, and can deliver a message again even after it
was acked. A tracking URL can also be opened many times. So every event has an
id, its type plus the id of the bid it belongs to, and the count and a record of
that id are written in one MongoDB transaction. If the record is already there,
the event was counted before and the message is only acked.

Counts land in the MongoDB `reports` collection, which the ad manager's
/reports endpoints serve to the dashboard.

A billable event (a render of a CPM ad, a click of a CPC ad) also adds its
price to what the ad and its campaign have spent, in the same transaction, and
the new totals are then copied to Redis, where the ad server checks budgets.
"""

import json
import logging
import os
import signal
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Event

import redis
from google.cloud import pubsub_v1
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import CollectionInvalid

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

# Raises a spend total in Redis, and never lowers it. Totals only grow, so keeping
# the larger value is right in whatever order the writes arrive, and writing the
# same value twice changes nothing. The values are whole numbers of nanos, and are
# compared as text: Lua numbers are doubles, which lose whole numbers past 2^53.
COUNTER_EVENT = {"render": "CSC", "click": "CLK"}  # how frequency caps name the two event types
KNOWN_COUNTERS = {f"{entity}:{event}" for entity in ("AD", "CAMPAIGN") for event in ("CSC", "CLK")}

# A user's events for one ad or campaign are kept in a Redis sorted set, scored by
# serve time, for the ad server's frequency caps. A week is the longest cap window,
# and ad-manager-svc caps a count at 1,000, so neither limit can change an answer.
COUNTER_KEEP = timedelta(days=7)
COUNTER_TTL = timedelta(days=8)
COUNTER_MAX_EVENTS = 1000

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


def spend_totals(event):
    """The spend totals one billable event adds to, and how long Redis keeps each.

    Each id is a MongoDB _id in the spend collection and, after "spend:", a Redis
    key the ad server reads. The day is the UTC day the ad was served, so a
    redelivered event always lands on the same day.
    """
    day = event.served_at.strftime("%Y-%m-%d")
    totals = []
    for kind, entity_id in (("ad", event.ad_id), ("campaign", event.campaign_id)):
        totals.append((f"{kind}:{entity_id}", TOTAL_SPEND_TTL))
        totals.append((f"{kind}:{entity_id}:{day}", DAILY_SPEND_TTL))
    return totals


def prepare_database(database):
    """Create the collections and the index the transaction needs. Safe to run on every start.

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


def record_event(client, database, redis_client, event_type, event, now):
    """Count one event at most once, and charge its price if it has one.

    Returns "counted", "duplicate" or "too_old".
    """
    if now - event.served_at > COUNT_WINDOW:
        return "too_old"

    event_id = f"{event_type}:{event.bid_id}"
    other = next(t for t in EVENT_TYPES if t != event_type)
    price = charge(event_type, event)
    totals = spend_totals(event) if price else []

    def count(session):
        # The upsert only inserts when the id is new, so finding it already there means it was counted.
        inbox = database.inbox.update_one(
            {"_id": event_id},
            {"$setOnInsert": {"seen_at": now}},
            upsert=True,
            session=session,
        )
        if inbox.upserted_id is None:
            return None
        database.reports.update_one(
            {"_id": event.ad_id},
            {"$inc": {event_type: 1}, "$setOnInsert": {other: 0}},
            upsert=True,
            session=session,
        )
        spent = {}
        for spend_id, _ in totals:
            row = database.spend.find_one_and_update(
                {"_id": spend_id},
                {"$inc": {"nanos": price}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
                session=session,
            )
            spent[spend_id] = row["nanos"]
        return spent

    # with_transaction runs count() again after a transient error such as a write
    # conflict. That is safe because count() only writes inside the transaction.
    with client.start_session() as session:
        spent = session.with_transaction(count)

    result = "counted"
    if spent is None:
        # Counted before. The copy in Redis may not have been made then, so make it again.
        result = "duplicate"
        ids = [spend_id for spend_id, _ in totals]
        spent = {row["_id"]: row["nanos"] for row in database.spend.find({"_id": {"$in": ids}})} if ids else {}

    copy_spend_to_redis(redis_client, spent, dict(totals))
    add_to_counters(redis_client, counter_keys(event_type, event), event)
    return result


def add_to_counters(redis_client, keys, event):
    """Add the event to its user's frequency cap counters, and drop what no cap can reach.

    The bid id is the member and the serve time the score, so writing the same event
    again changes nothing. Like the spend copy, a failure here nacks the message, and
    the redelivery, a duplicate, writes it again.
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
    """Write new spend totals to Redis for the ad server, never lowering one.

    This runs after the transaction has committed. If Redis can't be reached the
    error goes up, the message is nacked, and the redelivery comes back here as a
    duplicate and copies the totals again.
    """
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


def make_callback(client, database, redis_client, event_type):
    def callback(message):
        try:
            event = parse_event(message.data)
        except BadEvent as exc:
            # It will never succeed, so ack it to stop the redeliveries.
            log.error("dropping unusable %s message: %s", event_type, exc)
            message.ack()
            return

        try:
            result = record_event(client, database, redis_client, event_type, event, datetime.now(timezone.utc))
        except Exception:
            # Anything else (MongoDB or Redis down, a transaction that kept failing) is worth retrying.
            log.exception("failed to record %s message", event_type)
            message.nack()
            return

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
        sys.exit("MongoDB has to be a replica set: events are counted in transactions, which a standalone server does not run")
    database = mongo[MONGODB_DATABASE]
    prepare_database(database)

    redis_client = redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, username=REDIS_USERNAME, password=REDIS_PASSWORD, decode_responses=True
    )
    redis_client.ping()

    # Credentials come from Application Default Credentials; set
    # GOOGLE_APPLICATION_CREDENTIALS to a key file for local development.
    subscriber = pubsub_v1.SubscriberClient()
    futures = [
        subscriber.subscribe(
            subscriber.subscription_path(PROJECT_ID, CLICK_SUBSCRIPTION),
            callback=make_callback(mongo, database, redis_client, "click"),
        ),
        subscriber.subscribe(
            subscriber.subscription_path(PROJECT_ID, CSC_SUBSCRIPTION),
            callback=make_callback(mongo, database, redis_client, "render"),
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
    mongo.close()
    redis_client.close()


if __name__ == "__main__":
    main()
