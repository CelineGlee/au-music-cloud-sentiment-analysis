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

from flask import request, current_app
from typing import Dict, Any
import requests
import logging


def main() -> Dict[str, Any]:
    """Check Elasticsearch cluster health status.

    Handles:
    - ES cluster health API request
    - SSL certificate verification bypass
    - Basic authentication
    - Response logging

    Returns:
        JSON response from Elasticsearch cluster health API containing:
        - status: Cluster status (green/yellow/red)

    Raises:
        requests.exceptions.RequestException: For connection/API failures
    """
    # Log incoming request headers
    current_app.logger.info(
        f'Health check request from {request.remote_addr} '
        f'Headers: {dict(request.headers)}'
    )

    # Execute ES health check with type annotation
    es_response: requests.Response = requests.get(
        'https://elasticsearch-master.elastic.svc.cluster.local:9200/_cluster/health',
        verify=False,
        auth=('elastic', 'elastic'),
        timeout=5
    )

    # Log response status for monitoring
    current_app.logger.info(
        f'ES health check completed - '
        f'Status: {es_response.status_code} '
        f'Response time: {es_response.elapsed.total_seconds():.3f}s'
    )

    return es_response.json()
