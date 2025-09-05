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

""" test/e2e_test.py """
import os
import sys
import httpx

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:9090/")

def check_health():
    """ check health API """
    url = BASE_URL + "health"
    print(F"Probing {url}")
    r = httpx.get(url)
    assert r.status_code == 200, f"Health check failed: {r.text}"
    data = r.json()
    assert "status" in data, "Missing expected keys"

def check_analyser_api(path):
    """ check APIs """
    url = BASE_URL + path
    print(F"Probing {url}")
    r = httpx.get(url)
    assert r.status_code == 200, f"api connectivity check failed: {r.text}"


def check_metadata():
    """ check metadata API """
    url = BASE_URL + "last-post-time"
    print(F"Probing {url}")
    r = httpx.get(url)
    assert r.status_code == 200, f"/last-post-time failed: {r.text}"
    data = r.json()
    assert "totalPosts" in data and "lastUpdateTime" in data, "Missing expected keys"

def run_all_tests():
    """ run all test to check all API end point """
    print("Running E2E Tests...")
    check_health()
    check_analyser_api("total-artists-mention-count")
    check_analyser_api("mention-count-by-artist-final")
    check_analyser_api("artist-mention-counts-trend")
    check_metadata()
    print("✅ All E2E tests passed.")

if __name__ == "__main__":
    try:
        run_all_tests()
    except AssertionError as e:
        print("❌ Test failed:", e)
        sys.exit(1)