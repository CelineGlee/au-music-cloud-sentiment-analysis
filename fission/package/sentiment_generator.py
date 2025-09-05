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

"""Sentiment classification module. Called periodically to classify
sentiments of posts in dedicated indexes (as created in keyword_digger.py), and 
based on the keyword to index mapping in functions/keyword_config.json.
"""

from functions.sentiment_generator import process_sentiments

def main():
    """Main function to run the sentiment classification process"""
    process_sentiments("mastodon-prod-v3")
    return "Sentiment classification completed."
