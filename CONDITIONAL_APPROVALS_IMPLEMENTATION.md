# Conditional Model Use Approvals - Implementation Plan

## Overview
Implement configurable conditional approval requirements for model use based on model attributes and validation context.

## Business Requirements Summary

### Key Decisions
1. **Rule Evaluation Timing**:
   - Evaluate when validation request created
   - Re-evaluate when moving to "Pending Approval" status (handles null risk tiers)
   - Admin can void approval requirements with reason

2. **Deployed Regions**: All regions in `model_regions` table

3. **Region Matching**: Rule applies if ANY overlap between model regions and rule regions

4. **Retroactive Rules**: Only apply to new validations (or re-evaluation at Pending Approval)

5. **Who Can Approve**: Any Admin can approve on behalf of any role with evidence description

6. **Status Tracking**: Add `Model.use_approval_date` datetime field (timestamp of last/final approval)

7. **Rule Logic**:
   - Within dimension (e.g., validation_type_ids=[1,2]): OR logic (matches if 1 OR 2)
   - Across dimensions: AND logic (ALL non-empty dimensions must match)
   - Empty/null field = no constraint (matches ANY)

8. **UI Requirement**: Show English-language translation of rules

## Data Model

### New Tables

#### 1. approver_roles
```sql
- role_id (PK)
- role_name (unique, not null)
- description (text, nullable)
- is_active (boolean, default true)
- created_at, updated_at
```

#### 2. conditional_approval_rules
```sql
- rule_id (PK)
- rule_name (not null)
- description (text, nullable)
- is_active (boolean, default true)
- validation_type_ids (text, nullable) -- comma-separated
- risk_tier_ids (text, nullable) -- comma-separated
- governance_region_ids (text, nullable) -- comma-separated
- deployed_region_ids (text, nullable) -- comma-separated
- created_at, updated_at
```

#### 3. rule_required_approvers
```sql
- id (PK)
- rule_id (FK to conditional_approval_rules, CASCADE)
- approver_role_id (FK to approver_roles, CASCADE)
```

### Schema Changes

#### validation_approvals
- Add `approver_role_id` (FK to approver_roles, SET NULL)
- Add `approval_evidence` (text) - description of evidence
- Add `voided_by_id` (FK to users, SET NULL)
- Add `void_reason` (text)
- Add `voided_at` (datetime)

#### models
- Add `use_approval_date` (datetime) - timestamp of final approval

## Implementation Status

### ✅ Completed (2025-11-23)

**Backend Implementation:**
1. Database migration created and applied (edab17d6ee8f)
2. ORM models created (ApproverRole, ConditionalApprovalRule, RuleRequiredApprover)
3. Model and ValidationApproval ORM models updated (use_approval_date, approver_role_id, voiding fields)
4. Rule evaluation logic implemented with English translation (app/core/rule_evaluation.py)
5. API endpoints for ApproverRole CRUD (app/api/approver_roles.py)
6. API endpoints for ConditionalApprovalRule CRUD (app/api/conditional_approval_rules.py)
7. Integrated rule evaluation into validation workflow (evaluate on creation + Pending Approval status)
8. Conditional approval submission endpoint with evidence tracking
9. Approval voiding endpoint with reason tracking
10. Audit logging for approval actions (CONDITIONAL_APPROVAL_SUBMIT, CONDITIONAL_APPROVAL_VOID)
11. Sample data seeding for UAT (5 approver roles, 4 conditional rules)

**Frontend Implementation:**
12. Admin UI for ApproverRoles management (web/src/pages/ApproverRolesPage.tsx)
13. Admin UI for ConditionalApprovalRules with live rule translation preview (web/src/pages/ConditionalApprovalRulesPage.tsx)
14. Conditional approvals section component (web/src/components/ConditionalApprovalsSection.tsx)
15. Extended ValidationRequestDetailPage Approvals tab with conditional approvals UI
16. Navigation routes and links added (App.tsx, Layout.tsx)

### 📋 Pending

**Testing & Documentation:**
- Backend unit tests for rule evaluation and approval flow
- Frontend component tests for new pages
- Update ARCHITECTURE.md with conditional approvals feature description
- Update REGRESSION_TESTS.md with test coverage plan

## Rule Evaluation Logic

### Core Function: `get_required_approver_roles(validation_request, model)`

**Inputs**:
- `validation_request`: ValidationRequest entity (has validation_type_id)
- `model`: Model entity (has risk_tier_id, wholly_owned_region_id, model_regions)

**Logic**:
1. Fetch all active ConditionalApprovalRules
2. For each rule, check if model/validation match:
   - **validation_type_ids**: If not empty, check if validation_type_id IN parsed list
   - **risk_tier_ids**: If not empty, check if model.risk_tier_id IN parsed list
   - **governance_region_ids**: If not empty, check if model.wholly_owned_region_id IN parsed list
   - **deployed_region_ids**: If not empty, check if ANY model.model_regions.region_id IN parsed list
   - If ALL non-empty dimensions match → rule applies
3. Collect all approver roles from matching rules
4. Deduplicate by role_id
5. For each required role, check if approval already exists (and not voided)

**Output**:
```python
{
    "required_roles": [
        {
            "role_id": 1,
            "role_name": "US Model Risk Management Committee",
            "description": "...",
            "approval_status": "pending" | "approved" | None
        }
    ],
    "rule_explanation": "English translation of why these roles are required"
}
```

### English Translation Function

For each rule that applies, generate text like:
```
"US Model Risk Management Committee approval required because:
- Validation type is Initial Validation OR Conceptual Review
- Model inherent risk tier is High (Tier 1)
- Model governance region is US wholly-owned"
```

## API Endpoints

### ApproverRole Management
- `GET /approver-roles/` - List all roles (filter by is_active)
- `POST /approver-roles/` - Create new role (Admin only)
- `GET /approver-roles/{id}` - Get role details
- `PATCH /approver-roles/{id}` - Update role (Admin only)
- `DELETE /approver-roles/{id}` - Soft delete (set is_active=false, Admin only)

### ConditionalApprovalRule Management
- `GET /conditional-approval-rules/` - List all rules (filter by is_active)
- `POST /conditional-approval-rules/` - Create new rule (Admin only)
- `GET /conditional-approval-rules/{id}` - Get rule details with English translation
- `PATCH /conditional-approval-rules/{id}` - Update rule (Admin only)
- `DELETE /conditional-approval-rules/{id}` - Soft delete (Admin only)
- `POST /conditional-approval-rules/preview` - Preview rule translation before saving

### Conditional Approvals
- `GET /validation-workflow/requests/{id}/conditional-approvals` - Get required approvals for validation
- `POST /validation-workflow/approvals/{id}/submit-conditional` - Admin submits conditional approval with evidence
- `POST /validation-workflow/approvals/{id}/void` - Admin voids approval requirement with reason

## UI Components

### Admin Pages
1. **ApproverRolesPage** (`/approver-roles`)
   - List view with name, description, active status, # of rules using it
   - Create/Edit modal
   - Deactivate button

2. **ConditionalApprovalRulesPage** (`/conditional-approval-rules`)
   - List view with rule name, conditions summary, required approvers
   - Create/Edit form with:
     - Name, description, active toggle
     - Multi-select dropdowns for each dimension
     - Multi-select for required approver roles
     - **Live preview** showing English translation of rule
   - Delete/deactivate button

### End-User UI
3. **Extend ValidationRequestDetailPage Approvals Tab**
   - Show traditional approvals section (existing)
   - Show "Conditional Model Use Approvals" section:
     - List each required approver role
     - Show status: Pending / Approved / Voided
     - For approved: show who approved, when, evidence description
     - For pending: Admin can "Approve as [Role]" with evidence field
     - Admin can void requirement with reason
   - Show overall status banner if conditional approvals pending

## Testing Plan

### Backend Unit Tests
1. Rule evaluation logic:
   - No rules configured → empty list
   - Single rule matches → one role required
   - Multiple rules match → deduplicated roles
   - Partial dimension matches → rule does not apply
   - Empty dimensions → rule applies to any value
   - Deployed regions ANY overlap logic
2. English translation generation
3. Approval voiding logic

### Backend Integration Tests
1. Create/read/update/delete approver roles
2. Create/read/update/delete conditional rules
3. Rule evaluation at validation creation
4. Rule re-evaluation at Pending Approval status
5. Conditional approval submission
6. Approval voiding
7. Model.use_approval_date updated when final approval granted

### Frontend Tests
- Component rendering for ApproverRolesPage
- Component rendering for ConditionalApprovalRulesPage
- Rule translation preview
- Conditional approval UI in ValidationRequestDetailPage

## Migration Path

1. Deploy schema changes (already done)
2. Deploy backend code with new endpoints
3. Deploy frontend UI
4. Document for admins how to configure rules
5. No impact on existing validations (retroactive rules not applied)

## Files Modified/Created

### Backend
- ✅ `api/alembic/versions/edab17d6ee8f_*.py` - Migration
- ✅ `api/app/models/conditional_approval.py` - New models
- ✅ `api/app/models/model.py` - Add use_approval_date field
- ✅ `api/app/models/validation.py` - Extend ValidationApproval model
- ✅ `api/app/api/approver_roles.py` - New router
- ✅ `api/app/api/conditional_approval_rules.py` - New router
- ✅ `api/app/api/validation_workflow.py` - Extend for conditional approvals
- ✅ `api/app/schemas/conditional_approval.py` - Pydantic schemas
- ✅ `api/app/core/rule_evaluation.py` - Rule matching and translation logic
- ✅ `api/app/seed.py` - Sample data for UAT
- ✅ `api/app/main.py` - Register new routers
- 📋 `api/tests/test_conditional_approvals.py` - Tests (pending)

### Frontend
- ✅ `web/src/pages/ApproverRolesPage.tsx`
- ✅ `web/src/pages/ConditionalApprovalRulesPage.tsx`
- ✅ `web/src/pages/ValidationRequestDetailPage.tsx` - Extend Approvals tab
- ✅ `web/src/components/ConditionalApprovalsSection.tsx`
- ✅ `web/src/App.tsx` - Add routes
- ✅ `web/src/components/Layout.tsx` - Add navigation links

### Documentation
- 🚧 `ARCHITECTURE.md` - Document conditional approvals (in progress)
- 🚧 `REGRESSION_TESTS.md` - Add test coverage (in progress)
