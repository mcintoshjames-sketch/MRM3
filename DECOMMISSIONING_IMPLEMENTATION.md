# Model Decommissioning Implementation Plan

## Overview

Implement a model retirement/decommissioning workflow that allows models to be gracefully retired with proper approvals, replacement tracking, and gap analysis.

## Status Flow

```
PENDING → VALIDATOR_APPROVED → APPROVED
    ↓              ↓
 REJECTED      REJECTED
    ↓              ↓
WITHDRAWN    WITHDRAWN
```

## Approval Stages

### Stage 1: Dual Approval Gate (Validator + Owner)

The Stage 1 approval implements a **dual-gate pattern** when the requestor is not the model owner:

| Scenario | Required Approvals |
|----------|-------------------|
| Requestor IS the model owner | Validator only |
| Requestor is NOT the model owner | Validator + Model Owner (in parallel) |

**Validator Review:**
- Request starts in `PENDING`
- Appears on ALL Validator dashboards
- ANY Validator can approve/reject (first-come)
- Must provide comment
- On approval:
  - If owner approval required AND owner hasn't approved → stays `PENDING`
  - Otherwise → moves to `VALIDATOR_APPROVED`

**Owner Review (when required):**
- Only appears if `owner_approval_required = True`
- Model owner (or Admin) can approve/reject
- Must provide comment
- Can be done in parallel with Validator review (either can go first)
- On approval:
  - If validator hasn't approved → stays `PENDING`
  - If validator already approved → moves to `VALIDATOR_APPROVED`
- On rejection → moves to `REJECTED` (terminates workflow)

**Stage 1 → Stage 2 Gate:**
- When both Validator AND Owner (if required) have approved
- Status changes to `VALIDATOR_APPROVED`
- Stage 2 approval records are created

### Stage 2: Management Approvals
- Global Approver approval required (always)
- Regional Approver approval required for EACH region the model is deployed in
- When ALL required approvals complete → moves to `APPROVED`
- Model status updated to `RETIRED`

## Key Business Rules

### Reason-Based Logic
- Reasons `REPLACEMENT` and `CONSOLIDATION` require a replacement model
- Other reasons (BUSINESS_EXIT, VOLUME_THRESHOLD, etc.) do not require replacement

### Gap Analysis
- If replacement model's implementation date > retiring model's last production date:
  - Gap exists (no model running for X days)
  - `gap_justification` field becomes MANDATORY
- If replacement model's implementation date <= last production date:
  - No gap, justification not required

### Replacement Model Date Handling
- When selecting replacement, check if it has an implementation date (from ModelVersion.production_date)
- If no implementation date exists:
  - User must specify one via `replacement_implementation_date`
  - System creates a new ModelVersion with that production_date
- If implementation date exists:
  - Display as read-only

### Withdrawal Rules
- Allowed by: Admin OR the creator of the request
- Allowed in statuses: PENDING, VALIDATOR_APPROVED (not after APPROVED/REJECTED)

## Database Schema

### decommissioning_requests
| Column | Type | Description |
|--------|------|-------------|
| request_id | SERIAL PK | |
| model_id | FK → models | Model being retired |
| status | VARCHAR(30) | PENDING, VALIDATOR_APPROVED, APPROVED, REJECTED, WITHDRAWN |
| reason_id | FK → taxonomy_values | From "Model Decommission Reason" taxonomy |
| replacement_model_id | FK → models | Optional replacement |
| last_production_date | DATE | When retiring model stops |
| gap_justification | TEXT | Required if gap detected |
| archive_location | TEXT | Required artifact location |
| downstream_impact_verified | BOOLEAN | Must be TRUE |
| created_at | TIMESTAMP | |
| created_by_id | FK → users | |
| validator_reviewed_by_id | FK → users | Stage 1 - Validator reviewer |
| validator_reviewed_at | TIMESTAMP | |
| validator_comment | TEXT | |
| owner_approval_required | BOOLEAN | TRUE if requestor ≠ model owner |
| owner_reviewed_by_id | FK → users | Stage 1 - Owner reviewer |
| owner_reviewed_at | TIMESTAMP | |
| owner_comment | TEXT | |
| final_reviewed_at | TIMESTAMP | |
| rejection_reason | TEXT | |

### decommissioning_status_history
| Column | Type | Description |
|--------|------|-------------|
| history_id | SERIAL PK | |
| request_id | FK | |
| old_status | VARCHAR(30) | |
| new_status | VARCHAR(30) | |
| changed_by_id | FK → users | |
| changed_at | TIMESTAMP | |
| notes | TEXT | |

### decommissioning_approvals
| Column | Type | Description |
|--------|------|-------------|
| approval_id | SERIAL PK | |
| request_id | FK | |
| approver_type | VARCHAR(20) | GLOBAL, REGIONAL |
| region_id | FK → regions | NULL for GLOBAL |
| approved_by_id | FK → users | |
| approved_at | TIMESTAMP | |
| is_approved | BOOLEAN | NULL=pending |
| comment | TEXT | |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/decommissioning/` | POST | Create request (sets owner_approval_required) |
| `/decommissioning/` | GET | List requests |
| `/decommissioning/{id}` | GET | Get request details |
| `/decommissioning/{id}/validator-review` | POST | Validator approve/reject (Stage 1) |
| `/decommissioning/{id}/owner-review` | POST | Owner approve/reject (Stage 1, when required) |
| `/decommissioning/{id}/approvals/{approval_id}` | POST | Global/Regional approval (Stage 2) |
| `/decommissioning/{id}/withdraw` | POST | Withdraw request |
| `/decommissioning/pending-validator-review` | GET | Dashboard: for validators |
| `/decommissioning/my-pending-owner-reviews` | GET | Dashboard: for model owners |
| `/decommissioning/my-pending-approvals` | GET | Dashboard: for approvers |
| `/decommissioning/models/{id}/implementation-date` | GET | Check model's implementation date |
| `/decommissioning/{id}` | PATCH | Update request (PENDING only, creator/Admin) |

## Frontend

### New Page: DecommissioningRequestPage
- Route: `/models/:id/decommission`
- Form with conditional fields based on reason selection
- Dynamic gap calculation
- Implementation date handling for replacement model
- **Downstream Dependency Warning**: Fetches outbound dependencies from `/models/{id}/dependencies/outbound`
  - Shows amber warning banner listing all downstream consumer models
  - Each consumer model links to its details page
  - Shows dependency type (INPUT_DATA, SCORE, etc.)
  - Updates checkbox text to reference specific number of consumers

### New Page: PendingDecommissioningPage
- Route: `/pending-decommissioning`
- Access: Admin and Validator roles only
- Lists decommissioning requests pending validator review
- Columns: Model (link), Reason, Last Production Date (with urgency badge), Requested By, Requested On, Status, Actions
- Urgency badges: "Overdue" (red), "Due Soon" (≤7 days, orange), "Upcoming" (≤30 days, yellow)
- Links to model details and decommission review page

### Navigation
- "Pending Decommissioning" link added to sidebar navigation
- Accessible by ALL authenticated users (not just Admin/Validator)
  - Admin/Validator: See requests pending validator review
  - Model Owners: See requests pending owner review for their models
- Purple badge shows count of pending requests
- Similar pattern to "Pending Deployments"

### ModelDetailsPage Enhancements
- **Decommissioning Tab**: Always visible for all models
  - Shows all decommissioning requests for the model
  - Shows request cards with status, reason, dates, and links
  - **"Initiate Decommissioning" button**: Purple button shown when:
    - Model status is not Retired/Decommissioned
    - No active request exists (PENDING or VALIDATOR_APPROVED)
  - Empty state message guides users to click the button
- **Alert Banner**: Purple banner on Details tab when model has pending decommissioning
  - Format: "This model has an active decommissioning request with status: **{status}** ({last_production_date})."
  - Only shows for PENDING, VALIDATOR_APPROVED, or APPROVED statuses

### Form Fields
| Field | Condition | Required |
|-------|-----------|----------|
| Retirement Reason | Always | Yes |
| Replacement Model | If reason requires replacement | Conditional |
| Replacement Implementation Date | If replacement has no date | Conditional |
| Last Production Date | Always | Yes |
| Gap Justification | If gap detected | Conditional |
| Archive Location | Always | Yes |
| Downstream Impact Verified | Always | Yes (checkbox) |

### UI Text Definitions
1. **gap_justification**
   - Label: "Interim Risk Management Plan"
   - Help: "You have indicated a gap between the old model's retirement and the new model's activation. Please describe the manual controls or alternative monitoring in place to manage risk during this period."

2. **archive_location**
   - Label: "Artifact Archival Path"
   - Placeholder: "e.g., https://bitbucket.org/repo/tags/v1.0-final"
   - Help: "Provide the link to the frozen code, data, and documentation."

3. **downstream_impact_verified**
   - Label: "I certify that downstream consumers have been notified."
   - Help: "Ensure that any reports, feeds, or other models relying on this output have been re-pointed or notified."

4. **replacement_model_id**
   - Label: "Select Replacement Model"
   - Help: "Select the model that is taking over this function."

5. **implementation_date** (for replacement)
   - Label: "Replacement Implementation Date"
   - Help: "The selected replacement model does not have a confirmed start date. Please specify when it is expected to go live."

## Implementation Progress

- [x] Database migration (initial tables)
- [x] Database migration (owner approval columns)
- [x] ORM models (with owner review relationships)
- [x] Pydantic schemas (with owner review fields)
- [x] API router (all endpoints including owner-review)
- [x] Register router in main.py
- [x] Frontend page (with dual approval UI)
- [x] Frontend route/navigation
- [x] Decommissioning tab on ModelDetailsPage
- [x] Alert banner for pending decommissioning
- [x] PendingDecommissioningPage for Validator/Admin review
- [x] Navigation link with badge count
- [x] Backend tests (26 passing - includes PATCH endpoint tests)
- [x] Audit logging for all mutating operations
- [x] PATCH endpoint for updating requests (PENDING only)
- [x] Model owner navigation access (my-pending-owner-reviews)
- [x] Downstream dependency warning on DecommissioningRequestPage
- [x] "Initiate Decommissioning" button in Decommissioning tab
- [ ] Frontend tests for decommissioning pages
- [x] Update ARCHITECTURE.md

## Files Created/Modified

### Created
- `api/alembic/versions/d4e5f6a7b8c9_add_decommissioning_tables.py`
- `api/alembic/versions/e5f6a7b8c9d0_add_owner_approval_to_decommissioning.py`
- `api/app/models/decommissioning.py`
- `api/app/schemas/decommissioning.py`
- `api/app/api/decommissioning.py`
- `api/tests/test_decommissioning.py`
- `web/src/pages/DecommissioningRequestPage.tsx`
- `web/src/pages/PendingDecommissioningPage.tsx`

### Modified
- `api/app/models/__init__.py` - Export decommissioning models
- `api/app/main.py` - Register decommissioning router
- `web/src/App.tsx` - Add decommissioning routes (`/models/:id/decommission`, `/pending-decommissioning`)
- `web/src/pages/ModelDetailsPage.tsx` - Add Decommissioning tab and alert banner
- `web/src/components/Layout.tsx` - Add pending decommissioning count and navigation link
