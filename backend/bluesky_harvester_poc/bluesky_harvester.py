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

""" bluesky-harvester"""

from datetime import datetime
from atproto import Client
import redis
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

# Environment variables (assuming these are set)
BSKY_USERNAME = "sulayee.bsky.social"
BSKY_PASSWORD = "jvs2-qkex-xi5z-42h2"

REDIS_HOST = "localhost"
REDIS_PORT = 6379

CURSOR_KEY = "bluesky:timeline:cursor"  # Single key for the cursor

# Initialize atproto client and Redis client outside the function
client = Client()
try:
    login_info = client.login(BSKY_USERNAME, BSKY_PASSWORD)
    print("Bluesky login successful!")
except Exception as e:
    print(f"Bluesky login failed: {e}")
    exit(1)

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

def main():
    """
    Fetches Bluesky timeline posts, using Redis as a checkpoint for the last processed cursor.
    Designed to be run by multiple pods.
    """
    cursor = r.get(CURSOR_KEY)
    if cursor:
        cursor = cursor.decode('utf-8')
        print(f"Retrieved cursor from Redis: {cursor}")
    else:
        print("No cursor found in Redis. Initializing from the latest posts.")

    try:
        params = {"limit": 25}
        if cursor:
            params["cursor"] = cursor

        resp = client.app.bsky.feed.get_timeline(params)

        new_cursor = resp.cursor  # Access cursor as a direct attribute
        feed = resp.feed        # Access feed as a direct attribute
        posts = feed

        # Step 3: Store the new cursor in Redis
        if new_cursor:
            r.set(CURSOR_KEY, new_cursor)
            print(f"Updated cursor in Redis: {new_cursor}")

        # Step 4: Extract and format data for Elasticsearch
        docs = []
        for post_view in posts:  # Rename 'post' to 'post_view' for clarity
            #print(post_view)
            record_view = post_view.post  # This is a PostView object
            author = record_view.author   # This is a ProfileViewBasic object

            created_at = record_view.record.created_at  # Access 'created_at' directly
            text = record_view.record.text          # Access 'text' directly

            docs.append({
                "author": author.handle,      # Access 'handle' directly
                "text": text,
                "createdAt": created_at,
                "fetchedAt": datetime.utcnow().isoformat()
            })

        print(f"docs: {docs}")

        # Prepare documents for bulk helper
        # Connect to Elasticsearch
        es = Elasticsearch(
            ["https://localhost:9200"],
            # Temporarily bypass the SSL certificate verification for local testing
            verify_certs=False, 
            ssl_show_warn=False,
            basic_auth=("elastic", "elastic"),
            request_timeout=30
        ) 

        bulk_docs = [
            {
                "_index": "bluesky-prod",  # Replace with your target index name
                "_source": doc
            }
            for doc in docs
        ]

        print(f"bulk_docs: {bulk_docs}")
        print(es.info())

        # Perform bulk upload using helpers.bulk
        try:
            success, failed = bulk(
                es,
                bulk_docs,
                raise_on_error=True,  # Set to True to raise an exception on any failure
                stats_only=False       # Set to True to return only counts, not detailed errors
            )
            if failed:
                print(f"Bulk upload completed with {failed} errors: {failed}")
            else:
                print(f"Bulk upload successful! {success} documents indexed.")
        except Exception as e:
            print(f"Error during bulk upload: {e}")

        # Close the Elasticsearch client
        es.close()

    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    main()