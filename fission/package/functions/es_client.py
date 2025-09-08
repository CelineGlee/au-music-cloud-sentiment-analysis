"""Common methods for our Elastic environment"""

import json
import os
from functions.logger_config import get_logger
from elasticsearch import Elasticsearch, ConnectionError, AuthenticationException
from elasticsearch.helpers import bulk
from elasticsearch.helpers import BulkIndexError

# Set up logging
logger = get_logger(__name__)

def get_es_client():
    """Get the Elastic client"""
    try:
        client = Elasticsearch(
            ["https://elasticsearch-master.elastic.svc.cluster.local:9200"],
            verify_certs=False,
            ssl_show_warn=False,
            basic_auth=("elastic", "elastic"),
            request_timeout=30
        )
        # Verify connection
        if not client.ping():
            raise ConnectionError("Failed to connect to Elasticsearch")
        logger.info("Successfully connected to Elasticsearch")
        return client
    except ConnectionError as e:
        logger.error(f"Connection error while initializing Elasticsearch client: {e}")
        raise
    except AuthenticationException as e:
        logger.error(f"Authentication error with Elasticsearch: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error initializing Elasticsearch client: {e}")
        raise

es = get_es_client()

def load_es_config(config_path="elastic_config.json"):
    """Load the Elastic config from a JSON file"""
    try:
        filepath = os.path.join(os.path.dirname(__file__), config_path)
        logger.info(f"Loading Elastic config from {filepath}")
        with open(filepath, encoding="utf-8") as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        logger.error(f"Config file not found: {filepath}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file {filepath}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading config from {filepath}: {e}")
        raise

def initialise_es_index(index_name, config_path):
    """Initialise the Elastic index with the given name"""
    try:
        config = load_es_config(config_path)
        if not es.indices.exists(index=index_name):
            es.indices.create(index=index_name, body=config)
            logger.info(f"Index {index_name} created successfully.")
        else:
            logger.info(f"Index {index_name} already exists.")
    except Exception as e:
        logger.error(f"Failed to initialize index {index_name}: {e}")
        raise

def _gendata(data, index_name):
    """Generator for bulk indexing data"""
    try:
        for post in data:
            try:
                if isinstance(post, dict):
                    post_dict = post
                elif isinstance(post, (str, bytes, bytearray)):
                    try:
                        post_dict = json.loads(post)
                        if not isinstance(post_dict, dict):
                            logger.error(f"Parsed JSON is not a dict: {post_dict}")
                            continue
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in post data: {e} - Data: {post}")
                        continue
                else:
                    logger.error(f"Unsupported data type for post: {type(post)} - Data: {post}")
                    continue

                # Verify required fields
                if "id" not in post_dict:
                    logger.error(f"Missing 'id' field in post data: {post_dict}")
                    continue

                yield {
                    "_index": index_name,
                    "_id": post_dict["id"],
                    "_source": post_dict
                }
            except Exception as e:
                logger.error(f"Error processing post for index {index_name}: {e} - Data: {post}")
                continue
    except Exception as e:
        logger.error(f"Unexpected error generating data for index {index_name}: {e}")
        raise

def insert_es_data(index_name, data):
    """Insert data into the Elastic index in bulk"""
    if not data:
        logger.warning(f"No data provided for insertion into {index_name}")
        return 0, 0
    try:
        success, failed = bulk(es, _gendata(data, index_name))
        if failed:
            logger.warning(f"Partially inserted {success} documents into {index_name}, {len(failed)} failed")
            return success, failed
        logger.info(f"Successfully inserted {success} documents into {index_name}")
        return success, 0
    except BulkIndexError as e:
        logger.error(f"Bulk insert  insert failed for {index_name}: {len(e.errors)} documents failed")
        for i, error in enumerate(e.errors):
            logger.error(f"Error {i+1}: {error}")
        return 0, len(e.errors)
    except Exception as e:
        logger.error(f"Unexpected error inserting data into {index_name}: {e}")
        raise