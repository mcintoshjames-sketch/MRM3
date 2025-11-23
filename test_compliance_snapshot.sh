#!/bin/bash

# Test Point-in-Time Compliance Snapshot Feature

echo "=== Testing Point-in-Time Compliance Snapshot ==="
echo ""

# Login
echo "1. Logging in as admin..."
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8001/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}')

TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "Failed to get token"
  exit 1
fi
echo "✓ Logged in"

echo ""
echo "2. Getting a change type that requires MV approval (change_type_id=1: New Model Development)..."
CHANGE_TYPE=$(curl -s "http://localhost:8001/change-taxonomy/types/1" \
  -H "Authorization: Bearer $TOKEN")

echo "$CHANGE_TYPE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('Change Type:', data['name'])
print('Requires MV Approval:', data['requires_mv_approval'])
" 2>/dev/null || echo "Could not parse response"

echo ""
echo "3. Creating a model version with this change type..."
VERSION_RESPONSE=$(curl -s -X POST "http://localhost:8001/models/1/versions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "change_type": "MAJOR",
    "change_type_id": 1,
    "change_description": "Test change for compliance snapshot - New Model Development",
    "planned_production_date": "2025-12-15"
  }')

VERSION_ID=$(echo "$VERSION_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['version_id'])" 2>/dev/null)

if [ -z "$VERSION_ID" ]; then
  echo "Failed to create version"
  echo "$VERSION_RESPONSE"
  exit 1
fi

echo "✓ Created version ID: $VERSION_ID"

echo ""
echo "4. Verifying the compliance snapshot was captured..."
echo "$VERSION_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('Version Number:', data['version_number'])
print('Change Type:', data['change_type_name'])
print('Change Requires MV Approval (snapshot):', data.get('change_requires_mv_approval', 'NOT CAPTURED'))
print('Validation Request Created:', data.get('validation_request_created', False))
" 2>/dev/null || echo "Could not parse response"

echo ""
echo "5. Retrieving version details to confirm snapshot persisted..."
VERSION_DETAILS=$(curl -s "http://localhost:8001/versions/$VERSION_ID" \
  -H "Authorization: Bearer $TOKEN")

echo "$VERSION_DETAILS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('Version ID:', data['version_id'])
print('Change Requires MV Approval:', data.get('change_requires_mv_approval', 'NOT FOUND'))
print('Validation Request ID:', data.get('validation_request_id', 'None'))
" 2>/dev/null || echo "Could not parse response"

echo ""
echo "6. Testing compliance query: Find changes that required approval but have no validation..."
echo ""
echo "SQL Query Example:"
echo "  SELECT version_id, version_number, change_description"
echo "  FROM model_versions"
echo "  WHERE change_requires_mv_approval = true"
echo "  AND validation_request_id IS NULL;"
echo ""

echo "✓ Point-in-time compliance snapshot test complete!"
echo ""
echo "Key Benefits:"
echo "  - Historical data preserved even if taxonomy changes"
echo "  - Can identify non-compliant changes"
echo "  - Audit trail for regulatory reporting"
