# Overdue Revalidation Tracking & Commentary Feature

## Overview

Track and manage overdue model revalidations with required commentary from responsible parties, dashboard alerts, and consolidated reporting.

## Clarified Requirements

Based on user input:

1. **"Submitted"** = when validation moves from Planning to **In Progress** (indicated by `submission_received_date` being set on ValidationRequest)
2. **Expected completion date calculation**:
   - **Post-submission (In Progress+)**: Manually input by validator (`target_completion_date` on ValidationRequest - already exists!)
   - **Pre-submission (awaiting submission)**: Target submission date (from owner) + `model_change_lead_time_days` from ValidationPolicy
3. **Multi-validator**: Any one validator can submit the shared response
4. **Enforcement**: Soft (alerts, not blocking)
5. **Lead time**: Use `model_change_lead_time_days` from ValidationPolicy (already exists, default 90 days)
6. **Visibility**: Comments visible to everyone

---

## Existing Infrastructure (Already Built)

### Revalidation Status Calculation (`calculate_model_revalidation_status`)

The system already computes these statuses dynamically:
- `Never Validated` - No prior approved validation
- `No Policy Configured` - No ValidationPolicy for risk tier
- `Upcoming` - Within normal timeline
- `Awaiting Submission` - Request exists, no submission yet, before due
- `In Grace Period` - Request exists, no submission, past due but in grace
- **`Submission Overdue`** - Request exists, no submission, past grace period
- `Validation In Progress` - Submission received, validation ongoing
- **`Validation Overdue`** - Submission received, past expected completion
- **`Revalidation Overdue (No Request)`** - Past due with no active request

### Key Dates (computed from policy)
- `submission_due` = last_completed + frequency_months
- `grace_period_end` = submission_due + 3 months
- `validation_due` = grace_period_end + model_change_lead_time_days

### Existing Fields
- `ValidationRequest.submission_received_date` - marks when submission happened
- `ValidationRequest.target_completion_date` - validator's target (already exists!)
- `ValidationPolicy.model_change_lead_time_days` - lead time (default 90 days)

---

## Two Overdue Scenarios Requiring Commentary

### Important: ValidationRequest Required

**Design Decision**: A ValidationRequest must exist before commentary can be attached.

For `Revalidation Overdue (No Request)` status:
- UI prompts user to **create a ValidationRequest first**
- Once request exists, then commentary can be added
- This ensures all overdue tracking is tied to a request for proper audit trail

### Scenario A: Pre-Submission Overdue

**Triggers**: Status is:
- `Submission Overdue` (request exists but owner hasn't submitted)

**Prerequisite for `Revalidation Overdue (No Request)`**:
- User must first create a ValidationRequest
- Then add overdue commentary

**Responsible Party**: Model Owner and/or Developer

**Required Information**:
- `reason_comment`: Why is this overdue?
- `target_submission_date`: When will you submit?

**Computed Expected Completion** (for report):
```
target_submission_date + model_change_lead_time_days
```

### Scenario B: Post-Submission (Validation) Overdue

**Triggers**: Status is:
- `Validation Overdue` (submission received but past target_completion_date)

**Responsible Party**: Any Assigned Validator

**Required Information**:
- `reason_comment`: Why is this delayed?
- `target_completion_date`: When will validation complete?

**Computed Expected Completion** (for report):
```
target_completion_date (directly from validator input)
```

---

## Comment Freshness Requirements

A comment is **stale** and must be updated when:
1. No comment exists, OR
2. Comment is older than **45 days**, OR
3. Target date has passed without resolution

---

## Data Model

### New Table: `overdue_revalidation_comments`

Commentary is always attached to a ValidationRequest (required, not optional).

```sql
CREATE TABLE overdue_revalidation_comments (
    comment_id SERIAL PRIMARY KEY,

    -- Context: ValidationRequest is REQUIRED
    validation_request_id INTEGER NOT NULL REFERENCES validation_requests(request_id) ON DELETE CASCADE,

    -- Type: determines who is responsible
    overdue_type VARCHAR(30) NOT NULL CHECK (overdue_type IN ('PRE_SUBMISSION', 'VALIDATION_IN_PROGRESS')),

    -- Content
    reason_comment TEXT NOT NULL,
    target_date DATE NOT NULL,  -- Target Submission Date OR Target Completion Date

    -- Tracking
    created_by_user_id INTEGER NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- For history: when a new comment supersedes this one
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    superseded_at TIMESTAMP WITH TIME ZONE,
    superseded_by_comment_id INTEGER REFERENCES overdue_revalidation_comments(comment_id)
);

-- Indexes for fast lookup
CREATE INDEX idx_overdue_comments_request_current ON overdue_revalidation_comments(validation_request_id, is_current) WHERE is_current = TRUE;
CREATE INDEX idx_overdue_comments_created_by ON overdue_revalidation_comments(created_by_user_id);
```

---

## API Design

### 1. Get Overdue Status & Comment for Validation Request

```
GET /validation-workflow/requests/{request_id}/overdue-commentary
```

Response:
```json
{
  "request_id": 88,
  "model_id": 42,
  "model_name": "Credit Risk Scorecard",
  "revalidation_status": "Submission Overdue",
  "overdue_type": "PRE_SUBMISSION",
  "responsible_parties": ["owner", "developer"],
  "days_overdue": 15,

  "current_comment": {
    "comment_id": 123,
    "reason_comment": "Waiting for Q4 data refresh",
    "target_date": "2025-02-15",
    "created_by": "John Smith",
    "created_at": "2025-01-05T10:30:00Z",
    "comment_age_days": 20
  },
  "comment_status": "CURRENT",  // CURRENT | STALE | MISSING
  "needs_update": false,
  "update_reason": null,  // "Comment older than 45 days" | "Target date has passed"

  "computed_completion_date": "2025-05-16",  // target_date + lead_time
  "policy_lead_time_days": 90
}
```

### 2. Submit/Update Overdue Commentary

```
POST /validation-workflow/requests/{request_id}/overdue-commentary
```

Request (Pre-submission - from owner/developer):
```json
{
  "reason_comment": "Waiting for Q4 data refresh from upstream system",
  "target_submission_date": "2025-02-15"
}
```

Request (Validation in progress - from validator):
```json
{
  "reason_comment": "Extended scope due to regulatory changes",
  "target_completion_date": "2025-03-01"
}
```

Permission checks:
- Pre-submission: Must be model owner, developer, or Admin
- Validation in progress: Must be assigned validator or Admin

### 2a. Model-Level Convenience Endpoint

For UI convenience (showing alert on ModelDetailsPage):

```
GET /models/{model_id}/overdue-commentary
```

Returns the overdue commentary status for the model's active validation request (if any).
If no request exists (`Revalidation Overdue (No Request)`), returns:
```json
{
  "model_id": 42,
  "model_name": "Credit Risk Scorecard",
  "revalidation_status": "Revalidation Overdue (No Request)",
  "needs_request_creation": true,
  "message": "Please create a validation request before providing overdue commentary"
}
```

### 3. Dashboard: My Overdue Items

```
GET /dashboard/my-overdue-items
```

Response:
```json
{
  "pre_submission_overdue": [
    {
      "model_id": 42,
      "model_name": "Credit Risk Scorecard",
      "role": "owner",  // why you're seeing this
      "days_overdue": 15,
      "comment_status": "STALE",
      "needs_update": true,
      "update_reason": "Target date has passed"
    }
  ],
  "validation_overdue": [
    {
      "request_id": 88,
      "model_name": "Market Risk VaR",
      "days_overdue": 5,
      "comment_status": "MISSING",
      "needs_update": true,
      "update_reason": "No comment provided"
    }
  ],
  "total_needing_action": 2
}
```

### 4. Dashboard: All Overdue Summary (Admin)

```
GET /dashboard/overdue-summary
```

Response:
```json
{
  "pre_submission_overdue_count": 5,
  "validation_overdue_count": 3,
  "comments_missing": 4,
  "comments_stale": 2,
  "total_overdue": 8
}
```

### 5. Overdue Revalidation Report

```
GET /reports/overdue-revalidations
```

Query params:
- `overdue_type`: filter by PRE_SUBMISSION, VALIDATION_IN_PROGRESS, or all
- `risk_tier_id`: filter by risk tier
- `comment_status`: filter by CURRENT, STALE, MISSING

Response:
```json
{
  "report_date": "2025-01-21",
  "items": [
    {
      "model_id": 42,
      "model_name": "Credit Risk Scorecard",
      "owner_name": "John Smith",
      "developer_name": "Jane Doe",
      "risk_tier": "Tier 1 (High)",

      "overdue_type": "PRE_SUBMISSION",
      "revalidation_status": "Submission Overdue",
      "days_overdue": 15,

      "validation_request_id": 88,
      "current_stage": "INTAKE",  // or null if no request

      "reason_comment": "Waiting for Q4 data refresh",
      "comment_date": "2025-01-05",
      "comment_age_days": 16,
      "comment_status": "CURRENT",

      "target_date": "2025-02-15",  // submission or completion
      "computed_completion_date": "2025-05-16",  // target + lead time (pre-submission) or just target (in-progress)
      "policy_lead_time_days": 90
    }
  ],
  "summary": {
    "total_overdue": 8,
    "pre_submission_count": 5,
    "validation_count": 3,
    "comments_current": 4,
    "comments_stale": 2,
    "comments_missing": 2
  }
}
```

---

## Frontend Components

### Consolidation with Existing Dashboard

**Important**: The AdminDashboardPage already has these widgets:
- "Overdue Submissions" (`/validation-workflow/dashboard/overdue-submissions`)
- "Overdue Validations" (`/validation-workflow/dashboard/overdue-validations`)

**Strategy**: Augment existing endpoints and widgets rather than creating duplicates.

### 1. Enhanced AdminDashboard Widgets (Augment Existing)

**Backend Enhancement**: Add commentary fields to existing dashboard endpoints:
```typescript
// Enhanced OverdueSubmission interface
interface OverdueSubmission {
    // ... existing fields (request_id, model_id, model_name, etc.) ...
    comment_status: 'CURRENT' | 'STALE' | 'MISSING';
    latest_comment: string | null;
    latest_comment_date: string | null;
    target_submission_date: string | null;  // from commentary
    needs_comment_update: boolean;
}
```

**UI Enhancement**: Add to each row in existing widgets:
- Comment status indicator (✅ Current / ⚠️ Stale / ❌ Missing)
- "Update Explanation" button (opens modal)

### 2. Three Views of Overdue Items Needing Commentary

The system provides three distinct views based on user role:

#### View 1: Admin Dashboard (All Overdue Items)
**Endpoint**: `GET /overdue-revalidation-report/`
**Who**: Admin users only
**Shows**: ALL overdue items across the organization (both PRE_SUBMISSION and VALIDATION_IN_PROGRESS)

#### View 2: Model Owner/Developer Dashboard (PRE_SUBMISSION Only)
**Endpoint**: `GET /validation-workflow/my-overdue-items`
**Who**: Model owners and developers
**Shows**: Only **PRE_SUBMISSION** items - models awaiting documentation submission where the user is the owner/developer
**When**: Submission is still pending and validation work hasn't yet begun

#### View 3: Validator Dashboard (VALIDATION_IN_PROGRESS Only)
**Endpoint**: `GET /validation-workflow/my-validator-overdue-items`
**Who**: Assigned validators
**Shows**: Only **VALIDATION_IN_PROGRESS** items - validations assigned to them that are past their target completion date
**When**: Documentation has been submitted and validation is in progress but overdue

**Important Separation of Responsibility**:
- Once a model owner submits documentation, their responsibility for overdue commentary ends
- The validation team then owns any delay explanations if the validation runs past its target
- Model owners should NOT see VALIDATION_IN_PROGRESS overdue items
- Validators should NOT see PRE_SUBMISSION overdue items (unless they're also the model owner)

### 3. Overdue Alert Banner (ModelDetailsPage)

**Location**: ModelDetailsPage header area (below approval status banner)

**When shown**: Model has status `Submission Overdue`, `Revalidation Overdue (No Request)`, or `Validation Overdue`

**Note**: Only shows ONE alert - don't duplicate with existing approval status banner.

**UI**:
```
┌─────────────────────────────────────────────────────────────────────┐
│ ⚠️ REVALIDATION OVERDUE                                             │
│                                                                     │
│ This model is 15 days past its submission deadline.                │
│                                                                     │
│ Current explanation: "Waiting for Q4 data refresh" (16 days ago)   │
│ Target submission: Feb 15, 2025                                    │
│                                                                     │
│ [Update Explanation]                                               │
└─────────────────────────────────────────────────────────────────────┘
```

**If stale/missing**:
```
┌─────────────────────────────────────────────────────────────────────┐
│ 🔴 REVALIDATION OVERDUE - EXPLANATION NEEDED                        │
│                                                                     │
│ This model is 15 days past its submission deadline.                │
│ No current explanation on file.                                    │
│                                                                     │
│ As the model owner, please provide:                                │
│ • Reason for the delay                                             │
│ • Updated target submission date                                   │
│                                                                     │
│ [Provide Explanation]                                              │
└─────────────────────────────────────────────────────────────────────┘
```

**If no ValidationRequest exists** (`Revalidation Overdue (No Request)`):
```
┌─────────────────────────────────────────────────────────────────────┐
│ 🔴 REVALIDATION OVERDUE - REQUEST NEEDED                            │
│                                                                     │
│ This model is overdue for revalidation with no active request.     │
│                                                                     │
│ To track this overdue revalidation:                                │
│ 1. Create a validation request for this model                      │
│ 2. Then provide an explanation for the delay                       │
│                                                                     │
│ [Create Validation Request]                                        │
└─────────────────────────────────────────────────────────────────────┘
```

### 4. Overdue Alert Banner (ValidationRequestDetailPage)

**Location**: ValidationRequestDetailPage header

**When shown**: Validation status is `Validation Overdue`

**UI**: Similar to model page banner, prompts validators for delay explanation.

### 5. Overdue Commentary Modal (Reusable Component)

**Triggered by**: "Update Explanation" / "Provide Explanation" buttons anywhere

**Form fields**:
- Reason for delay (textarea, required)
- Target date (date picker, required)
  - Label changes based on context: "Target Submission Date" vs "Target Completion Date"

### 6. Overdue Revalidation Report Page

**Location**: Reports gallery → "Overdue Revalidation Report"

**Features**:
- Filterable by overdue type, risk tier, comment status
- Sortable columns
- CSV export with **Comment column**
- Summary statistics cards

---

## Implementation Phases

### Phase 1: Data Model & Core API (Backend)
- [ ] Create Alembic migration for `overdue_revalidation_comments` table
- [ ] Create SQLAlchemy model `OverdueRevalidationComment`
- [ ] Create Pydantic schemas for request/response
- [ ] Implement `GET /validation-workflow/requests/{id}/overdue-commentary`
- [ ] Implement `POST /validation-workflow/requests/{id}/overdue-commentary`
- [ ] Implement `GET /models/{id}/overdue-commentary` (convenience endpoint)
- [ ] Add permission checks (owner/developer for pre-submission, validator for in-progress)
- [ ] Implement comment staleness logic (45 days, target passed)
- [ ] Write unit tests

### Phase 2: Enhance Existing Dashboard Endpoints
- [ ] Enhance `GET /validation-workflow/dashboard/overdue-submissions` with commentary fields
- [ ] Enhance `GET /validation-workflow/dashboard/overdue-validations` with commentary fields
- [ ] Implement `GET /validation-workflow/dashboard/my-overdue-items` (user-specific)
- [ ] Write unit tests

### Phase 3: Frontend - Alerts & Modal
- [ ] Create `OverdueAlertBanner` component (reusable)
- [ ] Create `OverdueCommentaryModal` component (reusable)
- [ ] Integrate alert into `ModelDetailsPage`
- [ ] Integrate alert into `ValidationRequestDetailPage`
- [ ] Handle API calls for submitting commentary

### Phase 4: Frontend - Dashboard Enhancement
- [ ] Enhance existing AdminDashboard overdue widgets with commentary status
- [ ] Create `MyOverdueItemsPage` for non-admin users
- [ ] Add link to navigation sidebar

### Phase 5: Overdue Revalidation Report
- [ ] Implement `GET /reports/overdue-revalidations` endpoint
- [ ] Add report to Reports gallery metadata
- [ ] Create `OverdueRevalidationReportPage`
- [ ] Implement filters and CSV export (with Comment column)

### Phase 6: Testing & Documentation
- [ ] Backend unit tests (comprehensive)
- [ ] Frontend component tests
- [ ] End-to-end workflow testing
- [ ] Update ARCHITECTURE.md
- [ ] Update REGRESSION_TESTS.md

---

## Edge Cases & Business Rules

1. **Model with no ValidationPolicy**: Cannot compute due dates; show "No Policy Configured" status; no commentary required

2. **Model never validated**: Status is "Never Validated"; may or may not need commentary depending on whether it's a new model vs delinquent

3. **Multiple models on one ValidationRequest**: Each model tracks its own commentary separately (pre-submission), but validation commentary is per-request

4. **Validator leaves company**: Any assigned validator can update; if all validators removed, Admin can update

5. **Target date set in past**: Allow with warning; useful for documenting historical delays

6. **Rapid updates**: Each update creates new comment row; previous marked `is_current=FALSE`

7. **Comment visibility**: All users can view comments; only responsible parties can create/update

---

## Computed Completion Date Logic

```python
def get_computed_completion_date(
    model: Model,
    validation_request: Optional[ValidationRequest],
    overdue_comment: Optional[OverdueRevalidationComment],
    policy: ValidationPolicy
) -> Optional[date]:
    """
    For the Overdue Revalidation Report.
    """
    if not overdue_comment:
        return None

    if validation_request and validation_request.submission_received_date:
        # Post-submission: validator's target is the completion date
        return overdue_comment.target_date
    else:
        # Pre-submission: target submission + lead time
        return overdue_comment.target_date + timedelta(days=policy.model_change_lead_time_days)
```

---

## Questions Resolved

| Question | Answer |
|----------|--------|
| What counts as "submitted"? | `submission_received_date` is set (moves to In Progress) |
| How to calculate expected completion? | Pre: target_submission + lead_time. Post: validator's target directly |
| Multi-validator comments? | One shared comment per request; any validator can update |
| Enforcement level? | Soft - alerts only, no blocking |
| Which lead time field? | `model_change_lead_time_days` from ValidationPolicy |
| Comment visibility? | Everyone can view |
