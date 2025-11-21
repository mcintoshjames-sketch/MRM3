#!/bin/bash
set -e

echo "=== Testing Regional Version Workflow ==="
echo

# Get token
echo "1. Getting auth token..."
TOKEN=$(curl -s -X POST "http://localhost:8001/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "✓ Token obtained"
echo

# Get models
echo "2. Fetching models..."
MODELS=$(curl -s "http://localhost:8001/models/" -H "Authorization: Bearer $TOKEN")
echo "$MODELS" | python3 -m json.tool | head -20
echo

MODEL_ID=$(echo "$MODELS" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data[0]['model_id'] if len(data) > 0 else 'none')")
echo "Using model_id: $MODEL_ID"
echo

# Get regions
echo "3. Fetching regions..."
REGIONS=$(curl -s "http://localhost:8001/regions/" -H "Authorization: Bearer $TOKEN")
echo "$REGIONS" | python3 -m json.tool
echo

REGION_ID=$(echo "$REGIONS" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data[0]['region_id'] if len(data) > 0 else 'none')")
echo "Using region_id: $REGION_ID"
echo

# Test creating a GLOBAL version
echo "4. Creating GLOBAL MINOR version..."
GLOBAL_VERSION=$(curl -s -X POST "http://localhost:8001/models/$MODEL_ID/versions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "change_type": "MINOR",
    "change_description": "Global minor update - testing scope field",
    "scope": "GLOBAL"
  }')

echo "$GLOBAL_VERSION" | python3 -m json.tool
echo

# Test creating a REGIONAL version
echo "5. Creating REGIONAL MAJOR version with validation..."
REGIONAL_VERSION=$(curl -s -X POST "http://localhost:8001/models/$MODEL_ID/versions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"change_type\": \"MAJOR\",
    \"change_description\": \"Regional major change - testing regional scope and validation creation\",
    \"scope\": \"REGIONAL\",
    \"affected_region_ids\": [$REGION_ID],
    \"planned_production_date\": \"2025-06-01\"
  }")

echo "$REGIONAL_VERSION" | python3 -m json.tool
REGIONAL_VERSION_ID=$(echo "$REGIONAL_VERSION" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('version_id', 'none'))")
echo "Created version_id: $REGIONAL_VERSION_ID"
echo

# Test regional-versions endpoint
echo "6. Testing GET /models/$MODEL_ID/regional-versions endpoint..."
REGIONAL_STATUS=$(curl -s "http://localhost:8001/models/$MODEL_ID/regional-versions" \
  -H "Authorization: Bearer $TOKEN")

echo "$REGIONAL_STATUS" | python3 -m json.tool
echo

echo "=== Test Complete ==="
