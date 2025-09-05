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

"""Main entry point for harvester"""

import json
import random
import time
import os
import urllib.parse
import requests
from flask import request, jsonify
import functions.mastodon_harvester as mst
from functions.reddit_harvester import fetch_comments_worker, fetch_posts_worker
from functions.logger_config import get_logger

logger = get_logger(__name__)

DOMAIN = "http://router.fission.svc.cluster.local:80"

def harvest_mastodon():
    """Entry point for individual harvest operations (old vs new, different servers)."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), "mastodon_harvest_config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"Error loading Mastodon config: {str(e)}")
        return jsonify({"status": "error", "message": "Failed to load config"}), 500

    try:
        result = mst.harvest(request)
        logger.info("Mastodon harvest request processed successfully.")
        return result
    except Exception as e:
        logger.error(f"Error in Mastodon harvest processing: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def harvest_reddit():
    """Entry point for reddit harvest operations (old vs new, different servers)."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), "reddit_harvest_config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        subreddits = config.get("subreddits")

        total_postcount = 0
        for subreddit in subreddits:
            postcount = fetch_posts_worker(subreddit)
            total_postcount += postcount
            time.sleep(5)
        
        logger.info(f"Harvested {total_postcount} posts from Reddit subreddits.")
        
        return jsonify({
            "status": "success",
            "subreddits": subreddits,
            "posts_harvested": total_postcount
        }), 200
    
    except Exception as e:
        logger.error(f"Error harvesting posts from Reddit: {str(e)}")
        
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def harvest_reddit_comments():
    """Fission function to harvest comments from Reddit posts, triggered by MQTrigger."""
    try:
        # Get the message (post ID) from the request body
        message = request.get_data(as_text=True)
        if not message:
            logger.info("No post ID provided in request")
            return jsonify({
                "status": "error",
                "message": "No post ID provided"
            }), 400

        post_id = message.strip()
        logger.info(f"Processing comments for post {post_id}")

        # Call fetch_comments_worker with the post ID
        commentcount = fetch_comments_worker(post_id=post_id)
        
        logger.info(f"Harvested {commentcount} comments for post {post_id}")
        
        return jsonify({
            "status": "success",
            "post_id": post_id,
            "comments_harvested": commentcount
        }), 200
    
    except Exception as e:
        logger.error(f"Error harvesting comments for post {post_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def mastodon_entry():
    """
    Entry point for the Mastodon harvester. This is called periodically by fission.
    """
    try:
        config_path = os.path.join(os.path.dirname(__file__), "mastodon_harvest_config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        servers = config.get("servers", [])

        for server, fields in servers.items():
            try:
                query_old = urllib.parse.urlencode({
                    "action": "old",
                    "server": server,
                    "postqueue": fields['posts'],
                    "idqueue": fields['ids']
                })
                query_new = urllib.parse.urlencode({
                    "action": "new",
                    "server": server,
                    "postqueue": fields['posts'],
                    "idqueue": fields['ids']
                })

                url_old = f"{DOMAIN}/harvest-mastodon?{query_old}"
                url_new = f"{DOMAIN}/harvest-mastodon?{query_new}"

                r_old = requests.get(url_old)
                r_old.raise_for_status()
                logger.info(f"Triggered old post harvesting for server {server}: {r_old.status_code}")

                r_new = requests.get(url_new)
                r_new.raise_for_status()
                logger.info(f"Triggered new post harvesting for server {server}: {r_new.status_code}")

            except Exception as e:
                logger.error(f"Error triggering harvest for server {server}: {str(e)}")

        return "Mastodon harvesting round complete"

    except Exception as e:
        logger.error(f"Error in mastodon_entry: {str(e)}")
        return "Mastodon harvesting round failed"
    

# def mastodon_entry():
#     """
#     Entry point for the Mastodon harvester. This is called periodically by fission.
#     """

#     # Load config
#     config_path = os.path.join(os.path.dirname(__file__), "mastodon_harvest_config.json")
#     with open(config_path, "r", encoding="utf-8") as f:
#         config = json.load(f)
#     servers = config.get("servers", [])

#     # perform all harvesting actions for each server
#     for server, fields in servers.items():
#         # URL-encoded query parameters for old and new actions
#         query_old = urllib.parse.urlencode({"action": "old", "server": server, "postqueue": fields['posts'], "idqueue": fields['ids']})
#         query_new = urllib.parse.urlencode({"action": "new", "server": server, "postqueue": fields['posts'], "idqueue": fields['ids']})

#         # General posts (not hashtag-specific)
#         url_old = f"{DOMAIN}/harvest-mastodon?{query_old}"
#         requests.get(url_old)

#         url_new = f"{DOMAIN}/harvest-mastodon?{query_new}"
#         requests.get(url_new)

#     return "Mastodon harvesting round complete"