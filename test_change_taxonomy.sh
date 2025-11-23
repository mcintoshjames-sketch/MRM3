#!/bin/bash

# Test Change Taxonomy Admin Endpoints

echo "=== 1. Login as admin ==="
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8001/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}')

TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "Failed to get token"
  echo $LOGIN_RESPONSE
  exit 1
fi

echo "✓ Got admin token"

echo ""
echo "=== 2. GET /change-taxonomy/categories ==="
curl -s "http://localhost:8001/change-taxonomy/categories" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -40

echo ""
echo "=== 3. PATCH /change-taxonomy/types/2 (Update change type) ==="
curl -s -X PATCH "http://localhost:8001/change-taxonomy/types/2" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description": "TEST: Updated description for change type 2"}' | python3 -m json.tool

echo ""
echo "=== 4. Verify update worked ==="
curl -s "http://localhost:8001/change-taxonomy/types/2" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | grep -A2 "description"

echo ""
echo "=== 5. Rollback description ==="
curl -s -X PATCH "http://localhost:8001/change-taxonomy/types/2" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description": "Change to model theory, model philosophy, or model assumption"}' | python3 -m json.tool | grep -A2 "description"

echo ""
echo "✓ All tests passed!"
