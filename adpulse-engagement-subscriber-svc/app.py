"""Consumes click and render events from Pub/Sub and aggregates them per ad.

Counts land in the MongoDB `reports` collection, which the ad manager's
/reports endpoints serve to the dashboard.
"""

import json
import logging
import os
import signal
import sys
from threading import Event

from google.cloud import pubsub_v1
from pymongo import MongoClient

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


def get_reports_collection(client):
    return client[MONGODB_DATABASE].reports


def record_event(collection, ad_id, event_type):
    """Increment one counter for an ad, creating the row on first sight.

    A single upsert with $inc/$setOnInsert keeps this atomic — the previous
    read-then-write lost counts whenever two messages for the same ad were
    handled concurrently.
    """
    other = next(t for t in EVENT_TYPES if t != event_type)
    collection.update_one(
        {"_id": ad_id},
        {"$inc": {event_type: 1}, "$setOnInsert": {other: 0}},
        upsert=True,
    )
    log.info("recorded %s for ad %s", event_type, ad_id)


def make_callback(collection, event_type):
    def callback(message):
        try:
            payload = json.loads(message.data.decode())
            record_event(collection, payload["adid"], event_type)
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as exc:
            # Malformed messages will never succeed; ack so they stop redelivering.
            log.error("dropping unusable %s message: %s", event_type, exc)
        except Exception:
            # Anything else (a Mongo blip) is worth retrying, so leave it unacked.
            log.exception("failed to record %s message", event_type)
            message.nack()
            return
        message.ack()

    return callback


def main():
    if not PROJECT_ID:
        sys.exit("GCP_PROJECT_ID is not set")
    if not MONGODB_URI:
        sys.exit("MONGODB_URI is not set")

    mongo = MongoClient(MONGODB_URI)
    mongo.admin.command("ping")
    collection = get_reports_collection(mongo)

    # Credentials come from Application Default Credentials; set
    # GOOGLE_APPLICATION_CREDENTIALS to a key file for local development.
    subscriber = pubsub_v1.SubscriberClient()
    futures = [
        subscriber.subscribe(
            subscriber.subscription_path(PROJECT_ID, CLICK_SUBSCRIPTION),
            callback=make_callback(collection, "click"),
        ),
        subscriber.subscribe(
            subscriber.subscription_path(PROJECT_ID, CSC_SUBSCRIPTION),
            callback=make_callback(collection, "render"),
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
