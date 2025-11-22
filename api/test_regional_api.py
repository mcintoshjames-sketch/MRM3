#!/usr/bin/env python3
"""Quick test of regional version creation."""
import requests
import json

# Login
login_resp = requests.post("http://localhost:8001/auth/login", json={
    "email": "admin@example.com",
    "password": "admin123"
})
token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Create regional version
version_resp = requests.post(
    "http://localhost:8001/models/1/versions",
    headers=headers,
    json={
        "version_number": "9.10",  # Unique version number
        "change_type": "MINOR",
        "change_description": "Test regional version",
        "scope": "REGIONAL",
        "affected_region_ids": [1]
    }
)

print("Status:", version_resp.status_code)
print("Response:")
print(json.dumps(version_resp.json(), indent=2))
