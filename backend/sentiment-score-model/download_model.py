"""
download_model.py

This script downloads and saves a pre-trained RoBERTa sentiment analysis model from Hugging Face.
The model name is "cardiffnlp/twitter-roberta-base-sentiment-latest"
designed for sentiment classification of text.

The script creates directories for the tokenizer and model, downloads both components,
and saves them to the specified paths for later use in sentiment analysis tasks.

Returns:
     0 if model download successful, 1 if not download successful
"""

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os
import sys

def download_model():
    try:
        # Create directories for tokenizer and model if they don't exist
        os.makedirs("/models/roberta-sentiment/tokenizer", exist_ok=True)
        os.makedirs("/models/roberta-sentiment/model", exist_ok=True)

        # Define which model to download
        MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"
        print(f"Downloading model {MODEL_NAME}...")

        # Download and save the tokenizer
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        tokenizer.save_pretrained("/models/roberta-sentiment/tokenizer")
        print("Tokenizer saved successfully")

        # Download and save the tokenizer
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
        model.save_pretrained("/models/roberta-sentiment/model")
        print("Model saved successfully")

        print("Model download and preparation complete!")
        return True
    except Exception as e:
        print(f"Error downloading model: {e}")
        return False


if __name__ == "__main__":
    success = download_model()
    sys.exit(0 if success else 1)