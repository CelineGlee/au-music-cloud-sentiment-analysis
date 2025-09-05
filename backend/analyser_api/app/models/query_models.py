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

""" query-models.py """
from typing import Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel

class SortByEnum(str, Enum):
    """Enumeration for sorting options for topics."""
    count = "count"
    sentimentScore = "sentimentScore"


class IntervalEnum(str, Enum):
    """Enumeration for time interval options."""
    hour = "hour"
    day = "day"
    week = "week"
    month = "month"


class TopicsQuery(BaseModel):
    """Parameters for topics query."""
    subreddit: Optional[str] = None
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None
    limit: int = 10
    offset: int = 0
    sortBy: SortByEnum = SortByEnum.count


class TrendsQuery(BaseModel):
    """Parameters for trends query."""
    topic: str
    interval: IntervalEnum = IntervalEnum.month
    startTime: Optional[datetime] = None
    endTime: Optional[datetime] = None


class SentimentDistributionQuery(BaseModel):
    """Parameters for sentiment distribution query."""
    topic: Optional[str] = None

