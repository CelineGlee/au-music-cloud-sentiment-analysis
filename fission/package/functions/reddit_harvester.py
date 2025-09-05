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

"""RedditHarvester class to harvest posts from a subreddit using PRAW and store them in Redis."""

import random
import json
import time
from datetime import datetime, timezone
import praw
import praw.models
from prawcore.exceptions import RequestException, ResponseException
from functions.redis_client import redis_client, redis_error
from functions.logger_config import get_logger

logger = get_logger(__name__)

def read_secret_file(secret_key):
    """Read a secret from a file at the specified path."""
    name = secret_key.upper().replace("-", "_")
    path = f"/secrets/default/reddit-{secret_key}/REDDIT_{name}"
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

class PrawEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, praw.models.reddit.base.RedditBase):
            # Convert objects into dictionary
            return {k: v for k, v in vars(obj).items() if not k.startswith('_')}
        if isinstance(obj, datetime):
            return obj.timestamp()
        return super().default(obj)

class RedditHarvester:
    def __init__(self, subreddit_name=None, total_tokens=3):
        instance = random.randint(1, total_tokens)
        logger.info(f"Initialising Reddit client with token instance {instance}")
        
        try:
            credentials = {
                'client_id': read_secret_file(f'client-id-{instance}'),
                'client_secret': read_secret_file(f'client-secret-{instance}'),
                'user_agent': read_secret_file(f'user-agent-{instance}'),
                'refresh_token': read_secret_file(f'refresh-token-{instance}')
            }

            self.reddit = praw.Reddit(
                client_id=credentials['client_id'],
                client_secret=credentials['client_secret'],
                user_agent=credentials['user_agent'],
                refresh_token=credentials['refresh_token']
            )
            
            self.subreddit_name = subreddit_name
            if subreddit_name:
                self.subreddit = self.reddit.subreddit(subreddit_name)
        except Exception as e:
            logger.error(f"Failed to initialize PRAW with token instance {instance}: {e}", exc_info=True)
            raise 
        
    def flatten_reddit_post(self, post):
        """
        Flattens specified nested fields in a Reddit post into string fields to reduce Elasticsearch field count.
        """
        
        # Process media_metadata
        if "media_metadata" in post and isinstance(post["media_metadata"], dict):
            media_strings = []
            for media_id, metadata in post["media_metadata"].items():
                source = metadata.get("s", {})
                # Construct string: media_id|url|heightxwidth
                media_string = (
                    f"{media_id}|"
                    f"{source.get('u', '')}|"
                    f"{source.get('y', '')}x{source.get('x', '')}"
                )
                media_strings.append(media_string)
            post["media_metadata"] = ";".join(media_strings)
        
        # Process link_flair_richtext
        if "link_flair_richtext" in post and isinstance(post["link_flair_richtext"], list):
            # Extract 't' (text) values, skip if 't' is missing or not a string
            flair_texts = [
                item.get("t", "") for item in post["link_flair_richtext"]
                if isinstance(item.get("t"), str)
            ]
            # Join with spaces, or set empty string if no valid texts
            post["link_flair_richtext"] = " ".join(flair_texts) if flair_texts else ""
        
        # Process author_flair_richtext
        if "author_flair_richtext" in post and isinstance(post["author_flair_richtext"], list):
            # Extract 't' (text) values, skip if 't' is missing or not a string
            author_flair_texts = [
                item.get("t", "") for item in post["author_flair_richtext"]
                if isinstance(item.get("t"), str)
            ]
            # Join with spaces, or set empty string if no valid texts
            post["author_flair_richtext"] = " ".join(author_flair_texts) if author_flair_texts else ""
        
        return post
    
    def flatten_reddit_comment(self, comment):
        """
        Flattens specified nested fields in a Reddit comment into string fields to reduce Elasticsearch field count.
        """        
        # Process author_flair_richtext
        if "author_flair_richtext" in comment and isinstance(comment["author_flair_richtext"], list):
            flair_texts = [
                item.get("t", "") for item in comment["author_flair_richtext"]
                if isinstance(item.get("t"), str)
            ]
            comment["author_flair_richtext_string"] = " ".join(flair_texts) if flair_texts else ""
            del comment["author_flair_richtext"]
        
        # Process all_awardings
        if "all_awardings" in comment and isinstance(comment["all_awardings"], list):
            award_strings = [
                f"{award.get('id', '')}:{award.get('name', '')}:{award.get('count', 0)}"
                for award in comment["all_awardings"]
                if isinstance(award, dict)
            ]
            comment["all_awardings_string"] = ";".join(award_strings) if award_strings else ""
            del comment["all_awardings"]
        
        # Process awarders
        if "awarders" in comment and isinstance(comment["awarders"], list):
            comment["awarders_string"] = ";".join(str(awarder) for awarder in comment["awarders"]) if comment["awarders"] else ""
            del comment["awarders"]
        
        # Process user_reports
        if "user_reports" in comment and isinstance(comment["user_reports"], list):
            report_strings = [
                f"{report.get('user', '')}:{report.get('reason', '')}"
                for report in comment["user_reports"]
                if isinstance(report, dict)
            ]
            comment["user_reports_string"] = ";".join(report_strings) if report_strings else ""
            del comment["user_reports"]
        
        # Process mod_reports
        if "mod_reports" in comment and isinstance(comment["mod_reports"], list):
            report_strings = [
                f"{report.get('user', '')}:{report.get('reason', '')}"
                for report in comment["mod_reports"]
                if isinstance(report, dict)
            ]
            comment["mod_reports_string"] = ";".join(report_strings) if report_strings else ""
            del comment["mod_reports"]
        
        # Process gildings
        if "gildings" in comment and isinstance(comment["gildings"], dict):
            gilding_strings = [
                f"{award_type}:{count}"
                for award_type, count in comment["gildings"].items()
                if isinstance(count, (int, str))
            ]
            comment["gildings_string"] = ";".join(gilding_strings) if gilding_strings else ""
            del comment["gildings"]
        
        return comment
    
    def convert_to_json(self, submission):
        """Convert a PRAW submission object to a JSON-serializable dictionary."""
        try:
            if not isinstance(submission, (praw.models.Submission, praw.models.Comment)):
                logger.warning(f"Item is not a Reddit object: {type(submission)}")
                return None
            json_data = json.loads(json.dumps(submission, cls=PrawEncoder))
            
            # Convert UNIX timestamps to ISO format
            date_fields = ['created', 'created_utc', 'approved_at_utc', 'banned_at_utc', 'edited']
            for field in date_fields:
                if field in json_data and isinstance(json_data[field], (int, float)):
                    json_data[field] = datetime.fromtimestamp(json_data[field], tz=timezone.utc).isoformat()

            return json_data
        except Exception as e:
            logger.error(f"Failed to convert submission to JSON: {e}", exc_info=True)
            return None

    def get_timeline_id_key(self):
        if not self.subreddit_name:
            raise ValueError("Subreddit name required for timeline ID key")
        return f"reddit:{self.subreddit_name}:ids" 

    def get_timeline_queue_key(self):
        if not self.subreddit_name:
            raise ValueError("Subreddit name required for timeline queue key")
        return f"reddit:{self.subreddit_name}:queue"

    def initialise_timeline_ids(self):
        """Initialize min_id and max_id in Redis for a subreddit if not set."""
        if not self.subreddit_name:
            raise ValueError("Subreddit name required for initializing timeline IDs")
        key = self.get_timeline_id_key()
    
        if not redis_client.exists(key):
            posts = list(self.subreddit.new(limit=1))
            if posts:
                post_id = posts[0].fullname
                max_id = str(post_id)
                min_id = str(post_id)
                redis_client.hset(key, mapping={'min_id': min_id, 'max_id': max_id})
            else:
                raise ValueError(f"No posts found for subreddit {self.subreddit_name}")
            return min_id, max_id
    
        return redis_client.hget(key, 'min_id'), redis_client.hget(key, 'max_id')
    
    def fetch_old_posts(self, limit=100):
        """Fetch old posts from the subreddit and store them in Redis."""
        if not self.subreddit_name:
            raise ValueError("Subreddit name required for fetching posts")
        key = self.get_timeline_id_key() 
        self.initialise_timeline_ids()
        
        with redis_client.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(key)
                    current_id = pipe.hget(key, 'min_id')
                    logger.info(f"Fetching posts for r/{self.subreddit_name} from current id: {current_id}...")
                    
                    posts = list(self.subreddit.new(limit=limit, params={'after': current_id}))
                    if not posts:
                        pipe.unwatch()
                        return []
                                      
                    pipe.multi()
                    pipe.hset(key, 'min_id', posts[-1].fullname)
                    pipe.execute()
                    
                    logger.info(f"Successfully fetched {len(posts)} submissions from r/{self.subreddit_name} from {current_id} to {posts[-1].fullname}")                    
                    json_posts = [self.convert_to_json(post) for post in posts]
                    return [self.flatten_reddit_post(post) for post in json_posts]
                except redis_error:
                    continue
                
    def fetch_new_posts(self, limit=100):
        """Fetch newer posts for a subreddit since the current max_id."""
        if not self.subreddit_name:
            raise ValueError("Subreddit name required for fetching posts")
        key = self.get_timeline_id_key() 
        self.initialise_timeline_ids()
        
        with redis_client.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(key)
                    current_id = pipe.hget(key, 'max_id')
                    logger.info(f"Fetching posts for r/{self.subreddit_name} from current id: {current_id}...")
                    
                    posts = list(self.subreddit.new(limit=limit, params={'before': current_id}))
                    if not posts:
                        pipe.unwatch()
                        return []
                                      
                    pipe.multi()
                    pipe.hset(key, 'max_id', posts[0].fullname)
                    pipe.execute()
                    
                    logger.info(f"Successfully fetched {len(posts)} posts from r/{self.subreddit_name} from {current_id} to {posts[-1].fullname}")
                    
                    json_posts = [self.convert_to_json(post) for post in posts]
                    return [self.flatten_reddit_post(post) for post in json_posts]
                except redis_error:
                    continue
                
    def fetch_comments(self, post_id, max_retries=2, initial_delay=2):
        """Fetch all comments for a given post ID."""
        try:
            submission = self.reddit.submission(id=post_id)
            
            for attempt in range(max_retries):
                try:
                    submission.comments.replace_more(limit=None)
                    comments = submission.comments.list()
                    
                    cleaned_comments = [self.convert_to_json(comment) for comment in comments]
                    # Remove None values from the list due to failed cleaning
                    cleaned_comments = [c for c in cleaned_comments if c is not None]
                    cleaned_comments = [self.flatten_reddit_comment(comment) for comment in cleaned_comments]
                    
                    logger.info(f"Successfully fetched {len(cleaned_comments)} comments for post {post_id}.")
                    return cleaned_comments
                
                except (RequestException, ResponseException) as e:
                    if attempt < max_retries - 1:
                        delay = initial_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Rate limit hit for post {post_id}. Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                    else:
                        logger.error(f"Max retries reached for post {post_id}: {str(e)}")
                        return []
        except Exception as e:
            # Handle other unexpected errors
            logger.error(f"Error fetching comments for post {post_id}: {str(e)}")
            return []

def store_new_posts(cleaned_posts, subreddit_name):
    """Stores cleaned posts as a JSON list in a unified Redis queue."""
    # Unified queue for inserting into ES
    queue_key_es = "reddit:posts:queue"
    # Unified queue for getting comments
    queue_key_comments = "reddit:fetch_comments:queue"
    
    with redis_client.pipeline() as pipe:
        for post in cleaned_posts:
            pipe.rpush(queue_key_es, json.dumps(post))
            pipe.rpush(queue_key_comments, post['id'])
        pipe.execute()
    
    logger.info(f"Successfully stored {len(cleaned_posts)} posts in Redis for subreddit {subreddit_name}.")
    return len(cleaned_posts)

def store_new_comments(cleaned_comments, subreddit_name):
    """Stores cleaned comments as a JSON list in a unified Redis queue."""
    if not cleaned_comments:
        logger.info(f"No comments to store for {subreddit_name}.")
        return 0
    queue_key = "reddit:comments:queue"
    for comment in cleaned_comments:
        redis_client.rpush(queue_key, json.dumps(comment))
    logger.info(f"Successfully stored {len(cleaned_comments)} comments in Redis for subreddit {subreddit_name}.")
    return len(cleaned_comments)

def fetch_comments_worker(post_id=None):
    """Worker function for Fission to fetch comments for a Reddit post and store it in Redis.
    If post_id is provided, process that post; otherwise, pop from the queue.
    Returns the number of comments retrieved.
    """
    try:
        # If post_id is not provided, pop from the queue
        if post_id is None:
            post_id = redis_client.lpop("reddit:fetch_comments:queue")
            if post_id is None:
                logger.info("No posts in fetch_comments queue")
                return 0

        logger.info(f"Processing comments for post {post_id}")

        # Initialize harvester and fetch comments
        try:
            harvester = RedditHarvester()
            comments = harvester.fetch_comments(post_id)
        except praw.exceptions.APIException as e:
            # Put the post_id back in the queue if rate limit is hit
            if "RATELIMIT" in str(e):
                logger.warning(f"Rate limit hit for post {post_id}. Requeuing post_id.")
                # Requeue the post_id
                redis_client.rpush("reddit:fetch_comments:queue", post_id)
                return 0
            else:
                logger.error(f"API error fetching comments for post {post_id}: {e}", exc_info=True)
                raise RuntimeError(f"Error fetching comments: {e}")
        except Exception as e:
            logger.error(f"Failed to fetch comments for post {post_id}: {e}", exc_info=True)
            raise RuntimeError(f"Error fetching comments: {e}")

        # Store comments
        try:
            store_new_comments(comments, post_id)
        except Exception as e:
            logger.error(f"Failed to store comments for post {post_id}: {e}", exc_info=True)
            raise RuntimeError(f"Error storing comments: {e}")

        logger.info(f"Successfully processed {len(comments)} comments for post {post_id}")
        return len(comments)

    except Exception as e:
        logger.error(f"Error in fetch_comments_worker: {e}", exc_info=True)
        raise
    
def fetch_posts_worker(subreddit_name):
    """Worker function for Fission to fetch old and new posts from a subreddit and store them in Redis."""
    try:
        logger.info(f"Starting fetch_posts_worker for subreddit {subreddit_name}")

        # Initialize harvester and fetch old posts
        try:
            harvester = RedditHarvester(subreddit_name)
            old_posts = harvester.fetch_old_posts(limit=100)
            new_posts = harvester.fetch_new_posts(limit=100)
        except Exception as e:
            logger.error(f"Failed to fetch posts for subreddit {subreddit_name}: {e}", exc_info=True)
            raise RuntimeError(f"Error fetching posts: {e}")

        # Store posts
        try:
            old_post_count = store_new_posts(old_posts, subreddit_name)
            new_post_count = store_new_posts(new_posts, subreddit_name)
        except Exception as e:
            logger.error(f"Failed to store posts for subreddit {subreddit_name}: {e}", exc_info=True)
            raise RuntimeError(f"Error storing posts: {e}")

        if old_post_count > 0:
            logger.info(f"Successfully processed {old_post_count} old posts for subreddit {subreddit_name}")
        else:
            logger.info(f"No old posts found for subreddit {subreddit_name}")
            
        if new_post_count > 0:
            logger.info(f"Successfully processed {new_post_count} new posts for subreddit {subreddit_name}")
        else:
            logger.info(f"No new posts found for subreddit {subreddit_name}")
        return old_post_count + new_post_count

    except Exception as e:
        logger.error(f"Error in fetch_posts_worker for subreddit {subreddit_name}: {e}", exc_info=True)
        raise