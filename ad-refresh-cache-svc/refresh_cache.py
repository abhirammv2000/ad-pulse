"""Keeps the ad server's Redis cache fresh.

Every few seconds it calls the ad manager's cache endpoints. Each call rebuilds one
slice of the cache, so this service only has to supply the timer.
"""

import logging
import os
import signal
import sys
import threading

import requests

log = logging.getLogger("refresh_cache")

REQUEST_TIMEOUT_SECONDS = 10
DEFAULT_INTERVAL_SECONDS = 15

# Campaigns first, then the ads and creatives that belong to them.
CACHE_PATHS = ("/cache/campaigns", "/cache/ads", "/cache/creatives")


def call_endpoint(session, url):
    """GET one cache endpoint. Returns True if it answered 200."""
    log.info("calling %s", url)
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        log.error("%s failed: %s", url, exc)
        return False
    if response.status_code != 200:
        log.error("%s returned status %s", url, response.status_code)
        return False
    return True


def refresh_all(session, base_url):
    """Call every cache endpoint once. One failure doesn't stop the others.

    Returns the number of endpoints that failed.
    """
    failures = 0
    for path in CACHE_PATHS:
        if not call_endpoint(session, base_url + path):
            failures += 1
    return failures


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    base_url = os.getenv("AD_MANAGER_URL")
    if not base_url:
        sys.exit("AD_MANAGER_URL is not set")
    base_url = base_url.rstrip("/")
    interval = int(os.getenv("REFRESH_INTERVAL_SECONDS", str(DEFAULT_INTERVAL_SECONDS)))

    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())

    with requests.Session() as session:
        # Event.wait doubles as the sleep, so a SIGTERM ends the loop at once
        # instead of after the rest of the interval.
        while not stop.is_set():
            refresh_all(session, base_url)
            stop.wait(interval)

    log.info("stopped")


if __name__ == "__main__":
    main()
