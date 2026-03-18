#!/usr/bin/env python3
"""
Simple test script to verify the callback endpoint testing mechanism.
This script tests both the test mode and normal mode of the callback endpoint.
"""

import requests
import json

# Replace with your actual server URL
BASE_URL = "savestack.ojogulabs.xyz/api/v1"

def test_callback_endpoint():
    """Test the callback endpoint in both test and normal modes."""
    
    print("Testing Callback Endpoint Implementation")
    print("=" * 50)
    
    # Test 1: Test mode with ?test=true
    print("\n1. Testing callback endpoint in test mode:")
    print("   Request: GET /auth/callback?test=true")
    
    try:
        response = requests.get(f"{BASE_URL}/auth/callback?test=true")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        if response.status_code == 200 and response.json() == {"status": "ready"}:
            print("   ✅ Test mode working correctly!")
        else:
            print("   ❌ Test mode not working as expected")
            
    except requests.exceptions.ConnectionError:
        print("   ⚠️  Server not running. Please start the server to test.")
        print("   You can start it with: uvicorn src.main:app --reload")
        return
    except Exception as e:
        print(f"   ❌ Error testing test mode: {e}")
    
    # Test 2: Normal mode without required parameters
    print("\n2. Testing callback endpoint in normal mode (missing params):")
    print("   Request: GET /auth/callback")
    
    try:
        response = requests.get(f"{BASE_URL}/auth/callback")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response URL: {response.url}")
        
        # Should redirect to login with missing_params error
        if "missing_params" in response.url:
            print("   ✅ Normal mode working correctly (redirects with error)")
        else:
            print("   ⚠️  Normal mode behavior may have changed")
            
    except Exception as e:
        print(f"   ❌ Error testing normal mode: {e}")
    
    print("\n" + "=" * 50)
    print("Test completed!")
    print("\nUsage:")
    print("  Test mode: GET /auth/callback?test=true")
    print("  Normal mode: GET /auth/callback?code=xxx&state=yyy")

