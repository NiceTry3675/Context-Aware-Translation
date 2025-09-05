#!/usr/bin/env python3
"""Test script to verify validation endpoints work correctly."""

import requests
import json

# Configuration
API_BASE = "http://localhost:8000"
JOB_ID = 1  # Adjust as needed

# You'll need to get a valid token from the frontend
# For testing, you can get one from the browser's network tab
TOKEN = "YOUR_TOKEN_HERE"

def test_endpoints():
    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }
    
    print("Testing validation endpoints...")
    
    # Test segments endpoint
    print(f"\n1. Testing /api/v1/jobs/{JOB_ID}/segments")
    try:
        response = requests.get(
            f"{API_BASE}/api/v1/jobs/{JOB_ID}/segments",
            headers=headers,
            params={"offset": 0, "limit": 200}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Segments found: {data.get('total_segments', 0)}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test content endpoint
    print(f"\n2. Testing /api/v1/jobs/{JOB_ID}/content")
    try:
        response = requests.get(
            f"{API_BASE}/api/v1/jobs/{JOB_ID}/content",
            headers=headers
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            content_len = len(data.get('content', ''))
            print(f"   Content length: {content_len} characters")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test validation report endpoint
    print(f"\n3. Testing /api/v1/jobs/{JOB_ID}/validation-report")
    try:
        response = requests.get(
            f"{API_BASE}/api/v1/jobs/{JOB_ID}/validation-report",
            headers=headers
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            results = data.get('detailed_results', [])
            print(f"   Validation results found: {len(results)}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("Validation Endpoints Test")
    print("=" * 60)
    print(f"API Base: {API_BASE}")
    print(f"Job ID: {JOB_ID}")
    print("\nNOTE: You need to update the TOKEN variable with a valid JWT token")
    print("You can get one from the browser's network tab when logged in")
    print("=" * 60)
    
    if TOKEN == "YOUR_TOKEN_HERE":
        print("\n⚠️  Please update the TOKEN variable first!")
    else:
        test_endpoints()