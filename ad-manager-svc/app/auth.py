"""API key check for the ad manager.

When the API_KEY environment variable is set, every route except /health needs a matching X-API-Key header.
When it is not set the API stays open, as it was before, and a warning is logged at startup so nobody
finds that out later.

API_KEY can hold several keys separated by commas. That is how a key is rotated: add the new one, update the
callers, then remove the old one.

Two details that are easy to get wrong:

* Keys are compared as SHA-256 digests with hmac.compare_digest. The comparison does not stop at the first
  differing byte, and hashing first means the keys' lengths do not leak either (compare_digest is documented to
  leak length for inputs of different lengths).
* A browser sends a CORS preflight (an OPTIONS request) without any custom headers, so it can never carry the
  key. Flask runs before_request functions for it as well, so OPTIONS has to be let through or the dashboard
  could not call this API at all. flask-cors adds its headers in an after_request hook, which also covers the
  401 this module returns, so the browser can read the error.
"""

import hashlib
import hmac
import logging
import os

from flask import jsonify, request

log = logging.getLogger(__name__)

API_KEY_HEADER = "X-API-Key"

# Reachable without a key so Kubernetes probes keep working.
OPEN_PATHS = frozenset({"/health"})


def configured_keys(environ=None):
    """The keys in API_KEY, split on commas, with blanks dropped."""
    raw = (os.environ if environ is None else environ).get("API_KEY", "")
    return [key.strip() for key in raw.split(",") if key.strip()]


def _digest(value):
    return hashlib.sha256(value.encode("utf-8")).digest()


def key_matches(supplied, keys):
    """True if `supplied` equals any of `keys`. Every key is checked, so the time taken does not say which one matched."""
    supplied_digest = _digest(supplied)
    matched = False
    for key in keys:
        matched |= hmac.compare_digest(supplied_digest, _digest(key))
    return matched


def install_api_key_auth(app):
    keys = configured_keys()
    if not keys:
        log.warning("API_KEY is not set, so the manager API accepts requests without a key. Set it before exposing this service.")
        return

    @app.before_request
    def require_api_key():
        if request.method == "OPTIONS" or request.path in OPEN_PATHS:
            return None
        if key_matches(request.headers.get(API_KEY_HEADER, ""), keys):
            return None
        # Returning a value from a before_request function ends the request, so the route never runs.
        return jsonify({"error": "missing or invalid API key"}), 401
