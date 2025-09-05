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

""" config.py """
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Analytics-API"
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Elasticsearch settings
    ELASTICSEARCH_HOSTS: List[str] = ["https://elasticsearch-master.elastic.svc.cluster.local:9200"]
    # ELASTICSEARCH_HOSTS: List[str] = ["https://localhost:9200"]
    ELASTICSEARCH_USERNAME: str = "elastic"
    ELASTICSEARCH_PASSWORD: str = "elastic"
    ELASTICSEARCH_INDEX: str = "reddit-prod"
    ELASTICSEARCH_KATY_PERRY_INDEX: str = "katy-perry-index"
    ELASTICSEARCH_ALL_SINGERS_INDEX: str = "all-singers"
    ELASTICSEARCH_ARTISTS_INDEX: str = "artists"
    
    # Logging
    LOG_LEVEL: str = "INFO"

settings = Settings()
