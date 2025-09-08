""" Main entry point for pre-processor """

import json
import os
from functions.pre_processor import get_items_from_redis, send_items_to_elastic
from logging import getLogger
from flask import request


logger = getLogger(__name__)

def main():
    """
    Call functions related to pre-processing
    """
    try:
        logger.info("Starting Mastodon pre-processing")
        
        config_path = os.path.join(os.path.dirname(__file__), "mastodon_harvest_config.json")
        logger.info(f"Loading configuration from {config_path}")
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            logger.info("Successfully loaded configuration")
        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {config_path}: {str(e)}")
            return (f"Configuration file not found: {config_path}", 400)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file {config_path}: {str(e)}")
            return (f"Invalid JSON in configuration file: {config_path}", 400)
        except Exception as e:
            logger.error(f"Error loading configuration file {config_path}: {str(e)}")
            return (f"Error loading configuration file: {config_path}", 500)

        servers = config.get("servers", [])
        if not servers:
            logger.warning("No servers found in configuration")
            return ("No servers to process, check configuration", 400)

        processed_servers = 0
        for server, fields in servers.items():
            logger.info(f"Processing server: {server}")
            
            try:
                items = get_items_from_redis(fields['posts'])
                logger.info(f"Retrieved {len(items)} items for server {server}")
                
                if items:
                    send_items_to_elastic(items, "elastic_config.json", fields['index'])
                    logger.info(f"Successfully processed and sent items for server {server}")
                else:
                    logger.info(f"No items to send for server {server}")
                    
                processed_servers += 1
                
            except Exception as e:
                logger.error(f"Error processing server {server}: {str(e)}")
                continue

        logger.info(f"Completed processing {processed_servers} servers")
        return (f"Successfully processed {processed_servers} servers, check function log for details", 200)

    except Exception as e:
        logger.error(f"Unexpected error in main pre-processing: {str(e)}", exc_info=True)
        return (f"Unexpected error in pre-processing: {str(e)}", 500)

def preprocess_reddit():
    """Go through the Redis queue for Reddit posts and store them in Elastic"""
    try:
        raw_data = request.get_data()

        if not raw_data:
            logger.error("No data received in the request body. Headers: %s, Content-Length: %s",
                         request.headers, request.content_length)
            return ("No data received in request body", 400)

        logger.info(f"Raw data received {raw_data[:50]}...")
        
        try:
            message_str = raw_data.decode('utf-8')
            single_post_data = json.loads(message_str)
            logger.info("Successfully parsed JSON from raw_data.")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error: {e}. Data snippet: {message_str[:500]}")
            return (f"Invalid JSON format: {e}", 400)
        except UnicodeDecodeError as e:
            logger.error(f"UTF-8 decoding error: {e}. Raw data snippet (bytes): {raw_data[:500]}")
            return (f"Invalid UTF-8 data: {e}", 400)

        post_id = single_post_data.get("id", "N/A")
        logger.info(f"Processing one Reddit post (ID: {post_id}) for Elasticsearch.")
        items_to_send = [single_post_data] 
        send_items_to_elastic(items_to_send, "elastic_config_reddit.json", "reddit-prod-v6")
        
        logger.info(f"Successfully sent 1 post (ID: {post_id}) to Elasticsearch.")
        return (f"Successfully processed and sent post ID {post_id} to Elasticsearch", 200)
    except Exception as e:
        logger.error(f"Error processing Reddit comment: {str(e)}", exc_info=True)
        return (f"Error processing message: {str(e)}", 500)

def preprocess_reddit_comments():
    """Go through the Redis queue for Reddit comments and store them in Elastic"""
    try:
        raw_data = request.get_data()

        if not raw_data:
            logger.error("No data received in the request body. Headers: %s, Content-Length: %s",
                         request.headers, request.content_length)
            return ("No data received in request body", 400)

        logger.info(f"Raw data received {raw_data[:50]}...")
        
        try:
            message_str = raw_data.decode('utf-8')
            single_comment_data = json.loads(message_str)
            logger.info("Successfully parsed JSON from raw_data.")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error: {e}. Data snippet: {message_str[:500]}")
            return (f"Invalid JSON format: {e}", 400)
        except UnicodeDecodeError as e:
            logger.error(f"UTF-8 decoding error: {e}. Raw data snippet (bytes): {raw_data[:500]}")
            return (f"Invalid UTF-8 data: {e}", 400)

        comment_id = single_comment_data.get("id", "N/A")
        logger.info(f"Processing one Reddit comment (ID: {comment_id}) for Elasticsearch.")
        items_to_send = [single_comment_data] 
        send_items_to_elastic(items_to_send, "elastic_config_reddit.json", "reddit-comments-prod")
        
        logger.info(f"Successfully sent 1 comment (ID: {comment_id}) to Elasticsearch.")
        return (f"Successfully processed and sent comment ID {comment_id} to Elasticsearch", 200)
    except Exception as e:
        logger.error(f"Error processing Reddit comment: {str(e)}", exc_info=True)
        return (f"Error processing message: {str(e)}", 500)