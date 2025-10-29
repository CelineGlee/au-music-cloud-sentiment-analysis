from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError, NotFoundError
import plotly.express as px
import pandas as pd

def connect_elasticsearch():
    """Connect to Elasticsearch and verify connection."""
    es = Elasticsearch(
        ["https://localhost:9200"],
        verify_certs=False,
        ssl_show_warn=False,
        basic_auth=("elastic", "elastic"),
        request_timeout=30
    )
    if es.ping():
        print("Connected to Elasticsearch")
        return es
    else:
        print("Failed to connect to Elasticsearch")
        return None

def scroll_all_data(es, index, query, batch_size=1000, scroll="5m"):
    """Retrieve all data from the specified index using scrolling."""
    try:
        # Initialize scroll
        response = es.search(
            index=index,
            body=query,
            scroll=scroll,
            size=batch_size
        )
        scroll_id = response["_scroll_id"]
        total_hits = response["hits"]["total"]["value"]
        print(f"Total matching documents: {total_hits}")

        # Collect results
        all_results = []
        batch_count = 0

        # Process initial batch
        for hit in response["hits"]["hits"]:
            all_results.append(hit["_source"])
        batch_count += 1
        print(f"Processed batch {batch_count}: {len(all_results)} documents")

        # Continue scrolling
        while True:
            response = es.scroll(scroll_id=scroll_id, scroll=scroll)
            hits = response["hits"]["hits"]
            if not hits:
                break
            for hit in hits:
                all_results.append(hit["_source"])
            batch_count += 1
            print(f"Processed batch {batch_count}: {len(all_results)} documents")

        # Clear scroll context
        es.clear_scroll(scroll_id=scroll_id)
        print(f"Completed scrolling. Total documents retrieved: {len(all_results)}")
        return all_results

    except NotFoundError:
        print(f"Index '{index}' not found")
        return []
    except RequestError as e:
        print(f"Query error: {e.info}")
        return []
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return []

keywords = ["Trump", "Donald", "Donald Trump", "MAGA"]

reddit_query = {
    "query": {
        "bool": {
            "must": [
                {
                    "multi_match": {
                        "query": " ".join(keywords),
                        "fields": ["selftext", "body"],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                }
            ]
        }
    },
}

mastodon_query = {
    "query": {
        "bool": {
            "must": [
                {
                    "multi_match": {
                        "query": " ".join(keywords),
                        "fields": ["content"],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                }
            ]
        }
    },
}

es = connect_elasticsearch()
reddit_data = scroll_all_data(es, index="reddit-comments-prod", query=reddit_query, batch_size=1000)
mastodon_data = scroll_all_data(es, index="mastodon-prod-v3", query=mastodon_query, batch_size=1000)


def clean_reddit_comments(comment):
    """
    Clean and standardize a Reddit comment dictionary, skipping invalid entries.
    """
    # Check if input is a dictionary
    if not isinstance(comment, dict):
        print(f"Error: Input must be a dictionary, got {type(comment)}")
        return None

    # Check for required content field
    if "body" in comment:
        content = comment.get("body", "")
    elif "selftext" in comment:
        content = comment.get("selftext", "")
    else:
        print("Error: Comment missing 'body' or 'selftext' key")
        return None

    # Validate content is a string
    if not isinstance(content, str):
        print(f"Error: Comment content must be a string, got {type(content)}")
        return None

    try:
        # Check if roberta_sentiment exists
        if "roberta_sentiment" not in comment:
            print("Error: Comment missing 'roberta_sentiment' key")
            return None

        roberta_sentiment = comment["roberta_sentiment"]

        # Create cleaned comment dictionary
        cleaned_comment = {
            "platform": "reddit",
            "content": content,
            "positive": roberta_sentiment["positive"],
            "negative": roberta_sentiment["negative"],
            "neutral": roberta_sentiment["neutral"],
            "created_at": str(comment.get("created_utc", ""))[:10]
        }

        return cleaned_comment

    except (ValueError, TypeError, KeyError) as e:
        print(f"Error processing Reddit comment: {str(e)}")
        return None


def clean_mastodon_post(post):
    """
    Clean and standardize a Mastodon post dictionary, skipping invalid entries.
    """
    # Check if input is a dictionary
    if not isinstance(post, dict):
        print(f"Error: Input must be a dictionary, got {type(post)}")
        return None

    # Check for required content field
    content = post.get("content", "")
    if not content:
        print("Error: Post missing 'content' key or content is empty")
        return None

    # Validate content is a string
    if not isinstance(content, str):
        print(f"Error: Post content must be a string, got {type(content)}")
        return None

    try:
        # Check if roberta_sentiment exists
        if "roberta_sentiment" not in post:
            return None

        roberta_sentiment = post["roberta_sentiment"]

        # Create cleaned post dictionary
        cleaned_post = {
            "platform": "mastodon",
            "content": content,
            "positive": roberta_sentiment["positive"],
            "negative": roberta_sentiment["negative"],
            "neutral": roberta_sentiment["neutral"],
            "created_at": str(post.get("created_at", ""))[:10]
        }

        return cleaned_post

    except (ValueError, TypeError, KeyError) as e:
        print(f"Error processing Mastodon post: {str(e)}")
        return None


# Process the data
cleaned_reddit_comments = [cleaned_comment for comment in reddit_data if
                           (cleaned_comment := clean_reddit_comments(comment)) is not None]
cleaned_mastodon_posts = [cleaned_post for post in mastodon_data if
                          (cleaned_post := clean_mastodon_post(post)) is not None]

print(f"Number of cleaned Reddit comments: {len(cleaned_reddit_comments)}")
print(f"Number of cleaned Mastodon posts: {len(cleaned_mastodon_posts)}")

all_cleaned_data = cleaned_reddit_comments + cleaned_mastodon_posts
print(f"Total cleaned data: {len(all_cleaned_data)}")

# Get the average sentiment scores for each platform
df = pd.DataFrame(all_cleaned_data)
avg_scores = df.groupby('platform')[['positive', 'neutral', 'negative']].mean().reset_index()

# Melt the DataFrame to long format for Plotly Express
df_melted = avg_scores.melt(id_vars='platform',
                           value_vars=['positive', 'neutral', 'negative'],
                           var_name='Sentiment',
                           value_name='Average Score')

# Create grouped bar plot
fig = px.bar(df_melted,
             x='platform',
             y='Average Score',
             color='Sentiment',
             barmode='group',
             title='Average Sentiment Scores: Reddit vs Mastodon',
             color_discrete_map={
                 'positive': 'green',
                 'neutral': 'blue',
                 'negative': 'red'
             })

fig.update_layout(
    xaxis_title='Platform',
    yaxis_title='Average Score',
    yaxis_range=[0, 1],
    legend_title='Sentiment'
)

# Show the plot
fig.show()

# Prepare data for Reddit pie chart
mastodon_data = pd.DataFrame({
    'Sentiment': ['Positive', 'Neutral', 'Negative'],
    'Score': [avg_scores.loc[0, 'positive'], avg_scores.loc[0, 'neutral'], avg_scores.loc[0, 'negative']]
})

# Prepare data for Mastodon pie chart
reddit_data = pd.DataFrame({
    'Sentiment': ['Positive', 'Neutral', 'Negative'],
    'Score': [avg_scores.loc[1, 'positive'], avg_scores.loc[1, 'neutral'], avg_scores.loc[1, 'negative']]
})

# Create Reddit pie chart
reddit_fig = px.pie(reddit_data,
                    names='Sentiment',
                    values='Score',
                    title='Reddit Sentiment Distribution Towards Trump',
                    color='Sentiment',
                    color_discrete_map={
                        'Positive': 'green',
                        'Neutral': 'blue',
                        'Negative': 'red'
                    })

# Update layout for Reddit pie chart
reddit_fig.update_layout(
    template='plotly_white',
    legend_title='Sentiment'
)

# Create Mastodon pie chart
mastodon_fig = px.pie(mastodon_data,
                      names='Sentiment',
                      values='Score',
                      title='Mastodon Sentiment Distribution Towards Trump',
                      color='Sentiment',
                      color_discrete_map={
                        'Positive': 'green',
                        'Neutral': 'blue',
                        'Negative': 'red'
                      })

# Update layout for Mastodon pie chart
mastodon_fig.update_layout(
    template='plotly_white',
    legend_title='Sentiment'
)

# Show the plots
reddit_fig.show()
mastodon_fig.show()

# Calculate sentiment score for each post
df['sentiment_score'] = df['positive'] - df['negative']
df['created_at'] = pd.to_datetime(df['created_at'])

# Group by platform and date, averaging sentiment scores
df_agg = df.groupby(['platform', df['created_at'].dt.date])['sentiment_score'].mean().reset_index()
df_platform = df_agg[df_agg['platform'] == 'reddit']

# Create line plot
fig = px.line(
    df_platform,
    x='created_at',
    y='sentiment_score',
    title=f'Reddit Daily Sentiment Towards Trump Over Time',
    markers=True
)
fig.update_layout(
    xaxis_title='Date',
    yaxis_title='Sentiment Score',
    showlegend=False
)

fig.show()

# Group by platform and week, then calculate mean sentiment
df_agg = df.groupby(['platform', df['created_at'].dt.to_period('W')])['sentiment_score'].mean().reset_index()
df_agg['created_at'] = df_agg['created_at'].dt.start_time

df_platform = df_agg[df_agg['platform'] == 'mastodon']

# Create line plot
fig = px.line(
    df_platform,
    x='created_at',
    y='sentiment_score',
    title='Mastodon Weekly Sentiment Towards Trump Over Time',
    markers=True
)
fig.update_layout(
    xaxis_title='Week',
    yaxis_title='Sentiment Score',
    showlegend=False
)
fig.show()