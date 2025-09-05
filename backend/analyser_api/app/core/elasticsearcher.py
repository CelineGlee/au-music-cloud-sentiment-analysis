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

""" elasticsearch.py """
import logging
import ssl
from functools import lru_cache
from elasticsearch import Elasticsearch

from app.config import settings

logger = logging.getLogger(__name__)

@lru_cache()
def get_elasticsearch_client() -> Elasticsearch:
    """
    Create and return an Elasticsearch client instance.
    Uses LRU cache to avoid creating multiple instances.
    """

    # Create an SSL context that skips certificate verification
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    es_config = {
        "hosts": settings.ELASTICSEARCH_HOSTS,
        "verify_certs": False,
        "ssl_context": ssl_context
    }
    
    # Add authentication if provided
    if settings.ELASTICSEARCH_USERNAME and settings.ELASTICSEARCH_PASSWORD:
        es_config["basic_auth"] = (
            settings.ELASTICSEARCH_USERNAME,
            settings.ELASTICSEARCH_PASSWORD
        )
    
    try:
        client = Elasticsearch(**es_config)
        # Verify connection
        if not client.ping():
            logger.error("Could not connect to Elasticsearch")
            raise ConnectionError("Could not connect to Elasticsearch")
        return client
    except Exception as e:
        logger.error(f"Error creating Elasticsearch client: {e}")
        raise


# Helper functions for building Elasticsearch queries
def build_date_range_query(start_time=None, end_time=None):
    """Build a date range query for Elasticsearch."""
    date_range = {}
    
    if start_time:
        date_range["gte"] = start_time
    
    if end_time:
        date_range["lte"] = end_time
    
    if date_range:
        return {"range": {"created_utc": date_range}}
    
    return None


def build_topic_query(topic=None):
    """Build a query to filter by topic."""
    if not topic:
        return None
    
    return {
        "multi_match": {
            "query": topic,
            "fields": ["title", "selftext", "topic"],
            "fuzziness": "AUTO"
        }
    }


def build_subreddit_query(subreddit=None):
    """Build a query to filter by subreddit."""
    if not subreddit:
        return None
    
    return {"term": {"subreddit.keyword": subreddit}}


def build_combined_query(topic=None, subreddit=None, start_time=None, end_time=None):
    """Build a combined query with filters."""
    must_clauses = []
    
    topic_query = build_topic_query(topic)
    if topic_query:
        must_clauses.append(topic_query)
    
    subreddit_query = build_subreddit_query(subreddit)
    if subreddit_query:
        must_clauses.append(subreddit_query)
    
    date_range_query = build_date_range_query(start_time, end_time)
    if date_range_query:
        must_clauses.append(date_range_query)
    
    if not must_clauses:
        return {"match_all": {}}
    
    return {"bool": {"must": must_clauses}}
