# docker build -t yucai5/sentiment-analyzer:lightweight -f Dockerfile .
# docker push yucai5/sentiment-analyzer:lightweight

FROM python:3.9-slim

WORKDIR /app

# Create a directory for model caching
RUN mkdir -p /models/roberta-sentiment/model /models/roberta-sentiment/tokenizer

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache/pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy your sentiment analysis script
COPY download_model.py mastodon_sentiment_analyzer.py reddit_sentiment_analyzer.py reddit_comment_analyzer.py sentiment_analyzer_index.py ./

# Run the script when the container starts
CMD ["/bin/bash"]
