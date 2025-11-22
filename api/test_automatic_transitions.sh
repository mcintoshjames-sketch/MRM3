#!/bin/bash
# Test automatic version status transitions

TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbkBleGFtcGxlLmNvbSIsImV4cCI6MTc2Mzg1NzMzMH0.5hyREOEOA7VwYG_BlpMJ0fIPMGf7RL2VOHdA6yqOuSg"

echo "=============================================================================="
echo "TESTING AUTOMATIC VERSION STATUS TRANSITIONS"
echo "=============================================================================="

echo ""
echo "Step 1: Get current status of version 64 (should be IN_VALIDATION)"
echo "----------------------------------------------------------------------"
curl -s "http://localhost:8001/models/45/versions" \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
for v in data:
    if v['version_id'] == 64:
        print(f\"Version {v['version_id']}: {v['version_number']}\")
        print(f\"  Status: {v['status']}\")
        print(f\"  Validation Request: {v['validation_request_id']}\")
"

echo ""
echo "Step 2: Check validation request #49 status (should be IN_PROGRESS)"
echo "----------------------------------------------------------------------"
curl -s "http://localhost:8001/validation-workflow/requests/49" \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"Validation Request {data['request_id']}\")
print(f\"  Status: {data['current_status']}\")
print(f\"  Models: {', '.join(data['model_names'])}\")
"

echo ""
echo "Step 3: Transition validation request #49 to REVIEW status"
echo "----------------------------------------------------------------------"

# Get REVIEW status ID
REVIEW_STATUS_ID=$(curl -s "http://localhost:8001/taxonomies/Validation%20Request%20Status/values" \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
for item in data:
    if item['code'] == 'REVIEW':
        print(item['value_id'])
        break
")

echo "REVIEW status ID: $REVIEW_STATUS_ID"

curl -s -X PATCH "http://localhost:8001/validation-workflow/requests/49/status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"new_status_id\": $REVIEW_STATUS_ID, \"change_reason\": \"Testing automatic version status transition\"}" | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"✓ Validation request updated to: {data['current_status']}\")
"

echo ""
echo "Step 4: Verify version status (should still be IN_VALIDATION)"
echo "----------------------------------------------------------------------"
curl -s "http://localhost:8001/models/45/versions" \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
for v in data:
    if v['version_id'] == 64:
        print(f\"Version {v['version_id']}: {v['version_number']}\")
        print(f\"  Status: {v['status']} (should still be IN_VALIDATION)\")
"

echo ""
echo "=============================================================================="
echo "TEST SUMMARY"
echo "=============================================================================="
echo "The version status should remain IN_VALIDATION because REVIEW status"
echo "does not trigger an automatic transition. Only these transitions are automatic:"
echo ""
echo "  1. DRAFT → IN_VALIDATION (when validation moves to IN_PROGRESS)"
echo "  2. IN_VALIDATION → APPROVED (when validation moves to APPROVED)"
echo "  3. IN_VALIDATION → DRAFT (when validation moves to CANCELLED/ON_HOLD)"
echo "  4. APPROVED → ACTIVE (manual via /versions/{id}/activate endpoint)"
echo "  5. Previous ACTIVE → SUPERSEDED (automatic when new version activated)"
echo ""
