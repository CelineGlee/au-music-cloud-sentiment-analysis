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

"""
This stores functions related to pre-processing of queued 
harvested data and storing in Elastic
"""

from functions.es_client import initialise_es_index, insert_es_data
from functions.redis_client import redis_client
from functions.logger_config import get_logger
import redis
import json

logger = get_logger(__name__)

def get_items_from_redis(queue_name, n=100):
    """
    Get items from Redis queue for a given hashtag or public timeline
    """
    try:
        if not queue_name:
            raise ValueError("Queue name cannot be empty")
            
        with redis_client.pipeline() as pipe:
            for _ in range(n):
                pipe.lpop(queue_name)
            items = pipe.execute()

        items = [item for item in items if item is not None]
        logger.info(f"Retrieved {len(items)} items from {queue_name}")
        return items

    except redis.RedisError as e:
        logger.error(f"Redis error while retrieving items from {queue_name}: {str(e)}")
        raise
    except ValueError as e:
        logger.error(f"Invalid input: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_items_from_redis: {str(e)}")
        raise

def send_items_to_elastic(items, config_path, index):
    """
    Send posts to Elasticsearch
    """
    try:
        if not index:
            logger.error("No index provided, skipping Elastic insertion")
            raise ValueError("Index name is required")
            
        if not config_path:
            logger.error("No config path provided")
            raise ValueError("Config path is required")
            
        if not items:
            logger.info("No items to send to Elasticsearch")
            return

        for item in items:
            try:
                if isinstance(item, bytes):
                    json.loads(item.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"Invalid item format skipped: {str(e)}")
                continue

        initialise_es_index(index, config_path)
        
        logger.info(f"Inserting {len(items)} items to Elasticsearch index: {index}")
        insert_es_data(index, items)
        logger.info(f"Successfully inserted items to Elasticsearch index: {index}")

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in send_items_to_elastic: {str(e)}")
        raise