from elasticsearch import helpers
from functions.es_client import get_es_client

# Connect
es = get_es_client()

MAX_DOCS_PER_RUN = 500
QUERY_SIZE = 200

def make_keyword_query(keywords, check_field):
    return {
        "query": {
            "bool": {
                "must_not": {"exists": {"field": check_field}},
                "should": [{"match_phrase": {"content": keyword}} for keyword in keywords],
                "minimum_should_match": 1
            }
        }
    }

def process_keywords(keyworddict):
    for entry in keyworddict:
        check_field = "extracted_to_" + entry['to-index']
        query = make_keyword_query(entry['keywords'], check_field)

        docs = helpers.scan(es, index=entry['from-index'], query=query, size=QUERY_SIZE)
        actions = []
        count = 0

        for doc in docs:
            if count >= MAX_DOCS_PER_RUN:
                break

            doc_id = doc["_id"]
            source = doc["_source"]

            # Add to index-to-new-index action
            actions.append({
                "_op_type": "index",
                "_index": entry['to-index'],
                "_id": doc_id,
                "_source": source
            })

            # Add to update-original-doc action
            actions.append({
                "_op_type": "update",
                "_index": entry['from-index'],
                "_id": doc_id,
                "doc": {check_field: True}
            })

            count += 1

        if actions:
            helpers.bulk(es, actions)
            print(f"Processed {count} docs from '{entry['from-index']}' to '{entry['to-index']}'")
