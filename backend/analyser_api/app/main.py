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

""" main.py """
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import analyser
from app.core.elasticsearcher import get_elasticsearch_client
import json

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Analyser API",
    description="API for analyzing social media data. Mainly used by Jupyter Notebook frontend.",
    version="1.1.5",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analyser.router)

@app.on_event("startup")
async def startup_db_client():
    """Initialize the Elasticsearch client connection on startup."""
    # This will test the connection to Elasticsearch when the app starts
    try:
        es_client = get_elasticsearch_client()
        info = es_client.info()
        logger.info(f"Connected to Elasticsearch cluster: {info.get('cluster_name', 'unknown')}")

        with open("app/data/artists.json", "r", encoding="utf-8") as f:
            app.state.my_data = json.load(f)
        
        with open("app/data/artists_exact.json", "r", encoding="utf-8") as f:
            app.state.my_exact_data = json.load(f)
        
    except Exception as e:
        logger.error(f"Failed to connect to Elasticsearch: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    """Close the Elasticsearch client connection on shutdown."""
    logger.info("Application shutting down")


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {"status": "healthy", "service": "analyser-api v1.1.5"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
