#!/usr/bin/env python3
"""Test that completion_date is returned in validation request detail API."""
import requests
from datetime import datetime, timedelta
from jose import jwt
import os

# Generate token using same secret as API
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-keep-this-very-secret-in-production')
token_data = {
    'sub': 'admin@example.com',
    'exp': datetime.utcnow() + timedelta(days=1)
}
token = jwt.encode(token_data, SECRET_KEY, algorithm='HS256')

# Test detail endpoint for request #48 (Approved status)
url = 'http://localhost:8001/validation-workflow/requests/48'
headers = {'Authorization': f'Bearer {token}'}

print("=" * 80)
print("TESTING: completion_date in ValidationRequestDetailResponse")
print("=" * 80)

response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    print(f"\n✅ Status: {response.status_code} OK")
    print(f"\nValidation Request #{data['request_id']}:")
    print(f"  Status: {data['current_status']['label']}")
    print(f"  Target Completion: {data['target_completion_date']}")

    if 'completion_date' in data:
        print(f"  ✅ Completion Date Field: PRESENT")
        print(f"     Value: {data['completion_date'] or 'null (not yet completed)'}")
    else:
        print(f"  ❌ Completion Date Field: MISSING")
else:
    print(f"\n❌ Error: {response.status_code}")
    print(response.text)
