import redis

def get_redis_client():
    # Redis cloud instance details
    REDIS_HOST = 'redis-10477.c331.us-west1-1.gce.cloud.redislabs.com'
    REDIS_PORT = 10477
    REDIS_USERNAME = 'adpulse-admin'
    REDIS_PASSWORD = '***REMOVED***'

    # Create a Redis connection pool
    redis_pool = redis.ConnectionPool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        username=REDIS_USERNAME,
        password=REDIS_PASSWORD,
        decode_responses=True  # Convert byte responses to strings
    )

    # Create and return a Redis client using the connection pool
    return redis.StrictRedis(connection_pool=redis_pool)
