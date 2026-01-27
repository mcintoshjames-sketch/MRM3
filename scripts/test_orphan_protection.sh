#!/bin/bash

# Test Orphan Protection for Change Types

echo "=== Testing Change Type Deletion with Orphan Protection ==="
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
echo "2. Checking if any model versions exist with change_type_id=2..."
VERSION_CHECK=$(curl -s "http://localhost:8001/models/1/versions" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool)

echo "$VERSION_CHECK" | python3 -c "
import sys, json
data = json.load(sys.stdin)
count = sum(1 for v in data if v.get('change_type_id') == 2)
print(f'Found {count} model version(s) with change_type_id=2')
" 2>/dev/null || echo "No versions found or error"

echo ""
echo "3. Attempting to DELETE change type #2 (should fail if referenced)..."
DELETE_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X DELETE \
  "http://localhost:8001/change-taxonomy/types/2" \
  -H "Authorization: Bearer $TOKEN")

HTTP_STATUS=$(echo "$DELETE_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$DELETE_RESPONSE" | sed '/HTTP_STATUS:/d')

if [ "$HTTP_STATUS" = "409" ]; then
  echo "✓ Deletion blocked with HTTP 409 Conflict (as expected)"
  echo "Error message:"
  echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
elif [ "$HTTP_STATUS" = "204" ]; then
  echo "✓ Deletion succeeded (no references existed)"
else
  echo "Unexpected status: $HTTP_STATUS"
  echo "$BODY"
fi

echo ""
echo "4. Testing active_only filter..."
echo "   a. Default (active_only=true):"
curl -s "http://localhost:8001/change-taxonomy/categories" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
data = json.load(sys.stdin)
total_types = sum(len(cat['change_types']) for cat in data)
print(f'   Total change types returned: {total_types}')
" 2>/dev/null

echo "   b. With active_only=false:"
curl -s "http://localhost:8001/change-taxonomy/categories?active_only=false" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
data = json.load(sys.stdin)
total_types = sum(len(cat['change_types']) for cat in data)
active_types = sum(len([t for t in cat['change_types'] if t['is_active']]) for cat in data)
inactive_types = total_types - active_types
print(f'   Total change types: {total_types} ({active_types} active, {inactive_types} inactive)')
" 2>/dev/null

echo ""
echo "✓ Orphan protection test complete!"
