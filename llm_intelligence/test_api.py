#!/usr/bin/env python3
"""
Test Client for LLM Intelligence API
===================================

Tests all API endpoints to verify functionality.
"""

import urllib.request
import urllib.error
import json
import sys

def test_endpoint(url, description):
    """Test a single API endpoint"""
    try:
        print(f"🔄 Testing {description}...")
        print(f"   URL: {url}")
        
        with urllib.request.urlopen(url, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                print(f"   ✅ Status: {response.status}")
                
                # Show some response details
                if isinstance(data, list):
                    print(f"   📊 Returned {len(data)} items")
                    if data:
                        first_item = data[0]
                        if isinstance(first_item, dict):
                            print(f"   🔑 Keys: {list(first_item.keys())[:5]}...")
                elif isinstance(data, dict):
                    print(f"   🔑 Keys: {list(data.keys())[:5]}...")
                    
                return True
            else:
                print(f"   ❌ Status: {response.status}")
                return False
                
    except urllib.error.URLError as e:
        print(f"   ❌ Connection error: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"   ❌ JSON decode error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

def main():
    """Test all API endpoints"""
    base_url = "http://localhost:8055"
    
    print("🧪 LLM Intelligence API Test Suite")
    print("=" * 50)
    
    # Test endpoints
    endpoints = [
        ("/", "Root endpoint"),
        ("/health", "Health check"),
        ("/rankings", "Model rankings"),
        ("/rankings?limit=3", "Limited rankings"),
        ("/rankings?use_case=coding", "Coding rankings"),
        ("/rankings?has_free_tier=true", "Free tier rankings"),
        ("/rankings/top-free", "Top free models"),
        ("/rankings/best-value", "Best value models"),
        ("/providers/claude-3.5-sonnet", "Provider options"),
        ("/recommendations", "Recommendations"),
        ("/benchmarks", "Benchmark scores"),
        ("/benchmarks?benchmark_category=coding", "Coding benchmarks")
    ]
    
    passed = 0
    total = len(endpoints)
    
    for endpoint, description in endpoints:
        url = base_url + endpoint
        if test_endpoint(url, description):
            passed += 1
        print()
    
    # Summary
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} endpoints passed")
    
    if passed == total:
        print("🎉 All tests passed! API is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check server logs.")
        return 1

if __name__ == "__main__":
    sys.exit(main())