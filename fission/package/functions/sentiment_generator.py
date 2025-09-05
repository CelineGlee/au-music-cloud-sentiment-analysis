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

import requests
import torch
from elasticsearch import Elasticsearch
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Connect to Elasticsearch
es = Elasticsearch(
    ['https://localhost:9200'],
    basic_auth=('elastic', 'elastic'),  # Use basic_auth instead of http_auth
    verify_certs=False,
    ssl_show_warn=False,
    request_timeout=30
)

if es.ping():
    print("Successfully connected to Elasticsearch!")
else:
    print("Failed to connect to Elasticsearch")
    exit(1)

# Function to safely check if index exists
def safe_index_exists(index_name):
    try:
        return es.indices.exists(index=index_name)
    except Exception as e:
        print(f"Error checking if index {index_name} exists: {e}")
        return False

# Load CardiffNLP RoBERTa model
print("Loading sentiment analysis model...")
MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
print("Model loaded successfully")

# Move model to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Function to get sentiment score
def get_sentiment(text):
    if not text:
        return {"negative": 0.0, "neutral": 0.0, "positive": 0.0}

    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)

    # Perform inference
    with torch.no_grad():
        outputs = model(**inputs)

    scores = torch.nn.functional.softmax(outputs.logits, dim=1)
    scores_dict = {
        "negative": scores[0][0].item(),
        "neutral": scores[0][1].item(),
        "positive": scores[0][2].item()
    }
    return scores_dict

# Update mapping for both indice
def index_mapping(index_name):
    if not safe_index_exists(index_name):
        print(f"Index {index_name} does not exist. Skipping mapping update.")
        return False

    sentiment_mapping = {
        "properties": {
            "properties": {
                "negative": {"type": "float"},
                "neutral": {"type": "float"},
                "positive": {"type": "float"}
            }
        },
        "sentiment_label": {"type": "keyword"}
    }

    try:
        es.indices.put_mapping(body=sentiment_mapping, index=index_name)
        print(f"Updated mapping for {index_name}")
        return True
    except Exception as e:
        print(f"Error updating mapping for {index_name}: {e}")
        return False

# Process documents in an index
def process_index(index_name):
    total_docs = es.count(index=index_name)["count"]
    print(f"Processing {index_name}: {total_docs} documents")

    # Process documents in batches
    batch_size = 100
    for i in range(0, total_docs, batch_size):
        print(f"Processing batch {i // batch_size + 1} of {(total_docs // batch_size) + 1}")

        # Query documents
        response = es.search(
            index=index_name,
            body={
                "query": {
                    "bool": {
                        "must_not": {
                            "exists": {
                                "field": "roberta_sentiment_label"
                            }
                        }
                    }
                },
                "size": batch_size,
                "from": i,
                "_source": ["id", "content"]
            }
        )

        # Process each document
        success_count = 0
        error_count = 0
        for hit in tqdm(response["hits"]["hits"]):
            doc_id = hit["_id"]

            # Check if content exists and is a string
            if "content" not in hit["_source"]:
                print(f"Document {doc_id} has no content field. Skipping.")
                continue

            content = hit["_source"].get("content", "")

            if not isinstance(content, str):
                print(f"Document {doc_id} content is not a string. Skipping.")
                continue

            # Get sentiment scores
            sentiment_scores = get_sentiment(content)
            sentiment_label = max(sentiment_scores, key=sentiment_scores.get)

            # Update document with NEW fields that won't interfere with existing ones
            try:
                es.update(
                    index=index_name,
                    id=doc_id,
                    body={
                        "doc": {
                            "roberta_sentiment": {
                                "negative": sentiment_scores["negative"],
                                "neutral": sentiment_scores["neutral"],
                                "positive": sentiment_scores["positive"]
                            },
                            "roberta_sentiment_label": sentiment_label
                        }
                    }
                )
                success_count += 1
            except Exception as e:
                print(f"Error updating document {doc_id}: {e}")
                error_count += 1

        print(f"Batch results: {success_count} successful updates, {error_count} failures")

def process_sentiments(index_name):
    process_index(index_name)
    return "Sentiment analysis completed!"
