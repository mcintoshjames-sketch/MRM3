# Model Exceptions Remediation Plan

## Overview
This document addresses 5 issues found by auditor in the implementation of `ethereal-churning-raccoon.md` (Model Exceptions Tracking System).

**Date**: 2025-12-14
**Related Spec**: `ethereal-churning-raccoon.md`

---

## Issues Summary

| # | Issue | Severity | File(s) |
|---|-------|----------|---------|
| 1 | Type 1 persistent RED detection not called in routine workflow | Critical | `api/app/api/monitoring.py` |
| 2 | Type 1 "no recommendation" branch logic error | Critical | `api/app/core/exception_detection.py` |
| 3 | Missing `open_exception_count` in model response | Medium | `api/app/schemas/model.py`, `api/app/api/models.py`, `web/src/pages/ModelDetailsPage.tsx` |
| 4 | Model-level exceptions filtering broken | High | `api/app/api/exceptions.py` |
| 5 | Missing models endpoint for exception count | Low | `api/app/api/models.py` |

---

## Issue 1: Type 1 Persistent RED Detection Not Called in Routine Workflow

### Problem
The `detect_type1_persistent_red_for_model` function exists but is never called during routine monitoring cycle approval. Only `detect_type1_unmitigated_performance` is called at line 3924 in `monitoring.py`.

### Files to Modify
- `api/app/api/monitoring.py` (lines ~3920-3930)

### Changes
Add call to `detect_type1_persistent_red_for_model` in `_check_and_complete_cycle` function after the existing Type 1 detection:

```python
# Line ~3924 - AFTER existing call:
detect_type1_unmitigated_performance(db, model.model_id)
# ADD THIS:
detect_type1_persistent_red_for_model(db, model.model_id)
```

Also ensure import at top of file:
```python
from app.core.exception_detection import (
    detect_type1_unmitigated_performance,
    detect_type1_persistent_red_for_model,  # ADD
    detect_type3_use_prior_to_validation,
)
```

---

## Issue 2: Type 1 "No Recommendation" Branch Logic Error

### Problem
The recommendation existence check in `detect_type1_unmitigated_performance` (lines 199-204) queries for ANY recommendation for the model/cycle, ignoring:
1. Whether the recommendation is for the specific metric that has RED outcome
2. Whether the recommendation is in an actionable status (not CLOSED/CANCELLED)

### Files to Modify
- `api/app/core/exception_detection.py` (lines 199-220)

### Changes
Replace the recommendation query with metric-specific and status-filtered logic.

**Note (Jan 2026 addendum):** This section’s example status filter list is superseded by the
source-of-truth terminal status codes approach described in “Jan 2026 Addendum: Production Hardening”.

```python
# Current broken code (lines 199-204):
has_recommendation = db.query(exists().where(
    and_(
        Recommendation.model_id == result_model_id,
        Recommendation.monitoring_cycle_id == result.cycle_id
    )
)).scalar()

# Replace with:
has_active_recommendation = db.query(exists().where(
    and_(
        Recommendation.model_id == result_model_id,
        Recommendation.monitoring_cycle_id == result.cycle_id,
        Recommendation.plan_metric_id == result.plan_metric_id,  # Match specific metric
        Recommendation.status_id.in_(
            db.query(TaxonomyValue.value_id).filter(
                TaxonomyValue.taxonomy_id == db.query(Taxonomy.taxonomy_id).filter(
                    Taxonomy.name == "Recommendation Status"
                ).scalar_subquery(),
                TaxonomyValue.code.notin_(['CLOSED', 'CANCELLED', 'COMPLETED'])
            )
        )
    )
)).scalar()

if has_active_recommendation:
    continue  # Skip - active recommendation exists for this specific metric
```

Need to import `Taxonomy` and `TaxonomyValue` if not already imported.

---

## Issue 3: Missing `open_exception_count` in Model Response

### Problem
- `ModelDetailResponse` schema has no `open_exception_count` field
- UI has no badge on Exceptions tab showing count of open exceptions

### Files to Modify
1. `api/app/schemas/model.py` - Add field to schema
2. `api/app/api/models.py` - Compute count in GET endpoint
3. `web/src/pages/ModelDetailsPage.tsx` - Add badge to tab

### Changes

**A. Schema (`api/app/schemas/model.py`):**
Add to `ModelDetailResponse` class:
```python
open_exception_count: int = 0
```

**B. API (`api/app/api/models.py`):**
In `get_model` endpoint, compute and return count:
```python
from app.models import ModelException

# After fetching model, before returning:
open_exception_count = db.query(func.count(ModelException.exception_id)).filter(
    ModelException.model_id == model_id,
    ModelException.status == 'OPEN'
).scalar() or 0

# Include in response construction
```

**C. Frontend (`web/src/pages/ModelDetailsPage.tsx`):**
Add badge to Exceptions tab button:
```tsx
<button
    className={`px-4 py-2 font-medium ${activeTab === 'exceptions' ? '...' : '...'}`}
    onClick={() => setActiveTab('exceptions')}
>
    Exceptions
    {model.open_exception_count > 0 && (
        <span className="ml-2 px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-800">
            {model.open_exception_count}
        </span>
    )}
</button>
```

---

## Issue 4: Model-Level Exceptions Filtering Broken

### Problem
Frontend sends `status` query parameter but backend only accepts `include_closed` boolean. The filtering silently fails.

### Files to Modify
1. `api/app/api/exceptions.py` - Add `status` parameter

### Changes

**Backend (`api/app/api/exceptions.py`):**
Update `get_model_exceptions` endpoint (lines ~675-705):

```python
@router.get("/model/{model_id}", response_model=List[ModelExceptionListItem])
def get_model_exceptions(
    model_id: int,
    status: Optional[str] = Query(None, description="Filter by status: OPEN, ACKNOWLEDGED, CLOSED"),
    include_closed: bool = Query(False, description="Include closed exceptions (deprecated, use status)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get exceptions for a specific model."""
    query = db.query(ModelException).filter(ModelException.model_id == model_id)

    # New status filter takes precedence
    if status:
        query = query.filter(ModelException.status == status)
    elif not include_closed:
        # Legacy behavior for backwards compatibility
        query = query.filter(ModelException.status != 'CLOSED')

    return query.order_by(ModelException.detected_at.desc()).all()
```

Frontend already sends `status` parameter correctly - no changes needed.

---

## Issue 5: Missing Models Endpoint for Exception Count

### Problem
Original plan specified `GET /models/{id}/exceptions` endpoint in models router but it was never implemented.

### Files to Modify
- `api/app/api/models.py` - Add endpoint

### Changes
Add new endpoint to models router:

```python
from app.models import ModelException

@router.get("/{model_id}/exceptions", response_model=List[ModelExceptionListItem])
def get_model_exceptions(
    model_id: int,
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get exceptions for a model (convenience endpoint in models router)."""
    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    query = db.query(ModelException).filter(ModelException.model_id == model_id)

    if status:
        query = query.filter(ModelException.status == status)

    return query.order_by(ModelException.detected_at.desc()).all()


@router.get("/{model_id}/exceptions/count")
def get_model_exception_count(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get exception counts for a model."""
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    counts = db.query(
        ModelException.status,
        func.count(ModelException.exception_id)
    ).filter(
        ModelException.model_id == model_id
    ).group_by(ModelException.status).all()

    return {
        "model_id": model_id,
        "open": next((c for s, c in counts if s == 'OPEN'), 0),
        "acknowledged": next((c for s, c in counts if s == 'ACKNOWLEDGED'), 0),
        "closed": next((c for s, c in counts if s == 'CLOSED'), 0),
    }
```

---

## Implementation Order

1. **Issue 2** (Critical) - Fix recommendation query logic first (data correctness)
2. **Issue 1** (Critical) - Add persistent RED detection call (feature completeness)
3. **Issue 4** (High) - Fix status filtering (API contract)
4. **Issue 3** (Medium) - Add open_exception_count to model (UX)
5. **Issue 5** (Low) - Add convenience endpoints (API completeness)

---

## Jan 2026 Addendum: Production Hardening (Final Decisions)

This addendum captures follow-up risks discovered during an adversarial review and defines the final
remediation approach for exception detection correctness and operational safety.

**Date**: 2026-01-03

### Decisions

1. **Terminal recommendation statuses source-of-truth**
     - Use `TERMINAL_RECOMMENDATION_STATUS_CODES` (currently defined in `api/app/api/monitoring.py`) as the
         canonical definition of “terminal” recommendation statuses.
     - Avoid importing API-layer modules from core detection logic.
     - **Plan**: move `TERMINAL_RECOMMENDATION_STATUS_CODES` into a shared core module (e.g.
         `api/app/core/recommendation_status.py`) and import it from both:
         - `api/app/api/monitoring.py`
         - `api/app/core/exception_detection.py`

2. **Exception code generation strategy**
     - Use the “robust enough” approach: **unique constraint + bounded retry** on collision.
     - Do **not** introduce a counter table/sequence as part of this remediation (see Downsides section below).

### Issue 6: Recommendation Status Taxonomy Alignment (Type 1 correctness)

#### Problem
Type 1 detection currently treats “active recommendation statuses” as anything not in
`['CLOSED', 'CANCELLED', 'COMPLETED']`. However, the seeded taxonomy uses `REC_*` codes (e.g., `REC_CLOSED`,
`REC_DROPPED`). This mismatch can cause **false negatives** (a terminal recommendation suppresses an exception).

#### Files to Modify
- `api/app/core/exception_detection.py`
- `api/app/api/monitoring.py` (or shared module if constant moved)

#### Changes
- Replace the `TaxonomyValue.code.notin_([...])` filter with a filter that excludes the terminal codes from
    `TERMINAL_RECOMMENDATION_STATUS_CODES`.
- Ensure both Type 1 paths are updated:
    - `detect_type1_unmitigated_performance`
    - `ensure_type1_exception_for_result`

#### Acceptance Criteria
- A recommendation with terminal status (`REC_CLOSED` or `REC_DROPPED`) does **not** count as active.
- A RED result with only terminal recommendations for the same metric results in a Type 1 exception.

### Issue 7: Concurrency-Safe `exception_code` Generation (robust enough)

#### Problem
`generate_exception_code` uses `max(exception_code) + 1`. Under concurrent creation (e.g., two admin users
triggering detection in parallel), this can generate duplicate codes and fail on the unique index.

#### Files to Modify
- `api/app/core/exception_detection.py`

#### Changes
- Keep code format `EXC-YYYY-NNNNN`.
- On insert/flush of a new exception, if a unique-constraint collision occurs on `exception_code`, retry:
    - re-query max code for the year
    - generate next code
    - re-attempt flush
    - bounded attempts (e.g., 5) with a clear error if exhausted

#### Acceptance Criteria
- Concurrent exception creation never fails due to `exception_code` collisions (within reasonable concurrency).
- On collision, the system retries and succeeds without operator intervention.

### Issue 8: `/exceptions/detect-all` Guardrails

#### Problem
`POST /exceptions/detect-all` runs detection for every active model in a single request. In larger inventories,
this risks long transactions/timeouts and is difficult to operate safely.

#### Files to Modify
- `api/app/api/exceptions.py`

#### Changes (minimal, server-side)
- Add conservative server-side limits/guardrails (exact thresholds to be agreed):
    - cap number of models scanned per request, or require an explicit `limit` parameter
    - ensure audit logging always records `models_scanned` and `exceptions_created`
- Ensure partial progress is possible (e.g., commit per model or per chunk) to avoid one failure losing all work.

#### Acceptance Criteria
- Batch detection does not routinely hit request timeouts in UAT-scale environments.
- Audit logs clearly reflect scope and outcome of each batch run.

### Issue 9: Closure Taxonomy Hard Dependency

#### Problem
Auto-close relies on closure-reason taxonomy values being present. If seeding is incomplete, auto-close silently
fails (exception remains open) and only a warning is logged.

#### Files to Modify
- `api/app/core/exception_detection.py`

#### Changes
- Add a lightweight preflight check for required taxonomy codes (closure reasons) in contexts where auto-close
    is expected to occur (startup or first use).
- Ensure operational visibility: warning should be elevated to a clearly detectable signal (e.g., structured log
    field or explicit counter).

#### Acceptance Criteria
- Incomplete taxonomy state is detectable during deployment/UAT (not discovered weeks later via open exceptions).

### Issue 10: Targeted Regression Tests (must-have)

#### Backend Tests (`api/tests/test_exceptions.py`)

Add focused tests that fail under the current mismatch and pass after remediation:

1. **Type 1: terminal recommendation does not suppress exception**
     - Create an APPROVED cycle with a RED result for metric X.
     - Create a recommendation for the same model/cycle/metric with status `REC_CLOSED`.
     - Assert: Type 1 exception is created.

2. **Type 1: active recommendation does suppress exception**
     - Same setup but recommendation status `REC_OPEN` (or another non-terminal status).
     - Assert: no exception is created.

3. **Exception code collision retry**
     - Simulate two creations attempting the same `exception_code` (can be done by forcing generator output or
         monkeypatching `generate_exception_code`).
     - Assert: second creation retries and succeeds with a new code.

### Downsides of the “more robust” DB-managed counter/sequence (documented)

We are intentionally not choosing this option in this remediation due to:
- portability and migration complexity
- hot-row contention under batch detection
- year rollover and test isolation complexity


## Testing Plan

### Backend Tests (`api/tests/test_exceptions.py`)

Add tests for:
1. Type 1 persistent RED detection triggers during cycle approval
2. Recommendation query filters by metric and status
3. Status parameter filtering on model exceptions endpoint
4. New models router endpoints

---

## Manual Verification with MCP Puppeteer

After implementation, use MCP Puppeteer to verify fixes visually:

### Pre-requisites
```bash
docker compose up --build
```

### Test 1: Exception Badge on Model Details (Issue 3)

```javascript
// Step 1: Login
puppeteer_navigate({ url: "http://localhost:5174/login", launchOptions: { headless: true } })
puppeteer_fill({ selector: "input[name='email']", value: "admin@example.com" })
puppeteer_fill({ selector: "input[name='password']", value: "admin123" })
puppeteer_click({ selector: "button[type='submit']" })

// Step 2: Navigate to a model with open exceptions
puppeteer_navigate({ url: "http://localhost:5174/models/1" })
puppeteer_screenshot({ name: "model-detail-exceptions-badge" })

// Verify: Exceptions tab should show red badge with count if open exceptions exist
```

### Test 2: Exception Status Filtering (Issue 4)

```javascript
// Step 1: Navigate to model exceptions tab
puppeteer_navigate({ url: "http://localhost:5174/models/1" })
puppeteer_click({ selector: "button:contains('Exceptions')" })  // Or appropriate selector

// Step 2: Test status filter dropdown
puppeteer_select({ selector: "select[name='status']", value: "OPEN" })
puppeteer_screenshot({ name: "exceptions-filter-open" })

puppeteer_select({ selector: "select[name='status']", value: "ACKNOWLEDGED" })
puppeteer_screenshot({ name: "exceptions-filter-acknowledged" })

puppeteer_select({ selector: "select[name='status']", value: "CLOSED" })
puppeteer_screenshot({ name: "exceptions-filter-closed" })

// Verify: Each filter should show only matching exceptions
```

### Test 3: Type 1 Detection via Admin Detect (Issues 1 & 2)

```javascript
// Step 1: Navigate to Exceptions Report page
puppeteer_navigate({ url: "http://localhost:5174/reports/exceptions" })
puppeteer_screenshot({ name: "exceptions-report-before" })

// Step 2: Click "Detect All" button (admin only)
puppeteer_click({ selector: "button:contains('Detect All')" })

// Step 3: Wait and screenshot results
puppeteer_screenshot({ name: "exceptions-report-after-detect" })

// Verify: New exceptions should be created for:
// - Models with RED results and no active recommendation for that metric
// - Models with persistent RED across consecutive cycles
```

### Test 4: API Contract Verification

```javascript
// Use browser console to verify API responses
puppeteer_evaluate({ script: `
    // Test status filter works
    fetch('/api/exceptions/model/1?status=OPEN')
        .then(r => r.json())
        .then(data => console.log('OPEN exceptions:', data.length))

    // Test new count endpoint
    fetch('/api/models/1/exceptions/count')
        .then(r => r.json())
        .then(data => console.log('Exception counts:', data))
` })
puppeteer_screenshot({ name: "api-verification" })
```

### Test 5: End-to-End Workflow

```javascript
// Step 1: Create a monitoring cycle with RED result (via Monitoring page)
puppeteer_navigate({ url: "http://localhost:5174/monitoring" })
// ... navigate to a plan and cycle, record RED result

// Step 2: Approve the cycle
// ... click approve button

// Step 3: Check if exception was created
puppeteer_navigate({ url: "http://localhost:5174/models/[model_id]" })
puppeteer_click({ selector: "button:contains('Exceptions')" })
puppeteer_screenshot({ name: "e2e-exception-created" })

// Verify: UNMITIGATED_PERFORMANCE exception should exist if no active recommendation
```

---

## Verification Checklist

**Note (Jan 2026 addendum):** Re-run this checklist after applying the “Production Hardening” changes
(Issues 6–10), since the definition of “terminal recommendation status” is being standardized.

- [x] **Issue 1**: Approve cycle with 2+ consecutive RED results → Persistent RED exception created
  - ✅ Code verified: `detect_type1_persistent_red_for_model` called at line 3963 in monitoring.py
- [x] **Issue 2**: RED result WITH active recommendation for same metric → No exception
  - ✅ Code verified: Query filters by `plan_metric_id` at line 231 in exception_detection.py
- [x] **Issue 2**: RED result WITH recommendation for DIFFERENT metric → Exception created
  - ✅ Code verified: Only same-metric recommendations prevent exception creation
- [x] **Issue 2**: RED result WITH terminal recommendation → Exception created
    - ✅ Code verified: Terminal statuses are defined by `TERMINAL_RECOMMENDATION_STATUS_CODES` (e.g., `REC_CLOSED`, `REC_DROPPED`)
- [x] **Issue 3**: Model detail page shows exception count badge on tab
  - ✅ UI verified: "Exceptions" tab shows red badge with count "3" for model 1
  - ✅ API verified: GET /models/1 returns `open_exception_count: 3`
- [x] **Issue 4**: Status dropdown filter works correctly in UI
  - ✅ API verified: GET /exceptions/model/1?status=OPEN returns 3, status=CLOSED returns 0
- [x] **Issue 5**: `/models/{id}/exceptions/count` returns correct counts
  - ✅ API verified: Returns `{model_id: 1, open: 3, acknowledged: 0, closed: 0}`

---

## UAT Test Results

**Date**: 2025-12-15
**Tester**: Claude Code (UAT Phase 5)

### Critical Bug Fix: SQLAlchemy Lazy Loading Error

**Problem Identified**: The `approve_cycle` function in `monitoring.py` crashed with a SQLAlchemy lazy loading error when trying to access `cycle.plan.models` in `_check_and_complete_cycle`. The error occurred because the nested relationship was not eagerly loaded.

**Fix Applied** (lines ~3950-3958 in `monitoring.py`):
```python
# Before (broken):
cycle = db.query(MonitoringCycle).options(
    joinedload(MonitoringCycle.plan)
).get(cycle_id)

# After (fixed):
cycle = db.query(MonitoringCycle).options(
    joinedload(MonitoringCycle.plan).joinedload(MonitoringPlan.models)
).get(cycle_id)
```

### Test Execution

| Test | Description | Result | Notes |
|------|-------------|--------|-------|
| **TC-1** | Approve cycle with RED result via API | ✅ PASS | Cycle 2 (Plan 1) approved without errors |
| **TC-2** | Cycle status transition | ✅ PASS | PENDING_APPROVAL → APPROVED |
| **TC-3** | Nested relationship access | ✅ PASS | No crash on `cycle.plan.models` access |
| **TC-4** | Exception duplicate prevention | ✅ PASS | EXC-2025-00011 already existed for Result 431/Cycle 2 - no duplicate created |
| **TC-5** | Exception detection trigger | ✅ PASS | Type 1 detection ran without errors |

### Test Details

**Test Case TC-1: Cycle Approval via API**
```bash
# Approval request
POST /monitoring/cycles/2/approvals/70/approve
{
    "comments": "Approved for UAT testing",
    "approval_evidence": "UAT Phase 5 test"
}

# Response: HTTP 200
# approval_status: "Approved"
# Cycle status: APPROVED
```

**Test Case TC-4: Pre-existing Exception**
```json
{
    "exception_id": 11,
    "exception_code": "EXC-2025-00011",
    "model_id": 1,
    "exception_type": "UNMITIGATED_PERFORMANCE",
    "status": "OPEN",
    "description": "RED monitoring result detected for metric without a linked recommendation. Monitoring result ID: 431, Cycle ID: 2"
}
```

### Identified UI Issues (Non-blocking)

1. **Approvals Tab Display Bug**: ~~The "Approvals" tab in monitoring cycle detail showed "No approvals configured for this cycle" despite 1 pending approval existing (visible in tab badge count).~~
   - **Status**: ✅ **FIXED AND VERIFIED** (2025-12-15)
   - **Root Cause**: Pydantic v2 forward reference resolution issue - `MonitoringCycleApprovalResponse` schema wasn't calling `model_rebuild()` to resolve nested `RegionRef` and `UserRef` types
   - **Fix Applied**: Added `MonitoringCycleApprovalResponse.model_rebuild()` in `api/app/api/monitoring.py` after schema imports
   - **Verification**: Cycle 7 tested with 3 pending approvals:
     - Asia Pacific Approval - Pending ✓
     - United Kingdom Approval - Pending ✓
     - Global Approval - Pending ✓
   - Progress indicator shows "0 / 3 Complete" with action buttons (Approve, Reject, Void) functional
   - Screenshot evidence: `screenshots/approvals_tab_fix_verified.png`

### Conclusion

The nested `joinedload` fix resolves the critical SQLAlchemy lazy loading error. The automatic exception detection system now functions correctly during cycle approval workflow:

- ✅ Cycles can be approved without crashes
- ✅ Status transitions complete successfully
- ✅ Exception detection runs without errors
- ✅ Duplicate prevention works correctly
- ✅ Approvals tab displays correctly with region names and action buttons (Pydantic v2 fix)

**Status**: **PASSED** - All fixes verified and working as expected.

---

## Summary of Fixes Applied

| Issue | Fix | Status |
|-------|-----|--------|
| SQLAlchemy lazy loading crash | Added nested `joinedload` for `MonitoringPlan.models` | ✅ Verified |
| Approvals Tab "No approvals configured" | Added `MonitoringCycleApprovalResponse.model_rebuild()` | ✅ Verified |
| TypeScript optional chaining | Updated `CycleApprovalPanel.tsx` with `RegionRef`/`UserRef` interfaces | ✅ Verified |
