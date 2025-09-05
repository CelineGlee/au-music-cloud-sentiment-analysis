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

""" test connection """
import ssl
from elasticsearch import Elasticsearch


if __name__ == "__main__":
    print("hello")
    
    # Create an SSL context that skips certificate verification
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    es_config = {
        #"hosts": settings.ELASTICSEARCH_HOSTS,
        "hosts": ["https://localhost:9200"],
        "ssl_context": ssl_context,
        "verify_certs": False,
        "basic_auth": ("elastic", "elastic")
    }
    
    try:
        client = Elasticsearch(**es_config)
        # Verify connection
        if not client.ping():
            print("Could not connect to Elasticsearch")
            raise ConnectionError("Could not connect to Elasticsearch")
        else:
            print("connected succeclient")
    except Exception as e:
        print(f"Error creating Elasticsearch client: {e}")
        raise
