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

""" analyser.py """
from typing import List, Optional 
from datetime import datetime
import logging
import re

from fastapi import APIRouter, Query, HTTPException, Request

from app.core.elasticsearcher import get_elasticsearch_client, build_combined_query

from app.models.response_models import (
    TopicSummary, TrendPoint, SentimentDistribution, Metadata, ArtistMentionsResponse, 
    ArtistMentionsTrendResponse, SentimentCountResponse, ArtistMentionsCountResponse, ArtistMentionsFinalResponse
)
from app.models.query_models import SortByEnum, IntervalEnum

from app.config import settings

from collections import OrderedDict

import json

router = APIRouter()
logger = logging.getLogger(__name__)

example_artist_mention_counts_response = {
    "mentions": {
        "Taylor Swift": 20,
        "Beyoncé": 30,
        "Adele": 15
    }
}

example_artist_mention_counts_final_response = {
    "mentions": {
        "international": [("Taylor Swift", 2), ("Adele", 3)],
        "australia": [("Sia", 13)]
    }
}


@router.get("/total-artists-mention-count", response_model=ArtistMentionsCountResponse, tags=["analyser"]) 
async def get_total_artists_mention_count(request: Request):
    """
    Get artists mention post counts in artists index.
    """
    try:  
        artist_data = request.app.state.my_data
        logger.info(f"artist_data: {artist_data}")

        print("Querying international artists...")
        results_artists = process_artist_group(artist_data.get("artists", {}))   

        print("Querying Australian artists...")
        results_artists_au = process_artist_group(artist_data.get("artists_au", {}))

        mentions = {"international": results_artists, "australia": results_artists_au}
        
        logger.info(f"mentions: {mentions}")

        internationalCount = 0
        for artist in results_artists:
            if artist:
                internationalCount = internationalCount + artist[1]

        australiaCount = 0
        for au_artist in results_artists_au:
            if au_artist:
                australiaCount = australiaCount + au_artist[1]

        totalSum = internationalCount + australiaCount

        return ArtistMentionsCountResponse(
            mentionsCount = totalSum
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/mention-count-by-artist-final", response_model=ArtistMentionsFinalResponse, 
            responses={
                200: {
                        "description": "Successful Response",
                        "content": {
                            "application/json": {
                            "example": example_artist_mention_counts_final_response
                        }
                    }
                    }
            }, tags=["analyser"])
async def get_mention_count_by_artist_final(request: Request):
    """
    Get artists mention post counts in artists index.
    """
    try:  
        artist_data = request.app.state.my_data
        logger.info(f"artist_data: {artist_data}")

        print("Querying international artists...")
        results_artists = process_artist_group(artist_data.get("artists", {}))   

        print("Querying Australian artists...")
        results_artists_au = process_artist_group(artist_data.get("artists_au", {}))

        mentions = {"international": results_artists, "australia": results_artists_au}
        
        logger.info(f"mentions: {mentions}")

        return ArtistMentionsFinalResponse(
            international=results_artists,
            australia=results_artists_au
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/mention-count-by-artist", response_model=ArtistMentionsResponse, deprecated=True,
            responses={
                200: {
                        "description": "Successful Response",
                        "content": {
                            "application/json": {
                            "example": example_artist_mention_counts_response
                        }
                    }
                    }
            }, tags=["analyser"])
async def get_mention_count_by_artist(request: Request):
    """
    Get artists mention post counts in artists index.
    """

    data = request.app.state.my_data
   
    artists = []
    for artist_dict in [data["artists"], data["artists_au"]]:
        for names in artist_dict.values():
            artists.extend(names)

    logger.info(f"artists: {artists}")

    artists = list(OrderedDict.fromkeys(artists))

    try:
        es = get_elasticsearch_client()
        # Construct filters for the DSL
        filters = {
            artist: {
                "match_phrase": {
                "content": artist
                }
            }
        for artist in artists
        }

        query = {
            "size": 0,
            "aggs": {
                "artist_mentions": {
                    "filters": {
                        "filters": filters
                    }
                }
            }
        }

        logger.info(f"DSL Query: {query}")

        response = es.search(index=settings.ELASTICSEARCH_ARTISTS_INDEX, body=query)
        buckets = response["aggregations"]["artist_mentions"]["buckets"]

        alias_to_canonical = {}
        for artist_group in [data["artists"], data["artists_au"]]:
            for canonical, aliases in artist_group.items():
                for alias in aliases:
                    alias_to_canonical[alias] = canonical

        # Aggregate counts
        results = {}
        for alias, info in buckets.items():
            canonical = alias_to_canonical.get(alias)
            if canonical:
                results[canonical] = results.get(canonical, 0) + info["doc_count"]

        mentions = results
        #mentions = {artist: buckets.get(artist, {}).get("doc_count", 0) for artist in artists}
        logger.info(f"mentions: {mentions}")

        return ArtistMentionsResponse(mentions=mentions)


    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


example_artist_mention_counts_trend_response = {
    "mentions": {
        "Taylor Swift": {"202210":5, "202211":9},
        "Beyoncé": {"202210":4, "202211":6},
        "Adele": {"202210":1, "202211":2}
    }
}

@router.get("/artist-mention-counts-trend", response_model=ArtistMentionsTrendResponse, 
            responses={
                200: {
                        "description": "Successful Response",
                        "content": {
                            "application/json": {
                            "example": example_artist_mention_counts_trend_response
                        }
                    }
                    }
            }, tags=["analyser"])
async def get_artist_mention_counts_trend(request: Request):
    """
    Get artists mention post counts in artists index.
    """
    data = request.app.state.my_exact_data
   
    artists = []
    for artist_dict in [data["artists"], data["artists_au"]]:
        for names in artist_dict.values():
            artists.extend(names)

    logger.info(f"artists: {artists}")

    artists = list(OrderedDict.fromkeys(artists))


    try:
        es = get_elasticsearch_client()
        # Construct filters for the DSL
        
        filters = {
            artist: {
                "match_phrase": {
                "content": artist
                }
            }
        for artist in artists
        }

        query = {
            "size": 0,
            "aggs": {
                "artist_filters": {
                    "filters": {
                        "filters": filters
                    },
                    "aggs": {
                        "monthly_trend": {
                            "date_histogram": {
                                "field": "created_at",
                                "calendar_interval": "month",
                                "format": "yyyyMM"
                            }
                        }
                    }
                }
            }
        }

        mentions = {}
        
        logger.info(f"DSL Query: {query}")

        response = es.search(index=settings.ELASTICSEARCH_ARTISTS_INDEX, body=query)
        
        buckets = response["aggregations"]["artist_filters"]["buckets"]

        for artist, bucket in buckets.items():
            monthly_buckets = bucket.get("monthly_trend", {}).get("buckets", [])
            monthly_counts = {
                entry["key_as_string"]: entry["doc_count"]
                for entry in monthly_buckets
            }
            mentions[artist] = monthly_counts

        result = ArtistMentionsTrendResponse(mentions=mentions)
        logger.info(f"response: {result}")

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/sentiment_trends_per_artist", response_model=List[TrendPoint], tags=["analyser"])
async def get_trends(
    artist: str = Query(None, example="Katy Perry"),
    interval: IntervalEnum = Query(IntervalEnum.month, example=IntervalEnum.month),
    startTime: Optional[datetime] = Query(
        None,
        example="2020-01-01T00:00:00",
        description="Start time in ISO format"
    ),
    endTime: Optional[datetime] = Query(
        None,
        example="2025-12-31T23:59:59",
        description="End time in ISO format"
    )
):
    """
    Get sentiment trend over time.
    Returns time-series trend data for a specific artist.
    """
    try:
        es = get_elasticsearch_client()

        query = {
                "bool": {
                    "must": [
                        {
                        "range": {
                            "created_at": {
                            "gte": startTime,
                            "lte": endTime
                            }
                        }
                        }
                    ],
                    "should": [
                        {
                            "match_phrase": {
                                "content": artist
                            }
                        },
                        {
                            "term": {
                                "tags.keyword": artist
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            }
        
        aggs = {
                "monthly": {
                    "date_histogram": {
                        "field": "created_at",
                        "calendar_interval": interval,
                        "format": "yyyyMM"
                    },
                    "aggs": {
                        "positive": {
                            "filter": {
                                "term": {
                                    "roberta_sentiment_label.keyword": "positive"
                                }
                            }
                        },
                        "negative": {
                            "filter": {
                                "term": {
                                    "roberta_sentiment_label.keyword": "negative"
                                }
                            }
                        },
                        "neutral": {
                            "filter": {
                                "term": {
                                    "roberta_sentiment_label.keyword": "neutral"
                                }
                            }
                        }
                    }
                }
            }
        
        logger.info(f"DSL Query: {query}")
        logger.info(f"DSL Aggs: {aggs}")

        # Run aggregation query
        response = es.search(
            index=settings.ELASTICSEARCH_ARTISTS_INDEX,
            size=0,
            query=query,
            aggs=aggs)

        

        # Transform to desired format
        results = []
        for bucket in response["aggregations"]["monthly"]["buckets"]:
            record = TrendPoint(
                period=bucket["key_as_string"],
                positiveSentimentCount=bucket["positive"]["doc_count"],
                negativeSentimentCount=bucket["negative"]["doc_count"],
                neutralSentimentCount=bucket["neutral"]["doc_count"],
                totalPostCount=bucket["doc_count"]
            )
            results.append(record)
        return results
        
    except Exception as e:
        logger.error("Error retrieving trends: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e


@router.get("/sentiment-distribution-by-artist", response_model=SentimentCountResponse, tags=["analyser"])
async def get_sentiment_distribution(artist: Optional[str] = Query(None, example="Katy Perry")):
    """
    Get sentiment distribution.
    Returns sentiment distribution for a given artist.
    """
    try:
        es = get_elasticsearch_client()
        userInput = sanitize_input(artist)
    
        #artist_pattern = f".*{userInput.lower().replace(' ', '.*')}.*"

        filters = {
            userInput: {
                "match_phrase": {
                "content": userInput
                }
            }
        }

        query = {
        "size": 0,
        "aggs": {
            "artist_filters": {
                "filters": {
                    "filters": filters
                },
                "aggs": {
                    "sentiment_counts": {
                        "terms": {
                            "field": "roberta_sentiment_label.keyword"
                        }
                    }
                }
            }
        }
    }

        logger.info(f"DSL Query: {query}")   
        response = es.search(index=settings.ELASTICSEARCH_ARTISTS_INDEX, body=query)

        buckets = response["aggregations"]["artist_filters"]["buckets"]
        sentiment_buckets = buckets[userInput]["sentiment_counts"]["buckets"]

        sentiments = {bucket["key"]: bucket["doc_count"] for bucket in sentiment_buckets}

        return SentimentCountResponse(sentiments=sentiments)
        
    except Exception as e:
        logger.error("Error retrieving sentiment distribution: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e


@router.get("/last-post-time", response_model=Metadata, tags=["analyser"])
async def get_metadata():
    """
    Get dataset metadata.
    Returns metadata about the dataset such as last post creation time.
    """
    try:
        es = get_elasticsearch_client()
        
        # Get total post count
        count_response = es.count(index=settings.ELASTICSEARCH_ARTISTS_INDEX)
        total_posts = count_response["count"]
        
        # Get unique topics count
        aggs = {
            "latest_post": {
                "max": {
                    "field": "created_at"
                }
            }
        }

        logger.info(f"DSL Aggs: {aggs}")
        
        response = es.search(
            index=settings.ELASTICSEARCH_ARTISTS_INDEX,
            size=0,
            aggs=aggs
        )
        
        # Get the latest post timestamp as last update time
        last_update_timestamp = response["aggregations"]["latest_post"]["value_as_string"]
        last_update_time = datetime.fromisoformat(last_update_timestamp.replace('Z', '+00:00'))

        metadata = Metadata(
            totalPosts=total_posts,
            lastUpdateTime=last_update_time
        )
            
        return metadata
        
    except Exception as e:
        logger.error("Error retrieving metadata: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e


def sanitize_input(user_input: str) -> str:
    """ sanitize input """ 
        # Basic example: strip leading/trailing whitespace
        # and remove suspicious characters
    sanitized = user_input.strip()

        # Optional: remove or escape potentially harmful characters
        # like *, ?, :, ", etc. depending on your search use-case
    sanitized = re.sub(r'[^a-zA-Z0-9\s]', '', sanitized)

    return sanitized

# Get post count for artist
def get_post_count(aliases):


    should_clauses = [{"match_phrase": {"content": alias}} for alias in aliases]
    query = {
        "query": {
            "bool": {
                "should": should_clauses,
                "minimum_should_match": 1
            }
        },
        "track_total_hits": True,
        "size": 0
    }

    try:

        es = get_elasticsearch_client()

        response = es.search(
            index=settings.ELASTICSEARCH_ARTISTS_INDEX,
            body=query
        )

        return response["hits"]["total"]["value"]

    except Exception as e:
        print(f"Request failed for aliases {aliases}: {str(e)}")
        return 0


def process_artist_group(artist_dict):
    results = []  # List used to keep sequence
    for artist in artist_dict:
        padded_name = "`" + artist.rjust(20)
        aliases = artist_dict[artist]
        count = get_post_count(aliases)
        results.append((padded_name, count))
    return results