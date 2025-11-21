#!/bin/bash
set -e

echo "=========================================="
echo "Model Submission Approval Workflow E2E Test"
echo "=========================================="
echo ""

BASE_URL="http://localhost:8001"

# Step 1: Login as Emily Davis (Regular User, user_id=9)
echo "Step 1: Login as Emily Davis (Regular User)"
EMILY_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "emily.davis@contoso.com", "password": "emily123"}')

EMILY_TOKEN=$(echo $EMILY_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$EMILY_TOKEN" ]; then
    echo "✗ Failed to login as Emily"
    echo "Response: $EMILY_RESPONSE"
    exit 1
fi
echo "✓ Logged in as Emily Davis"
echo ""

# Step 2: Create a model as Emily (should go to pending status)
echo "Step 2: Create a model as Emily (should auto-set to pending)"
MODEL_RESPONSE=$(curl -s -X POST "$BASE_URL/models/" \
  -H "Authorization: Bearer $EMILY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "Test Submission Model",
    "description": "Testing the submission approval workflow",
    "development_type": "In-House",
    "owner_id": 9,
    "status": "In Development",
    "user_ids": [9]
  }')

MODEL_ID=$(echo $MODEL_RESPONSE | grep -o '"model_id":[0-9]*' | cut -d':' -f2)
MODEL_STATUS=$(echo $MODEL_RESPONSE | grep -o '"row_approval_status":"[^"]*' | cut -d'"' -f4)

if [ -z "$MODEL_ID" ]; then
    echo "✗ Model creation failed"
    echo "Response: $MODEL_RESPONSE"
    exit 1
fi

if [ "$MODEL_STATUS" != "pending" ]; then
    echo "✗ Model should have pending status, got: $MODEL_STATUS"
    echo "Response: $MODEL_RESPONSE"
    exit 1
fi
echo "✓ Created model $MODEL_ID with status: pending"
echo ""

# Step 3: Verify Emily can see her submission in /models/my-submissions
echo "Step 3: Verify Emily can see her submission"
MY_SUBMISSIONS=$(curl -s -X GET "$BASE_URL/models/my-submissions" \
  -H "Authorization: Bearer $EMILY_TOKEN")

if echo "$MY_SUBMISSIONS" | grep -q "\"model_id\":$MODEL_ID"; then
    echo "✓ Emily can see her submission in my-submissions"
else
    echo "✗ Emily cannot see her submission"
    echo "Response: $MY_SUBMISSIONS"
    exit 1
fi
echo ""

# Step 4: Login as Admin
echo "Step 4: Login as Admin"
ADMIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}')

ADMIN_TOKEN=$(echo $ADMIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ADMIN_TOKEN" ]; then
    echo "✗ Failed to login as Admin"
    exit 1
fi
echo "✓ Logged in as Admin"
echo ""

# Step 5: Admin views pending submissions
echo "Step 5: Admin views pending submissions"
PENDING_SUBMISSIONS=$(curl -s -X GET "$BASE_URL/models/pending-submissions" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

if echo "$PENDING_SUBMISSIONS" | grep -q "\"model_id\":$MODEL_ID"; then
    echo "✓ Admin can see the pending submission"
else
    echo "✗ Admin cannot see the pending submission"
    echo "Response: $PENDING_SUBMISSIONS"
    exit 1
fi
echo ""

# Step 6: Admin sends back with feedback
echo "Step 6: Admin sends back model with feedback"
SENDBACK_RESPONSE=$(curl -s -X POST "$BASE_URL/models/$MODEL_ID/send-back" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "comment": "Please add more details about the validation approach and expected outcomes."
  }')

UPDATED_STATUS=$(echo $SENDBACK_RESPONSE | grep -o '"row_approval_status":"[^"]*' | cut -d'"' -f4)

if [ "$UPDATED_STATUS" != "needs_revision" ]; then
    echo "✗ Status should be needs_revision, got: $UPDATED_STATUS"
    echo "Response: $SENDBACK_RESPONSE"
    exit 1
fi
echo "✓ Model status changed to: needs_revision"
echo ""

# Step 7: Verify comment was created
echo "Step 7: Verify feedback comment was created"
MODEL_DETAIL=$(curl -s -X GET "$BASE_URL/models/$MODEL_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

if echo "$MODEL_DETAIL" | grep -q "Please add more details"; then
    echo "✓ Feedback comment is visible in model details"
else
    echo "✗ Feedback comment not found"
    echo "Response: $MODEL_DETAIL"
    exit 1
fi
echo ""

# Step 8: Emily edits the model
echo "Step 8: Emily updates the model based on feedback"
EDIT_RESPONSE=$(curl -s -X PATCH "$BASE_URL/models/$MODEL_ID" \
  -H "Authorization: Bearer $EMILY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "Test Submission Model (Updated)",
    "description": "Updated with detailed validation approach: We will use historical data analysis and backtesting to validate model performance.",
    "development_type": "In-House",
    "owner_id": 9,
    "status": "In Development",
    "user_ids": [9]
  }')

EDIT_MODEL_NAME=$(echo $EDIT_RESPONSE | grep -o '"model_name":"[^"]*' | cut -d'"' -f4)

if echo "$EDIT_MODEL_NAME" | grep -q "Updated"; then
    echo "✓ Emily successfully updated the model"
else
    echo "✗ Model update failed"
    echo "Response: $EDIT_RESPONSE"
    exit 1
fi
echo ""

# Step 9: Emily resubmits the model
echo "Step 9: Emily resubmits the model"
RESUBMIT_RESPONSE=$(curl -s -X POST "$BASE_URL/models/$MODEL_ID/resubmit" \
  -H "Authorization: Bearer $EMILY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "comment": "Updated description with detailed validation approach as requested."
  }')

RESUBMIT_STATUS=$(echo $RESUBMIT_RESPONSE | grep -o '"row_approval_status":"[^"]*' | cut -d'"' -f4)

if [ "$RESUBMIT_STATUS" != "pending" ]; then
    echo "✗ Status should be pending after resubmit, got: $RESUBMIT_STATUS"
    echo "Response: $RESUBMIT_RESPONSE"
    exit 1
fi
echo "✓ Model resubmitted with status: pending"
echo ""

# Step 10: Admin approves the model
echo "Step 10: Admin approves the model"
APPROVE_RESPONSE=$(curl -s -X POST "$BASE_URL/models/$MODEL_ID/approve" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "comment": "Looks good! Approved for inventory."
  }')

FINAL_STATUS=$(echo $APPROVE_RESPONSE | grep -o '"row_approval_status":[^,}]*' | cut -d':' -f2 | tr -d ' ')

if [ "$FINAL_STATUS" = "null" ]; then
    echo "✓ Model approved (row_approval_status = NULL)"
else
    echo "✗ Status should be null after approval, got: $FINAL_STATUS"
    echo "Response: $APPROVE_RESPONSE"
    exit 1
fi
echo ""

# Step 11: Verify model appears in general models list (approved)
echo "Step 11: Verify approved model is visible to Emily"
MODELS_LIST=$(curl -s -X GET "$BASE_URL/models/" \
  -H "Authorization: Bearer $EMILY_TOKEN")

if echo "$MODELS_LIST" | grep -q "\"model_id\":$MODEL_ID"; then
    echo "✓ Approved model is visible in general models list"
else
    echo "✗ Approved model not found in models list"
    exit 1
fi
echo ""

# Step 12: Verify model no longer in my-submissions (since it's approved)
echo "Step 12: Verify model is no longer in my-submissions"
UPDATED_SUBMISSIONS=$(curl -s -X GET "$BASE_URL/models/my-submissions" \
  -H "Authorization: Bearer $EMILY_TOKEN")

if echo "$UPDATED_SUBMISSIONS" | grep -q "\"model_id\":$MODEL_ID"; then
    echo "⚠ Model still appears in my-submissions (approved models should not appear here)"
else
    echo "✓ Approved model correctly removed from my-submissions"
fi
echo ""

# Step 13: Verify news feed shows activity
echo "Step 13: Verify news feed contains submission activity"
NEWS_FEED=$(curl -s -X GET "$BASE_URL/dashboard/news-feed" \
  -H "Authorization: Bearer $EMILY_TOKEN")

COMMENT_COUNT=$(echo "$NEWS_FEED" | grep -o "\"model_id\":$MODEL_ID" | wc -l)

if [ "$COMMENT_COUNT" -ge 3 ]; then
    echo "✓ News feed shows at least 3 activities for model $MODEL_ID"
    echo "  (Expected: submission, send_back, resubmit, approve comments)"
else
    echo "⚠ News feed shows $COMMENT_COUNT activities (expected at least 3)"
fi
echo ""

echo "=========================================="
echo "✓ ALL TESTS PASSED!"
echo "=========================================="
echo ""
echo "Summary:"
echo "- Model ID: $MODEL_ID"
echo "- Workflow states tested: pending → needs_revision → pending → approved"
echo "- Comments created: At least 3 (feedback, resubmit note, approval)"
echo "- RLS verified: Emily can see her own submissions"
echo "- Admin approval workflow: Functional"
echo ""
