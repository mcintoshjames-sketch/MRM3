# Model Exceptions Reporting & Metrics - Implementation Plan

## Overview

Implement a comprehensive model exceptions tracking system with three exception types:
1. **Unmitigated Performance Problem** - RED monitoring results persisting or lacking linked recommendations
2. **Model Used Outside Intended Purpose** - ATT_Q10_USE_RESTRICTIONS answered "No"
3. **Model In Use Prior to Full Validation** - Deployment confirmed before validation approval

## Exception Definitions & Detection Logic

### Type 1: Unmitigated Performance Problem
**Trigger (Union of B and C):**
- RED monitoring result persists across consecutive monitoring cycles, OR
- RED monitoring result exists without a linked recommendation

**Detection:**
- Query `MonitoringResult` where `calculated_outcome == "RED"`
- Check if same metric on same model had RED in previous cycle (persistence)
- Check if no `Recommendation` exists with `monitoring_cycle_id` pointing to that cycle

### Type 2: Model Used Outside Intended Purpose
**Trigger:** ATT_Q10_USE_RESTRICTIONS attestation question answered "No"

**Detection:**
- Query `AttestationResponse` where `question_id` matches ATT_Q10_USE_RESTRICTIONS and `answer == False`
- Join to `AttestationRecord` → `Model`

**Protection:** Mark ATT_Q10_USE_RESTRICTIONS as `is_system_protected = True` (new field)

### Type 3: Model In Use Prior to Full Validation
**Trigger:** Model version deployed before validation approved

**Detection:**
- Query `VersionDeploymentTask` where `deployed_before_validation_approved == True` AND `status == "CONFIRMED"`
- Field already exists at [version_deployment_task.py:59-69](api/app/models/version_deployment_task.py#L59-L69)

## Exception Lifecycle

```
OPEN → ACKNOWLEDGED → CLOSED
```

**Status Definitions:**
- **OPEN**: Exception detected, awaiting acknowledgment
- **ACKNOWLEDGED**: Admin has acknowledged the exception exists
- **CLOSED**: Exception resolved (manually or automatically)

**Closure Requirements (Admin only):**
- Free-text `closure_narrative` (required, min 10 chars)
- `closure_reason_id` from taxonomy (required)
- Seeded values: "No longer an exception", "Exception overridden", "Other"

## Auto-Close Logic

Exceptions can be closed automatically when their underlying condition is resolved, OR manually by an Admin at any time.

### Type 1: Unmitigated Performance Problem
**Auto-close trigger:** The metric/model combination returns from RED to GREEN in a subsequent monitoring cycle
- Detection: When a MonitoringResult is recorded, check if any open Type 1 exceptions exist for that model/metric
- If the new result is GREEN (or YELLOW), auto-close the exception with:
  - `closure_narrative`: "Auto-closed: Metric returned to acceptable range"
  - `closure_reason_id`: Look up taxonomy_value_id for code "NO_LONGER_EXCEPTION"

### Type 2: Model Used Outside Intended Purpose
**No auto-close** - Must be manually closed by Admin
- Rationale: This requires human judgment to confirm the issue has been addressed

### Type 3: Model In Use Prior to Full Validation
**Auto-close trigger:** A FULL validation request (not interim) is subsequently approved
- Detection: When a ValidationRequest transitions to APPROVED status:
  - Check `validation_type` is NOT "Interim" (must be Initial, Comprehensive, or Targeted Review)
  - Check if model has open Type 3 exceptions
  - Only auto-close if validation is a full validation type
- Auto-close with:
  - `closure_narrative`: "Auto-closed: Full validation approved on [date]"
  - `closure_reason_id`: Look up taxonomy_value_id for code "NO_LONGER_EXCEPTION"
- **Important**: Interim validations do NOT resolve this exception - the model must complete full validation

### Manual Closure
Admin can close ANY exception at any time using the standard closure UI:
- Required: `closure_narrative` (min 10 chars)
- Required: `closure_reason_id` from taxonomy

## Database Schema

### New Table: `model_exceptions`

```python
class ModelException(Base):
    __tablename__ = "model_exceptions"

    exception_id: int  # PK
    exception_code: str  # EXC-YYYY-NNNNN, unique
    model_id: int  # FK to models
    exception_type: str  # UNMITIGATED_PERFORMANCE | OUTSIDE_INTENDED_PURPOSE | USE_PRIOR_TO_VALIDATION

    # Source tracking (one set per exception type)
    monitoring_result_id: Optional[int]  # FK, unique partial constraint
    attestation_response_id: Optional[int]  # FK, unique partial constraint
    deployment_task_id: Optional[int]  # FK, unique partial constraint

    # Status & lifecycle
    status: str  # OPEN | ACKNOWLEDGED | CLOSED
    description: str  # Auto-generated from exception type
    detected_at: datetime
    auto_closed: bool = False  # True if closed by system, False if closed by Admin

    # Acknowledgment
    acknowledged_by_id: Optional[int]
    acknowledged_at: Optional[datetime]
    acknowledgment_notes: Optional[str]

    # Closure
    closed_at: Optional[datetime]
    closed_by_id: Optional[int]  # NULL for auto-closed exceptions
    closure_narrative: Optional[str]  # Required when closing
    closure_reason_id: Optional[int]  # FK to taxonomy_values, required when closing
```

### New Table: `model_exception_status_history`

```python
class ModelExceptionStatusHistory(Base):
    history_id: int
    exception_id: int  # FK
    old_status: Optional[str]
    new_status: str
    changed_by_id: int
    changed_at: datetime
    notes: Optional[str]
```

### Schema Update: `taxonomy_values`

Add column: `is_system_protected: bool = False`

## Files to Create

| File | Purpose |
|------|---------|
| `api/app/models/model_exception.py` | ModelException and ModelExceptionStatusHistory models |
| `api/app/core/exception_detection.py` | Detection functions for all three exception types |
| `api/app/api/exceptions.py` | API router with CRUD and status transitions |
| `api/app/schemas/model_exception.py` | Request/response schemas |
| `api/alembic/versions/xxx_add_model_exceptions.py` | Migration |
| `web/src/components/ModelExceptionsTab.tsx` | Model detail page exceptions tab |
| `web/src/pages/ExceptionsReportPage.tsx` | Exceptions report page |
| `web/src/api/exceptions.ts` | Frontend API client |

## Files to Modify

| File | Changes |
|------|---------|
| `api/app/models/__init__.py` | Export new models |
| `api/app/models/taxonomy.py` | Add `is_system_protected` field |
| `api/app/main.py` | Register exceptions router |
| `api/app/seed.py` | Add Exception Closure Reason taxonomy, mark ATT_Q10 as protected |
| `api/app/api/models.py` | Add `GET /models/{id}/exceptions` endpoint |
| `api/app/schemas/model.py` | Add `open_exception_count` to ModelResponse |
| `api/app/api/kpi_report.py` | Add "% Models with Open Exceptions" KPI |
| `api/app/api/my_portfolio.py` | Add `open_exceptions` section to portfolio report |
| `api/app/api/monitoring.py` | Trigger Type 1 exception detection on cycle approval; auto-close on GREEN results |
| `api/app/api/attestations.py` | Trigger Type 2 exception detection on attestation submit |
| `api/app/api/deployment_tasks.py` | Trigger Type 3 exception detection on deployment confirm |
| `api/app/api/validation_workflow.py` | Auto-close Type 3 exceptions on validation approval |
| `api/app/core/activity_timeline.py` | Add exception events to activity timeline |
| `api/app/api/dashboard.py` | Add exception events to news feed |
| `web/src/pages/ModelDetailsPage.tsx` | Add Exceptions tab + header badge |
| `web/src/pages/ReportsPage.tsx` | Add Exceptions Report to gallery |
| `web/src/App.tsx` | Add route for ExceptionsReportPage |
| `web/src/components/Layout.tsx` | Add exception badge count to sidebar (optional) |

## API Endpoints

```
GET    /exceptions/                           - List exceptions (filters: model_id, type, status)
GET    /exceptions/{id}                       - Get exception details
POST   /exceptions/{id}/acknowledge           - Acknowledge exception (Admin)
POST   /exceptions/{id}/close                 - Close with narrative (Admin)
POST   /exceptions/detect/{model_id}          - Trigger detection for model (Admin)
POST   /exceptions/detect-all                 - Batch detection (Admin)
GET    /models/{model_id}/exceptions          - Get model's exceptions
```

## Seed Data

### Exception Closure Reason Taxonomy
```python
{
    "name": "Exception Closure Reason",
    "is_system": True,
    "values": [
        {"code": "NO_LONGER_EXCEPTION", "label": "No longer an exception", "sort_order": 1},
        {"code": "EXCEPTION_OVERRIDDEN", "label": "Exception overridden", "sort_order": 2},
        {"code": "OTHER", "label": "Other", "sort_order": 3}
    ]
}
```

### Update ATT_Q10_USE_RESTRICTIONS
Set `is_system_protected = True` to prevent deletion/deactivation.

## KPI Integration

Add new metric to [kpi_report.py](api/app/api/kpi_report.py):

```python
"4.28": {
    "name": "% of Models with Open Exceptions",
    "definition": "Proportion of active models with at least one open exception",
    "calculation": "(# models with open exceptions) / (Total active models) x 100%",
    "category": "Key Risk Indicators",
    "type": "ratio",
    "is_kri": True
}
```

## Dashboard & Task List Integration

### User Dashboard Task List
Add exception items to existing task lists for visibility:

**For Model Owners:**
- Show open exceptions on models they own
- Include in "My Portfolio" report: `GET /reports/my-portfolio` should include `open_exceptions` section
- Exception badge count in sidebar navigation

**For Admins:**
- "Open Exceptions Requiring Attention" section on Admin dashboard
- Filterable by type and age
- Link to Exceptions Report for full drill-down

### Model Details Page
- **Exceptions Tab**: New tab showing all exceptions for the model
- **Header Badge**: Red badge showing count of open exceptions
- **Quick Actions**: Acknowledge, Close (Admin only)

### Activity Feed Integration
Exception status changes should appear in:
- Model's activity timeline (`GET /models/{id}/activity-timeline`)
- Dashboard news feed (`GET /dashboard/news-feed`)

## Workflow Integration Points

### Monitoring Cycle Workflow
**Exception Creation (on cycle approval with RED results):**
- Trigger exception detection for Type 1 (unmitigated performance)
- Auto-create exceptions for RED results without linked recommendations
- Check for persistence against previous cycle

**Auto-Close Detection (on new monitoring results):**
- When new MonitoringResult is recorded with GREEN/YELLOW outcome
- Check for open Type 1 exceptions on same model/metric combination
- Auto-close any matching exceptions

### Attestation Workflow
When attestation is submitted:
- Check ATT_Q10_USE_RESTRICTIONS answer
- If answer is "No", auto-create Type 2 exception for that model

### Deployment Task Workflow
When a VersionDeploymentTask is confirmed:
- If `deployed_before_validation_approved == True`, auto-create Type 3 exception
- Link exception to the deployment task for traceability

### Validation Workflow
**Surface Exceptions:**
- Display warning if model has open Type 3 exceptions during submission
- Include open exception count in validation request detail view

**Auto-Close Detection (on FULL validation approval only):**
- When ValidationRequest transitions to APPROVED status
- Check `validation_type` is NOT "Interim" (must be Initial, Comprehensive, or Targeted Review)
- If full validation: Check for open Type 3 exceptions on the same model and auto-close
- If interim validation: Do NOT auto-close - exception remains open

## UX Improvements

### Unified "Attention Required" Dashboard Section
Instead of separate sections for different alert types, consolidate into a single "Items Requiring Attention" section showing:
- Open exceptions (grouped by type)
- RED monitoring results
- Overdue attestations
- Other actionable items

This reduces cognitive load and provides a single place to see all items needing action.

### Model Details "Flags" Badge (Future Enhancement)
In addition to the Exceptions Tab, a future iteration could add:
- A flags/warning badge in the model header showing count of open issues
- Clicking the badge expands an inline panel showing exceptions
- Full history available via "View All" link to the Exceptions tab

Note: Phase 4 implements the Exceptions Tab as the primary UI. The inline badge is optional future work.

### Inline Resolution Actions
For exceptions that can be closed with a single action:
- Show "Close" button directly in the exceptions list
- Modal opens with required narrative and reason fields
- Confirm closes exception without navigating away

### Exception Source Links
Each exception should provide direct navigation to its source:
- Type 1: Link to the MonitoringResult/Cycle that triggered it
- Type 2: Link to the Attestation response
- Type 3: Link to the VersionDeploymentTask

## Implementation Phases

**Implementation Order Note**: Write tests alongside each phase (test-first where possible). The test file `api/tests/test_exceptions.py` should be created in Phase 1 and expanded throughout.

### Phase 1: Database & Core Models (Est: 3-4 hours)
1. Add `is_system_protected` to TaxonomyValue model
2. Create `api/app/models/model_exception.py`
3. Create Alembic migration
4. Update `api/app/models/__init__.py`

### Phase 2: Detection Service (Est: 4-5 hours)
1. Create `api/app/core/exception_detection.py`
2. Implement detection for Type 1 (unmitigated performance)
3. Implement detection for Type 2 (outside intended purpose)
4. Implement detection for Type 3 (use prior to validation)
5. Add exception code generator (EXC-YYYY-NNNNN)
6. Implement auto-close functions for Type 1 (on GREEN result) and Type 3 (on validation approval)

### Phase 3: API Endpoints (Est: 4-5 hours)
1. Create `api/app/schemas/model_exception.py`
2. Create `api/app/api/exceptions.py` with all endpoints
3. Add model exceptions endpoint to `api/app/api/models.py`
4. Register router in `api/app/main.py`
5. Update seed.py with Exception Closure Reason taxonomy

### Phase 4: Frontend - Model Details (Est: 4-5 hours)
1. Create `web/src/api/exceptions.ts`
2. Create `web/src/components/ModelExceptionsTab.tsx`
3. Add Exceptions tab to ModelDetailsPage
4. Add exception count badge

### Phase 5: Frontend - Reports & KPI (Est: 4-5 hours)
1. Create `web/src/pages/ExceptionsReportPage.tsx`
2. Add to ReportsPage.tsx gallery
3. Add route to App.tsx
4. Add KPI metric to kpi_report.py
5. Update KPIReportPage if needed

### Phase 6: Workflow Integration & Activity Feed (Est: 3-4 hours)
1. Add exception detection hooks to monitoring cycle approval (Type 1 creation)
2. Add auto-close hooks to monitoring results (Type 1 closes on GREEN)
3. Add exception detection hooks to attestation submission (Type 2 creation)
4. Add exception detection hooks to deployment task confirmation (Type 3 creation)
5. Add auto-close hooks to FULL validation approval only (Type 3 closes on APPROVED, skip for Interim)
6. Add exception events to activity timeline
7. Add exception events to news feed
8. Add open_exceptions section to My Portfolio report

### Phase 7: Testing (Write Early - Test as You Go)

**File**: `api/tests/test_exceptions.py`

Tests should be written BEFORE or alongside implementation to validate as we go.

#### Model & Schema Tests
```python
def test_create_exception_model():
    """ModelException can be created with required fields"""

def test_exception_code_format():
    """Exception codes follow EXC-YYYY-NNNNN format"""

def test_unique_constraint_monitoring_result():
    """Cannot create duplicate exceptions for same monitoring_result_id"""

def test_unique_constraint_attestation_response():
    """Cannot create duplicate exceptions for same attestation_response_id"""

def test_unique_constraint_deployment_task():
    """Cannot create duplicate exceptions for same deployment_task_id"""
```

#### Detection Logic Tests
```python
# Type 1: Unmitigated Performance
def test_detect_type1_red_without_recommendation():
    """Creates exception when RED result has no linked recommendation"""

def test_detect_type1_red_persists_across_cycles():
    """Creates exception when RED persists across consecutive cycles"""

def test_no_exception_when_red_has_recommendation():
    """No exception when RED result has a linked recommendation"""

def test_no_duplicate_type1_exception():
    """Does not create duplicate if exception already exists for same source"""

# Type 2: Outside Intended Purpose
def test_detect_type2_attestation_no():
    """Creates exception when ATT_Q10_USE_RESTRICTIONS answered No"""

def test_no_type2_when_attestation_yes():
    """No exception when ATT_Q10_USE_RESTRICTIONS answered Yes"""

# Type 3: Use Prior to Full Validation
def test_detect_type3_deployed_before_validation():
    """Creates exception when deployed_before_validation_approved=True"""

def test_no_type3_when_deployed_after_validation():
    """No exception when deployed_before_validation_approved=False"""
```

#### Auto-Close Tests
```python
# Type 1 Auto-Close
def test_autoclose_type1_on_green_result():
    """Type 1 exception auto-closes when metric returns to GREEN"""

def test_autoclose_type1_on_yellow_result():
    """Type 1 exception auto-closes when metric returns to YELLOW"""

def test_no_autoclose_type1_if_still_red():
    """Type 1 exception stays open if metric is still RED"""

# Type 3 Auto-Close (FULL validation only)
def test_autoclose_type3_on_full_validation_approved():
    """Type 3 exception auto-closes when FULL validation is approved"""

def test_no_autoclose_type3_on_interim_validation():
    """Type 3 exception stays OPEN when only interim validation is approved"""

def test_autoclose_type3_initial_validation():
    """Type 3 auto-closes on Initial validation type"""

def test_autoclose_type3_comprehensive_validation():
    """Type 3 auto-closes on Comprehensive validation type"""

def test_autoclose_type3_targeted_review():
    """Type 3 auto-closes on Targeted Review validation type"""

# Type 2 Manual Only
def test_no_autoclose_type2():
    """Type 2 exceptions are never auto-closed"""
```

#### API Endpoint Tests
```python
def test_list_exceptions():
    """GET /exceptions/ returns paginated list"""

def test_list_exceptions_filter_by_model():
    """GET /exceptions/?model_id=X filters correctly"""

def test_list_exceptions_filter_by_type():
    """GET /exceptions/?type=UNMITIGATED_PERFORMANCE filters correctly"""

def test_list_exceptions_filter_by_status():
    """GET /exceptions/?status=OPEN filters correctly"""

def test_get_exception_detail():
    """GET /exceptions/{id} returns full exception details"""

def test_acknowledge_exception_admin():
    """POST /exceptions/{id}/acknowledge works for Admin"""

def test_acknowledge_exception_non_admin_forbidden():
    """POST /exceptions/{id}/acknowledge returns 403 for non-Admin"""

def test_close_exception_with_narrative():
    """POST /exceptions/{id}/close works with valid narrative and reason"""

def test_close_exception_missing_narrative_fails():
    """POST /exceptions/{id}/close fails without narrative"""

def test_close_exception_short_narrative_fails():
    """POST /exceptions/{id}/close fails if narrative < 10 chars"""

def test_close_exception_missing_reason_fails():
    """POST /exceptions/{id}/close fails without closure_reason_id"""

def test_detect_for_model():
    """POST /exceptions/detect/{model_id} triggers detection"""

def test_detect_all():
    """POST /exceptions/detect-all triggers batch detection"""

def test_model_exceptions_endpoint():
    """GET /models/{id}/exceptions returns model's exceptions"""
```

#### Status History Tests
```python
def test_status_history_on_acknowledge():
    """Acknowledging creates status history record"""

def test_status_history_on_close():
    """Closing creates status history record"""

def test_status_history_on_autoclose():
    """Auto-closing creates status history record with system user"""
```

#### Integration Tests
```python
def test_exception_appears_in_activity_timeline():
    """Exception events appear in model activity timeline"""

def test_exception_appears_in_news_feed():
    """Exception events appear in dashboard news feed"""

def test_open_exception_count_in_model_response():
    """Model detail includes open_exception_count field"""

def test_kpi_models_with_exceptions():
    """KPI 4.28 correctly calculates % models with open exceptions"""
```

## Key Design Decisions

1. **Single Exception Per Source**: Unique partial constraints prevent duplicate exceptions per triggering entity
2. **Simplified Lifecycle**: Three states only (OPEN → ACKNOWLEDGED → CLOSED), removed REMEDIATION_IN_PROGRESS for simplicity
3. **Admin-Only Status Transitions**: All manual changes require Admin role
4. **Closure Requirements**: Both narrative and reason required (DB constraint enforced)
5. **Auto-Close Logic**: Type 1 closes when metric returns to GREEN; Type 3 closes when FULL validation approved (not interim); Type 2 is manual-only
6. **Auto-Detection**: Can be triggered manually per model, batch for all, or integrated into workflows
7. **Exception Codes**: Format `EXC-YYYY-NNNNN` generated automatically
8. **Source Traceability**: Each exception links to its source entity (MonitoringResult, AttestationResponse, or DeploymentTask)
