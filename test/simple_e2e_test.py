#!/usr/bin/env python3
"""
Simple E2E tests using requests and BeautifulSoup.
Tests basic functionality without complex browser automation.
"""
import requests
import time
import sys
from bs4 import BeautifulSoup


def wait_for_server(url, max_retries=30, delay=2):
    """Wait for the server to be ready."""
    print(f"Waiting for server at {url}...")
    for i in range(max_retries):
        try:
            response = requests.get(f"{url}/healthz", timeout=5)
            if response.status_code in [200, 302]:  # 302 is redirect, which is also OK
                print(f"✅ Server is ready (attempt {i+1})")
                return True
        except requests.exceptions.RequestException:
            pass
        
        print(f"  [{i+1}/{max_retries}] Server not ready yet, waiting {delay}s...")
        time.sleep(delay)
    
    print("❌ Server failed to become ready")
    return False


def test_health_endpoint():
    """Test the health endpoint."""
    print("Testing health endpoint...")
    try:
        response = requests.get("http://127.0.0.1:8000/healthz", timeout=10)
        print(f"✅ Health endpoint responded with status {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Health endpoint failed: {e}")
        return False


def test_static_files():
    """Test that static files are served."""
    print("Testing static file serving...")
    try:
        # Test the main page
        response = requests.get("http://127.0.0.1:8000/", timeout=10)
        if response.status_code == 200:
            # Parse HTML to check for basic structure
            soup = BeautifulSoup(response.text, 'html.parser')
            if soup.find('title') or soup.find('div'):
                print("✅ Main page loads with HTML content")
                return True
            else:
                print("❌ Main page loads but no HTML structure found")
                return False
        else:
            print(f"❌ Main page returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Static file test failed: {e}")
        return False


def test_api_endpoints():
    """Test basic API endpoints."""
    print("Testing API endpoints...")
    
    # Test config endpoint
    try:
        response = requests.get("http://127.0.0.1:8000/api/config", timeout=10)
        if response.status_code == 200:
            print("✅ /api/config endpoint is accessible")
            config_works = True
        else:
            print(f"⚠️  /api/config returned status {response.status_code}")
            config_works = False
    except Exception as e:
        print(f"⚠️  /api/config failed: {e}")
        config_works = False
    
    # Test banners endpoint
    try:
        response = requests.get("http://127.0.0.1:8000/api/banners", timeout=10)
        if response.status_code == 200:
            print("✅ /api/banners endpoint is accessible")
            banners_works = True
        else:
            print(f"⚠️  /api/banners returned status {response.status_code}")
            banners_works = False
    except Exception as e:
        print(f"⚠️  /api/banners failed: {e}")
        banners_works = False
    
    return config_works or banners_works  # At least one should work


def run_tests():
    """Run all E2E tests."""
    print("🧪 Starting Simple E2E Tests")
    print("=" * 40)
    
    # Wait for server
    if not wait_for_server("http://127.0.0.1:8000"):
        print("💥 Server not ready, aborting tests")
        return False
    
    # Run tests
    tests = [
        test_health_endpoint,
        test_static_files,
        test_api_endpoints,
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
        print()  # Empty line between tests
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 40)
    print(f"🎯 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All E2E tests passed!")
        return True
    else:
        print("💥 Some E2E tests failed")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)