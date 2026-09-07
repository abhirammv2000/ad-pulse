import os

import redis

_client = None


def get_redis_client():
    """Return the shared Redis client, building it on first use.

    Configuration comes from REDIS_HOST / REDIS_PORT / REDIS_USERNAME /
    REDIS_PASSWORD. Only the host is required; the rest have sane defaults so a
    plain local `redis-server` works with no configuration at all.
    """
    global _client
    if _client is None:
        pool = redis.ConnectionPool(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            username=os.getenv("REDIS_USERNAME") or None,
            password=os.getenv("REDIS_PASSWORD") or None,
            decode_responses=True,  # Convert byte responses to strings
        )
        _client = redis.StrictRedis(connection_pool=pool)
    return _client
