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

""" test_analyser_api_main.py """
import sys
import os

# Append project root to sys.path (adjust '..' as needed)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'analyser_api')))

from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.analyser_api.app.main import app

client = TestClient(app)

@patch("backend.analyser_api.app.main.get_elasticsearch_client")
@patch("backend.analyser_api.app.main.logger")
def test_startup_db_client(mock_logger, mock_es_client):
    mock_es_client.return_value.info.return_value = {"cluster_name": "test-cluster"}

    with client:
        mock_logger.info.assert_called_with("Connected to Elasticsearch cluster: test-cluster")
