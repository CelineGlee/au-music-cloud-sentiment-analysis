"""Common methods etc. for Redis"""

import redis

redis_client = redis.Redis(
    host='redis-headless.redis.svc.cluster.local',
    port=6379,
    decode_responses=True,  # Automatically decode strings
)

redis_error = redis.WatchError
