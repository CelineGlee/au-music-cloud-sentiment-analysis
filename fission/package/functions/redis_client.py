"""
===============================================================================
Team 81

Members:
- Adam McMillan (1393533)
- Ryan Kuang (1547320)
- Tim Shen (1673715)
- Yili Liu (883012)
- Yuting Cai (1492060)

===============================================================================
"""

"""Common methods etc. for Redis"""

import redis

redis_client = redis.Redis(
    host='redis-headless.redis.svc.cluster.local',
    port=6379,
    decode_responses=True,  # Automatically decode strings
)

redis_error = redis.WatchError
