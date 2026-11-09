"""Consumes click and render events from Pub/Sub and counts each one exactly once.

Pub/Sub delivers at least once, and can deliver a message again even after it
was acked. A tracking URL can also be opened many times. So every event has an
id, its type plus the id of the bid it belongs to, and the count and a record of
that id are written in one MongoDB transaction. If the record is already there,
the event was counted before and the message is only acked.

Counts land in the MongoDB `reports` collection, which the ad manager's
/reports endpoints serve to the dashboard.
"""

import json
import logging
import os
import signal
import sys
from datetime import datetime, timedelta, timezone
from threading import Event

from google.cloud import pubsub_v1
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
CLICK_SUBSCRIPTION = os.getenv("CLICK_SUBSCRIPTION_ID", "click-service-topic-sub")
CSC_SUBSCRIPTION = os.getenv("CSC_SUBSCRIPTION_ID", "csc-service-topic-sub")
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "ad_pulse")

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


class BadEvent(ValueError):
    """A message that can never be counted, so it is acked and dropped."""


def parse_event(data):
    """Return (ad id, bid id, serve time) from a message body, or raise BadEvent."""
    try:
        payload = json.loads(data.decode())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BadEvent(f"not JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise BadEvent("not a JSON object")

    ad_id = payload.get("adid")
    bid_id = payload.get("bidid")
    served = payload.get("requesttimestamp")
    if not isinstance(ad_id, str) or not ad_id:
        raise BadEvent("no adid")
    if not isinstance(bid_id, str) or not bid_id:
        raise BadEvent("no bidid")
    if isinstance(served, bool) or not isinstance(served, int):
        raise BadEvent("no requesttimestamp")
    try:
        served_at = datetime.fromtimestamp(served, tz=timezone.utc)
    except (OverflowError, OSError, ValueError) as exc:
        raise BadEvent(f"requesttimestamp out of range: {served}") from exc
    return ad_id, bid_id, served_at


def prepare_database(database):
    """Create the collections and the index the transaction needs. Safe to run on every start.

    The collections are made here, outside any transaction, so two transactions
    never race to create one.
    """
    for name in ("reports", "inbox"):
        try:
            database.create_collection(name)
        except CollectionInvalid:
            pass  # it already exists
    # MongoDB deletes an inbox record this long after it was written.
    database.inbox.create_index("seen_at", expireAfterSeconds=int(INBOX_TTL.total_seconds()))


def record_event(client, database, event_type, ad_id, bid_id, served_at, now):
    """Count one event at most once. Returns "counted", "duplicate" or "too_old"."""
    if now - served_at > COUNT_WINDOW:
        return "too_old"

    event_id = f"{event_type}:{bid_id}"
    other = next(t for t in EVENT_TYPES if t != event_type)

    def count(session):
        # The upsert only inserts when the id is new, so finding it already there means it was counted.
        inbox = database.inbox.update_one(
            {"_id": event_id},
            {"$setOnInsert": {"seen_at": now}},
            upsert=True,
            session=session,
        )
        if inbox.upserted_id is None:
            return False
        database.reports.update_one(
            {"_id": ad_id},
            {"$inc": {event_type: 1}, "$setOnInsert": {other: 0}},
            upsert=True,
            session=session,
        )
        return True

    # with_transaction runs count() again after a transient error such as a write
    # conflict. That is safe because count() only writes inside the transaction.
    with client.start_session() as session:
        counted = session.with_transaction(count)
    return "counted" if counted else "duplicate"


def make_callback(client, database, event_type):
    def callback(message):
        try:
            ad_id, bid_id, served_at = parse_event(message.data)
        except BadEvent as exc:
            # It will never succeed, so ack it to stop the redeliveries.
            log.error("dropping unusable %s message: %s", event_type, exc)
            message.ack()
            return

        try:
            result = record_event(
                client, database, event_type, ad_id, bid_id, served_at, datetime.now(timezone.utc)
            )
        except Exception:
            # Anything else (MongoDB down, a transaction that kept failing) is worth retrying.
            log.exception("failed to record %s message", event_type)
            message.nack()
            return

        if result == "too_old":
            log.warning("not counting %s for ad %s: it was served at %s, too long ago", event_type, ad_id, served_at)
        else:
            log.info("%s %s for ad %s", result, event_type, ad_id)
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

    # Credentials come from Application Default Credentials; set
    # GOOGLE_APPLICATION_CREDENTIALS to a key file for local development.
    subscriber = pubsub_v1.SubscriberClient()
    futures = [
        subscriber.subscribe(
            subscriber.subscription_path(PROJECT_ID, CLICK_SUBSCRIPTION),
            callback=make_callback(mongo, database, "click"),
        ),
        subscriber.subscribe(
            subscriber.subscription_path(PROJECT_ID, CSC_SUBSCRIPTION),
            callback=make_callback(mongo, database, "render"),
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


if __name__ == "__main__":
    main()
