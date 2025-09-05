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

""" create elastic index for bluesky """
import os
import json
from elasticsearch import Elasticsearch

print(f"Current working directory: {os.getcwd()}")

# Connect to Elasticsearch
es = Elasticsearch(
    ["https://localhost:9200"],
    # Temporarily bypass the SSL certificate verification for local testing
    verify_certs=False, 
    ssl_show_warn=False,
    basic_auth=("elastic", "elastic"),
    request_timeout=30
) 

def load_config():
    """ load elastic config to create the schema """
    with open("backend/bluesky_harvester/elastic_config.json", encoding="utf-8") as f:
        config = json.load(f)
    return config

def initialise_index(index_name, config):
    """ create the index """
    if not es.indices.exists(index=index_name):
        es.indices.create(index=index_name, body=config)
        print(f"Index {index_name} created successfully.")
    else:
        print(f"Index {index_name} already exists.")

        
def main():
    # Create the index if it doesn't exist 
    index_name = "bluesky-prod"
    config = load_config()
    initialise_index(index_name, config)

if __name__ == "__main__":
    main()