import json
import requests
from requests.auth import HTTPBasicAuth

ES_URL = "https://localhost:9200"
SRC_INDEX = "mastodon-prod-v3"
DST_INDEX = "all-singers"
AUTH = HTTPBasicAuth("elastic", "elastic")
HEADERS = {"Content-Type": "application/json"}

VERIFY_SSL = False

with open("artists.json", "r") as f:
    data = json.load(f)
    artist_names = set(data["artists"] + data["artists_au"])
    artist_terms = [name.lower() for name in artist_names]

print(f"Loaded {len(artist_terms)} unique artist names.")


def scroll_all_docs():
    # Construct the initial search URL with scroll enabled (keeps the search context alive for 1 minute)
    url = f"{ES_URL}/{SRC_INDEX}/_search?scroll=1m"

    # Define the search request body:
    # - size: number of documents per batch
    # - query: match all documents
    # - Removed _source filter to fetch all fields
    body = {
        "size": 1000,
        "query": {"match_all": {}}
    }

    # Send the initial search request
    resp = requests.post(url, auth=AUTH, headers=HEADERS, json=body, verify=VERIFY_SSL)
    resp.raise_for_status()  # Raise an error if the request failed
    result = resp.json()

    # Extract the scroll ID and the first batch of hits
    scroll_id = result["_scroll_id"]
    hits = result["hits"]["hits"]

    # Continue fetching documents as long as there are hits
    while hits:
        # Yield each document in the current batch
        yield from hits

        # Prepare the scroll request to get the next batch
        scroll_url = f"{ES_URL}/_search/scroll"
        scroll_body = {
            "scroll": "1m",
            "scroll_id": scroll_id
        }

        # Send the scroll request
        resp = requests.post(scroll_url, auth=AUTH, headers=HEADERS, json=scroll_body, verify=VERIFY_SSL)
        resp.raise_for_status()
        result = resp.json()

        # Extract the next batch of hits
        hits = result["hits"]["hits"]

def create_index_if_needed():
    url = f"{ES_URL}/{DST_INDEX}"
    resp = requests.head(url, auth=AUTH, verify=VERIFY_SSL)
    if resp.status_code == 404:
        resp = requests.put(url, auth=AUTH, verify=VERIFY_SSL)
        resp.raise_for_status()
        print(f"Created index: {DST_INDEX}")
    else:
        print(f"Index already exists: {DST_INDEX}")

# Create target index (if not already created)
create_index_if_needed()

def contains_artist(doc_source):
    content = doc_source.get("content", "")
    content_lower = content.lower()
    return any(artist in content_lower for artist in artist_terms)


def bulk_insert(docs):
    bulk_lines = ""
    for doc in docs:
        action = {"index": {"_index": DST_INDEX, "_id": doc["_id"]}}
        # Copy the entire document source
        doc_source = doc["_source"].copy()
        # Ensure 'id' field matches '_id' if 'id' exists
        if "id" in doc_source:
            doc_source["id"] = doc["_id"]
        bulk_lines += json.dumps(action) + "\n"
        bulk_lines += json.dumps(doc_source) + "\n"

    bulk_url = f"{ES_URL}/_bulk"
    resp = requests.post(bulk_url, auth=AUTH, headers=HEADERS, data=bulk_lines, verify=VERIFY_SSL)
    resp.raise_for_status()
    print(f"Indexed {len(docs)} docs to '{DST_INDEX}'")

buffer = []
count = 0

for doc in scroll_all_docs():
    if contains_artist(doc["_source"]):
        buffer.append(doc)

    if len(buffer) >= 500:
        bulk_insert(buffer)
        count += len(buffer)
        buffer = []

if buffer:
    bulk_insert(buffer)
    count += len(buffer)

print(f"\n✅ Total indexed documents: {count}")

resp = requests.get(ES_URL, auth=AUTH, verify=VERIFY_SSL)
print("Connected to Elasticsearch" if resp.status_code == 200 else "Connection failed")