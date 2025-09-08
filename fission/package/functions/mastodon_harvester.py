"""
This stores functions related to harvesting of data from external APIs.
Will probably be necessary to split this out into multiple files and then 
import each one into package/harvester.py
"""
import json
from mastodon import Mastodon
from bs4 import BeautifulSoup
from functions.redis_client import redis_client, redis_error
from datetime import datetime
from functions.logger_config import get_logger

logger = get_logger(__name__)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class MastodonHarvester:
    def __init__(self, api_base_url, server_key, id_key):
        try:
            self.mastodon_client = Mastodon(
                api_base_url=api_base_url,
                ratelimit_method='wait'
            )
            # Test connection by fetching server information
            self.mastodon_client.instance()
            
            self.api_base_url = api_base_url
            self.server_key = server_key
            self.id_key = id_key
        except Exception as e:
            logger.error(f"Failed to initialize Mastodon client for {api_base_url}: {e}", exc_info=True)
            raise

    def initialise_timeline_ids(self, idqueue):
        """Initialize min_id and max_id in Redis for a hashtag or public timeline if not set."""
        if not redis_client.exists(idqueue):

            posts = self.mastodon_client.timeline_public(limit=40, local=True)

            if posts:
                max_id = str(posts[0]['id'])
                min_id = str(posts[-1]['id'])
                redis_client.hset(idqueue, mapping={'min_id': min_id, 'max_id': max_id})
            else:
                raise ValueError(
                    f"No posts found for target server!"
                )
            return min_id, max_id
        
        return redis_client.hget(idqueue, 'min_id'), redis_client.hget(idqueue, 'max_id')

    def remove_html(self, html_content):
        '''Remove HTML tags from the content'''
        content_text = BeautifulSoup(html_content, 'html.parser').get_text()
        return content_text

    def convert_to_json(self, post):
        """Convert a Mastodon Status object to a JSON-serializable dictionary."""
        try:
            # Note: Original code had an incomplete isinstance check; assuming it checks for dict (Mastodon post)
            # if not isinstance(post, dict):
            #     logger.warning(f"Item is not a Mastodon post: {type(post)}")
            #     return None
            return json.dumps(post, cls=DateTimeEncoder, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to convert post to JSON: {e}", exc_info=True)
            return None

    def _fetch_posts(self, fetch_func, id_field, limit, is_newer):
        """Function to fetch posts and update min_id/max_id atomically."""
        self.initialise_timeline_ids(self.id_key)
        
        with redis_client.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(self.id_key)
                    current_id = pipe.hget(self.id_key, id_field)
                    logger.info(f"Fetching posts for {self.server_key} from {current_id}...")
                    
                    posts = fetch_func(current_id, limit)
                    if not posts:
                        pipe.unwatch()
                        logger.info(f"No more posts to retreive for {self.server_key}")
                        return []
                    
                    new_id = str(posts[0]['id']) if is_newer else str(posts[-1]['id'])
                    
                    cleaned_posts = [self.convert_to_json(post) for post in posts]
                    
                    pipe.multi()
                    pipe.hset(self.id_key, id_field, new_id)
                    pipe.execute()
                    
                    logger.info(f"Successfully fetched {len(posts)} posts from {current_id} to {new_id} on {self.server_key}")
                    
                    return cleaned_posts
                except redis_error:
                    continue

    def fetch_new_posts(self, limit=40):
        """Fetch newer public timeline posts since the current max_id."""
        def fetch_func(current_id, limit):
            return self.mastodon_client.timeline_public(min_id=current_id, limit=limit, local=True)
        
        return self._fetch_posts(fetch_func, 'max_id', limit, is_newer=True)

    def fetch_old_posts(self, limit=40):
        """Fetch older public timeline posts since the current min_id."""
        def fetch_func(current_id, limit):
            return self.mastodon_client.timeline_public(max_id=current_id, limit=limit, local=True)
        
        return self._fetch_posts(fetch_func, 'min_id', limit, is_newer=False)

    def store_new_posts(self, cleaned_posts):
        """Stores cleaned posts as a JSON list in Redis."""
        if not cleaned_posts:
            logger.info(f"No posts to store for {self.server_key}.")
            return 0
        for post in cleaned_posts:
            redis_client.rpush(self.server_key, post)
        logger.info(f"Successfully stored {len(cleaned_posts)} posts in Redis for {self.server_key}.")
        return len(cleaned_posts)
    
def harvest(request):
    """Harvest function, to be called for each server/hashtag combination."""

    # Get the query parameters
    action = request.args.get('action', '').lower()
    server = request.args.get('server', '').lower()
    postqueue = request.args.get('postqueue', '').lower()
    idqueue = request.args.get('idqueue', '').lower()

    logger.info(f"Harvesting posts {action} from {server}")

    try:
        harvester = MastodonHarvester(server, postqueue, idqueue)

        if action == 'new':
            posts = harvester.fetch_new_posts(limit=40)
        elif action == 'old':
            posts = harvester.fetch_old_posts(limit=40)
        else:
            return (
                f"Invalid action: {action}. Use 'new' to fetch new posts or 'old' to fetch older posts.",
                400,
            )

        num_stored = harvester.store_new_posts(posts)

        if posts:
            first_post = json.loads(posts[0])
            last_post = json.loads(posts[-1])
            start_time, end_time = last_post['created_at'], first_post['created_at']
            return (
                f"Harvested and stored {num_stored} posts from {server} from "
                f"{start_time} to {end_time}",
                200,
            )
        else:
            return f"No new posts harvested from {server}.", 200

    except Exception as e:
        logger.error(f"Error during harvesting from {server}: {e}", exc_info=True)
        return f"Error harvesting posts: {str(e)}", 500