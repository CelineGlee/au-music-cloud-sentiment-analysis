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

"""This is called periodically to look for posts with specific keywords and pull them out into their 
own dedicated index. Config file functions/keyword_config.json contains the dictionary of dedicated 
indexes and keywords related to that index."""

import json
import os
from functions.keyword_digger import process_keywords

def main():
    """
    Main entry point for keyword processing
    """

    config_path = os.path.join(os.path.dirname(__file__), "mastodon_harvest_config.json")
    with open(config_path, "r",  encoding="utf-8") as f:
        config = json.load(f)

    keywords = config.get("digger", {})

    process_keywords(keywords)
    return "Keyword processing completed"
