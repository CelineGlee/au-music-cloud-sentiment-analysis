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

""" response-models.py """
from typing import Optional
from typing import Dict, List, Tuple
from datetime import datetime
from pydantic import BaseModel, Field


class TopicSummary(BaseModel):
    """Model for topic summary response."""
    topic: str
    count: int
    sentimentScore: float
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None


class TrendPoint(BaseModel):
    """Model for a single point in trend data."""
    period: str = Field(..., description="Time interval label, e.g., '2024/01'")
    positiveSentimentCount: int
    negativeSentimentCount: int
    neutralSentimentCount: int
    totalPostCount: int

class SentimentDistribution(BaseModel):
    """Model for sentiment distribution response."""
    positiveCount: int
    neutralCount: int
    negativeCount: int
    totalCount: int

class ArtistMentionsCountResponse(BaseModel):
    """Model for artists mention """
    mentionsCount: int

class ArtistMentionsResponse(BaseModel):
    """Model for artists mention """
    mentions: Dict[str, int]

class ArtistMentionsFinalResponse(BaseModel):
    """Model for artists mention """
    international: List[Tuple[str, int]]
    australia: List[Tuple[str, int]]

class ArtistMentionsTrendResponse(BaseModel):
    """Model for artists mention trend """
    mentions: Dict[str, Dict[str, int]]

class Metadata(BaseModel):
    """Model for dataset metadata response."""
    totalPosts: int
    lastUpdateTime: datetime

class SentimentCountResponse(BaseModel):
    sentiments: Dict[str, int]