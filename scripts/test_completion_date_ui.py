#!/usr/bin/env python3
"""Test that completion_date is returned in validation request detail API."""
import requests
from datetime import datetime, timedelta
from jose import jwt

# Generate token
SECRET_KEY = 'your-secret-key-keep-this-very-secret-in-production'
token_data = {
    'sub': 'admin@example.com',
    'exp': datetime.utcnow() + timedelta(days=1)
}
token = jwt.encode(token_data, SECRET_KEY, algorithm='HS256')

# Test detail endpoint for request #48 (Approved status)
url = 'http://localhost:8001/validation-workflow/requests/48'
headers = {'Authorization': f'Bearer {token}'}

print("=" * 80)
print("TESTING VALIDATION REQUEST DETAIL API - COMPLETION_DATE FIELD")
print("=" * 80)
print(f"\nEndpoint: {url}")
print(f"Token: {token[:50]}...")

response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    print(f"\n✅ Status Code: {response.status_code}")
    print(f"\nKey fields:")
    print(f"  Request ID: {data.get('request_id')}")
    print(f"  Status: {data.get('current_status', {}).get('label')}")
    print(f"  Target Completion: {data.get('target_completion_date')}")
    print(f"  ✨ Completion Date: {data.get('completion_date')}")

    if 'completion_date' in data:
        print(f"\n✅ SUCCESS: completion_date field is present in response")
        if data['completion_date']:
            print(f"   Value: {data['completion_date']}")
        else:
            print(f"   Value: null (validation not yet completed)")
    else:
        print(f"\n❌ ERROR: completion_date field is missing from response!")
        print(f"\nAvailable fields: {list(data.keys())}")
else:
    print(f"\n❌ Error: Status Code {response.status_code}")
    print(f"Response: {response.text}")
