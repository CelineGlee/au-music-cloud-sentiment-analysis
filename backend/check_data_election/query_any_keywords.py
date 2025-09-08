import requests
from requests.auth import HTTPBasicAuth

url = "https://localhost:9200/mastodon-all-index/_count"
auth = HTTPBasicAuth("elastic", "elastic")

# Ask about Dutton or Albo
# query = {
#     "query": {
#         "bool": {
#             "should": [
#                 { "match_phrase": { "content": "peter dutton" } },
#                 { "match": { "content": "peterdutton" } },
#                 { "match": { "content": "dutton" } }
#             ],
#             "minimum_should_match": 1
#         }
#     }
# }

query = {
    "query": {
        "bool": {
            "should": [
                { "match_phrase": { "content": "anthony albanese" } },
                { "match": { "content": "albanese" } },
                { "match": { "content": "albo" } },
                { "match": { "content": "anthonyalbanese" } },
            ],
            "minimum_should_match": 1
        }
    }
}

query = {
    "query": {
        "bool": {
            "should": [
                { "match_phrase": { "content": "kylie minogue" } },
                { "match_phrase": { "content": "kylie" } },
                { "match_phrase": { "content": "minogue" } },
                { "match_phrase": { "content": "kylieminogue" } }
            ],
            "minimum_should_match": 1
        }
    }
}

response = requests.post(url, auth=auth, json=query, verify=False)

if response.status_code == 200:
    print("Doc count", response.json().get("count"))
else:
    print("Query failed", response.text)