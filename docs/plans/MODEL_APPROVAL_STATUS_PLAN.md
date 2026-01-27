# Model Approval Status Feature Plan

## Overview

Add a **Model Approval Status** concept that represents the model's current state based on its validation history and approval completeness. This is distinct from:
- **Model Status** (`Model.status`): Lifecycle state (Active, In Development, Retired)
- **Validation Request Status** (`ValidationRequest.current_status`): Workflow state of individual validation projects (Intake, Assigned, In Progress, etc.)

The Model Approval Status answers: **"Is this model currently approved for use based on its validation history?"**

---

## Status Definitions

| Status | Code | Description |
|--------|------|-------------|
| **Never Validated** | `NEVER_VALIDATED` | No validation request has ever been approved for this model |
| **Approved** | `APPROVED` | Most recent validation is APPROVED with ALL required approvals complete (traditional + conditional). Model remains APPROVED even during the revalidation window until it expires. |
| **Interim Approved** | `INTERIM_APPROVED` | Most recent completed validation was of INTERIM type (temporary/expedited approval) with all approvals complete |
| **Validation In Progress** | `VALIDATION_IN_PROGRESS` | Model is **overdue** (past revalidation deadline) BUT has an active validation request in planning stage or later (not INTAKE, CANCELLED) |
| **Expired** | `EXPIRED` | Model is **overdue** (past revalidation deadline) AND either has no active validation OR validation is still in INTAKE stage |

### Key Concept: Revalidation Window vs Expiration

```
Timeline:
├── Last Validation Approved ──────────────────────────────────────────────────►
│
├── [APPROVED status continues] ──────────────────────────────────────────────►
│                                                                              │
│   ◄─────────────── Revalidation Window (frequency_months) ─────────────────► │
│                                                                              │
├── Submission Due Date ───────────────────────────────────────────────────────►
│                                                                              │
│   ◄─────────────── Grace Period (grace_period_months) ─────────────────────► │
│                                                                              │
├── Grace Period End ──────────────────────────────────────────────────────────►
│                                                                              │
│   ◄─────────────── Lead Time (model_change_lead_time_days) ────────────────► │
│                                                                              │
├── Model Validation Due Date (EXPIRATION POINT) ──────────────────────────────►
│                                                                              │
│   After this date:                                                           │
│   - If active validation in ASSIGNED/IN_PROGRESS/REVIEW/PENDING_APPROVAL     │
│     → VALIDATION_IN_PROGRESS                                                 │
│   - If no active validation OR validation in INTAKE                          │
│     → EXPIRED                                                                │
```

**Important:** A model with an approved validation stays **APPROVED** throughout the entire revalidation window, even if a new validation request has been created. The status only changes to VALIDATION_IN_PROGRESS or EXPIRED after the model passes its validation due date.

### Status Determination Logic (Priority Order)

```
1. If is_model == False → NULL (non-models don't have approval status)

2. If no APPROVED validation ever exists:
   → NEVER_VALIDATED

3. Get most recent APPROVED validation and check if all approvals complete:
   - All ValidationApproval records with is_required=True have approval_status='Approved'
   - Model.use_approval_date is set (conditional approvals complete)
   
   If approvals incomplete on most recent "APPROVED" validation:
   → Check if model is overdue (see step 4)
   → If overdue: VALIDATION_IN_PROGRESS (validation approved but awaiting final approvals past deadline)
   → If not overdue: APPROVED (still within window, approvals pending doesn't affect status)

4. Check if model is OVERDUE (today > model_validation_due_date):
   
   If NOT overdue:
   → Check validation type of most recent approved validation:
      - If validation_type.code == 'INTERIM': INTERIM_APPROVED
      - Else: APPROVED
   
   If OVERDUE:
   → Check for active validation request (status not in [APPROVED, CANCELLED, INTAKE]):
      - If active validation in substantive stage (ASSIGNED, IN_PROGRESS, REVIEW, PENDING_APPROVAL):
        → VALIDATION_IN_PROGRESS
      - If no active validation OR only in INTAKE stage:
        → EXPIRED
```

### Status Transition Examples

**Example 1: Normal Revalidation Cycle (On Time)**
```
Jan 1, 2024:  Validation approved → APPROVED
Oct 1, 2024:  New validation created (INTAKE) → APPROVED (still within window)
Nov 1, 2024:  Validation moves to ASSIGNED → APPROVED (still within window)
Dec 15, 2024: Submission due date passes → APPROVED (in grace period)
Mar 15, 2025: Grace period ends → APPROVED (in lead time)
Jun 15, 2025: Model validation due date → Still APPROVED if not past this date
Jun 16, 2025: ONE DAY OVERDUE → VALIDATION_IN_PROGRESS (has active validation)
Jul 1, 2025:  Validation approved → APPROVED
```

**Example 2: Overdue Without Active Validation**
```
Jan 1, 2024:  Validation approved → APPROVED
Jun 16, 2025: Model validation due date passes, no new validation created → EXPIRED
Jul 1, 2025:  New validation created (INTAKE) → EXPIRED (INTAKE doesn't count)
Jul 5, 2025:  Validation moves to ASSIGNED → VALIDATION_IN_PROGRESS
Aug 1, 2025:  Validation approved → APPROVED
```

**Example 3: Interim Approval**
```
Jan 1, 2024:  INTERIM validation approved → INTERIM_APPROVED
Jun 16, 2025: Overdue, no active validation → EXPIRED
Jul 1, 2025:  Full validation created and in progress → VALIDATION_IN_PROGRESS
Aug 1, 2025:  Full validation approved → APPROVED
```

---

## Data Model

### New Table: `model_approval_status_history`

Tracks changes to model approval status over time for audit purposes.

```python
class ModelApprovalStatusHistory(Base):
    """Audit trail for model approval status changes."""
    __tablename__ = "model_approval_status_history"

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), 
        nullable=False, index=True
    )
    old_status: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True,
        comment="Previous approval status (NULL for initial status)"
    )
    new_status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="New approval status"
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    trigger_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="What triggered this change: VALIDATION_APPROVED, VALIDATION_CREATED, APPROVAL_SUBMITTED, EXPIRATION_CHECK, MANUAL"
    )
    trigger_entity_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="Entity type that triggered change: ValidationRequest, ValidationApproval, etc."
    )
    trigger_entity_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="ID of the entity that triggered the change"
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Additional context about the status change"
    )

    # Relationships
    model = relationship("Model", back_populates="approval_status_history")
```

### New Taxonomy: `Model Approval Status`

Add to seed data for the taxonomy system:

```python
{
    "taxonomy_type": "Model Approval Status",
    "code": "model_approval_status",
    "values": [
        {"code": "NEVER_VALIDATED", "label": "Never Validated", "sort_order": 1},
        {"code": "APPROVED", "label": "Approved", "sort_order": 2},
        {"code": "INTERIM_APPROVED", "label": "Interim Approved", "sort_order": 3},
        {"code": "VALIDATION_IN_PROGRESS", "label": "Validation In Progress", "sort_order": 4},
        {"code": "EXPIRED", "label": "Expired", "sort_order": 5},
    ]
}
```

---

## API Design

### New Endpoint: Get Model Approval Status

```
GET /models/{model_id}/approval-status
```

**Response Schema:**
```python
class ModelApprovalStatusResponse(BaseModel):
    model_id: int
    model_name: str
    is_model: bool
    
    # Current status
    approval_status: Optional[str]  # NULL for non-models
    approval_status_label: Optional[str]
    status_determined_at: datetime
    
    # Validation context
    latest_approved_validation_id: Optional[int]
    latest_approved_validation_date: Optional[datetime]
    latest_approved_validation_type: Optional[str]  # INITIAL, COMPREHENSIVE, INTERIM, etc.
    
    active_validation_id: Optional[int]
    active_validation_status: Optional[str]
    
    # Approval details
    all_approvals_complete: bool
    pending_approval_count: int
    conditional_approvals_complete: bool
    use_approval_date: Optional[datetime]
    
    # Expiration context
    next_validation_due_date: Optional[date]
    days_until_due: Optional[int]  # Negative if overdue
    is_overdue: bool
    
    # Timestamps
    initial_approval_date: Optional[datetime]  # When model was first ever approved
```

### New Endpoint: Get Model Approval Status History

```
GET /models/{model_id}/approval-status/history
```

**Query Parameters:**
- `limit`: int (default 50)
- `offset`: int (default 0)

**Response Schema:**
```python
class ModelApprovalStatusHistoryItem(BaseModel):
    history_id: int
    old_status: Optional[str]
    old_status_label: Optional[str]
    new_status: str
    new_status_label: str
    changed_at: datetime
    trigger_type: str
    trigger_entity_type: Optional[str]
    trigger_entity_id: Optional[int]
    notes: Optional[str]

class ModelApprovalStatusHistoryResponse(BaseModel):
    model_id: int
    model_name: str
    total_count: int
    history: List[ModelApprovalStatusHistoryItem]
```

### Bulk Endpoint: Get Approval Status for Multiple Models

```
POST /models/approval-status/bulk
```

**Request:**
```python
class BulkApprovalStatusRequest(BaseModel):
    model_ids: List[int]
```

**Response:**
```python
class BulkApprovalStatusResponse(BaseModel):
    statuses: Dict[int, ModelApprovalStatusResponse]  # model_id -> status
```

---

## Core Computation Module

Create new module: `api/app/core/model_approval_status.py`

```python
"""
Model Approval Status computation and history tracking.

This module provides functions to:
1. Compute the current approval status of a model
2. Record status changes to history
3. Trigger status recalculation when relevant events occur
"""

from datetime import date, datetime
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from app.models import Model, ValidationRequest, ValidationApproval, TaxonomyValue
from app.models.model_approval_status_history import ModelApprovalStatusHistory
from app.core.time import utc_now


class ApprovalStatus:
    """Enum-like class for approval status codes."""
    NEVER_VALIDATED = "NEVER_VALIDATED"
    APPROVED = "APPROVED"
    INTERIM_APPROVED = "INTERIM_APPROVED"
    VALIDATION_IN_PROGRESS = "VALIDATION_IN_PROGRESS"
    EXPIRED = "EXPIRED"


def compute_model_approval_status(
    model: Model,
    db: Session
) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Compute the current approval status for a model.
    
    Key Logic:
    - Models remain APPROVED throughout the revalidation window
    - Status only changes to VALIDATION_IN_PROGRESS or EXPIRED after the model is OVERDUE
    - VALIDATION_IN_PROGRESS requires both: (1) model is overdue AND (2) active validation in substantive stage
    - EXPIRED means model is overdue with no substantive validation work happening
    
    Returns:
        Tuple of (status_code, context_dict)
        - status_code: One of ApprovalStatus constants, or None for non-models
        - context_dict: Additional context about the determination
    """
    # Non-models don't have approval status
    if not model.is_model:
        return None, {"reason": "Non-model entity"}
    
    context = {
        "model_id": model.model_id,
        "computed_at": utc_now(),
    }
    
    # Get most recent APPROVED validation
    latest_approved = _get_latest_approved_validation(model, db)
    if not latest_approved:
        return ApprovalStatus.NEVER_VALIDATED, context
    
    context["latest_approved_validation_id"] = latest_approved.request_id
    context["latest_approved_date"] = latest_approved.completion_date or latest_approved.updated_at
    context["validation_type"] = latest_approved.validation_type.code if latest_approved.validation_type else None
    
    # Check if all required approvals are complete on the approved validation
    approvals_complete, pending_count = _check_approvals_complete(latest_approved, model, db)
    context["approvals_complete"] = approvals_complete
    context["pending_approval_count"] = pending_count
    
    # Check if model is overdue for revalidation
    is_overdue = _is_model_overdue(model, latest_approved, db)
    context["is_overdue"] = is_overdue
    
    if not is_overdue:
        # Model is within revalidation window - stays APPROVED or INTERIM_APPROVED
        # regardless of whether a new validation has been started
        validation_type_code = latest_approved.validation_type.code if latest_approved.validation_type else None
        if validation_type_code == "INTERIM":
            return ApprovalStatus.INTERIM_APPROVED, context
        return ApprovalStatus.APPROVED, context
    
    # Model is OVERDUE - now check if there's substantive validation work happening
    active_validation = _get_active_substantive_validation(model, db)
    context["active_validation_id"] = active_validation.request_id if active_validation else None
    context["active_validation_status"] = active_validation.current_status.code if active_validation else None
    
    if active_validation:
        # Overdue but validation work is in progress
        return ApprovalStatus.VALIDATION_IN_PROGRESS, context
    
    # Overdue with no substantive validation work
    return ApprovalStatus.EXPIRED, context


def _get_active_substantive_validation(model: Model, db: Session) -> Optional[ValidationRequest]:
    """
    Get active validation request in a substantive stage for model.
    
    Substantive stages are: ASSIGNED, IN_PROGRESS, REVIEW, PENDING_APPROVAL
    INTAKE stage does NOT count as substantive work has not begun.
    """
    from app.models.validation import ValidationRequestModelVersion
    
    # Statuses that indicate substantive validation work
    substantive_statuses = ["ASSIGNED", "IN_PROGRESS", "REVIEW", "PENDING_APPROVAL"]
    
    return db.query(ValidationRequest).join(
        ValidationRequestModelVersion
    ).filter(
        ValidationRequestModelVersion.model_id == model.model_id,
        ValidationRequest.current_status.has(
            TaxonomyValue.code.in_(substantive_statuses)
        )
    ).order_by(
        ValidationRequest.created_at.desc()
    ).first()


def _get_active_validation(model: Model, db: Session) -> Optional[ValidationRequest]:
    """Get any active (non-terminal) validation request for model."""
    from app.models.validation import ValidationRequestModelVersion
    
    return db.query(ValidationRequest).join(
        ValidationRequestModelVersion
    ).filter(
        ValidationRequestModelVersion.model_id == model.model_id,
        ValidationRequest.current_status.has(
            TaxonomyValue.code.notin_(["APPROVED", "CANCELLED"])
        )
    ).order_by(
        ValidationRequest.created_at.desc()
    ).first()


def _get_latest_approved_validation(model: Model, db: Session) -> Optional[ValidationRequest]:
    """Get most recent APPROVED validation for model."""
    from app.models.validation import ValidationRequestModelVersion
    
    return db.query(ValidationRequest).join(
        ValidationRequestModelVersion
    ).filter(
        ValidationRequestModelVersion.model_id == model.model_id,
        ValidationRequest.current_status.has(TaxonomyValue.code == "APPROVED")
    ).order_by(
        ValidationRequest.completion_date.desc().nullslast(),
        ValidationRequest.updated_at.desc()
    ).first()


def _is_model_overdue(
    model: Model,
    latest_approved: ValidationRequest,
    db: Session
) -> bool:
    """Check if model is overdue for revalidation."""
    # Use existing revalidation status calculation
    from app.api.validation_workflow import calculate_model_revalidation_status
    
    status = calculate_model_revalidation_status(model, db)
    return status.get("status") in [
        "Submission Overdue",
        "Validation Overdue",
        "Revalidation Overdue (No Request)"
    ]


def _check_approvals_complete(
    validation: ValidationRequest,
    model: Model,
    db: Session
) -> Tuple[bool, int]:
    """
    Check if all required approvals are complete.
    
    Returns:
        Tuple of (all_complete, pending_count)
    """
    # Check traditional approvals
    pending_traditional = db.query(ValidationApproval).filter(
        ValidationApproval.request_id == validation.request_id,
        ValidationApproval.is_required == True,
        ValidationApproval.approval_status == "Pending",
        ValidationApproval.voided_at.is_(None)  # Not voided
    ).count()
    
    # Check conditional approvals (via use_approval_date)
    # If conditional approvals were required but not complete, use_approval_date would be None
    conditional_complete = True
    if _has_conditional_approval_requirements(validation, db):
        conditional_complete = model.use_approval_date is not None
    
    pending_count = pending_traditional
    if not conditional_complete:
        # Count pending conditional approvals
        pending_conditional = db.query(ValidationApproval).filter(
            ValidationApproval.request_id == validation.request_id,
            ValidationApproval.approver_role_id.isnot(None),  # Conditional approval
            ValidationApproval.approval_status == "Pending",
            ValidationApproval.voided_at.is_(None)
        ).count()
        pending_count += pending_conditional
    
    all_complete = pending_traditional == 0 and conditional_complete
    return all_complete, pending_count


def _has_conditional_approval_requirements(
    validation: ValidationRequest,
    db: Session
) -> bool:
    """Check if this validation has any conditional approval requirements."""
    return db.query(ValidationApproval).filter(
        ValidationApproval.request_id == validation.request_id,
        ValidationApproval.approver_role_id.isnot(None)
    ).count() > 0


def record_status_change(
    model_id: int,
    old_status: Optional[str],
    new_status: str,
    trigger_type: str,
    db: Session,
    trigger_entity_type: Optional[str] = None,
    trigger_entity_id: Optional[int] = None,
    notes: Optional[str] = None
) -> ModelApprovalStatusHistory:
    """Record a status change to history."""
    history = ModelApprovalStatusHistory(
        model_id=model_id,
        old_status=old_status,
        new_status=new_status,
        trigger_type=trigger_type,
        trigger_entity_type=trigger_entity_type,
        trigger_entity_id=trigger_entity_id,
        notes=notes
    )
    db.add(history)
    return history


def get_status_label(status_code: Optional[str]) -> Optional[str]:
    """Get human-readable label for status code."""
    labels = {
        ApprovalStatus.NEVER_VALIDATED: "Never Validated",
        ApprovalStatus.APPROVED: "Approved",
        ApprovalStatus.INTERIM_APPROVED: "Interim Approved",
        ApprovalStatus.VALIDATION_IN_PROGRESS: "Validation In Progress",
        ApprovalStatus.EXPIRED: "Expired",
    }
    return labels.get(status_code)
```

---

## Integration Points

### 1. Validation Request Status Changes

When `ValidationRequest.current_status` changes, recalculate approval status for all models in that request.

**File:** `api/app/api/validation_workflow.py`

**Location:** `update_request_status()` endpoint

```python
# After status change is committed
from app.core.model_approval_status import compute_model_approval_status, record_status_change

for model_assoc in validation_request.model_versions_assoc:
    model = model_assoc.model
    old_status = _get_cached_status(model, db)  # Get from last history record
    new_status, context = compute_model_approval_status(model, db)
    
    if old_status != new_status:
        record_status_change(
            model_id=model.model_id,
            old_status=old_status,
            new_status=new_status,
            trigger_type="VALIDATION_STATUS_CHANGE",
            trigger_entity_type="ValidationRequest",
            trigger_entity_id=validation_request.request_id,
            notes=f"Validation status changed to {new_status_code}",
            db=db
        )
```

### 2. Validation Approval Submissions

When a `ValidationApproval` is submitted (approved/rejected), recalculate.

**File:** `api/app/api/validation_workflow.py`

**Location:** `submit_approval()` and `submit_conditional_approval()` endpoints

### 3. Validation Request Creation

When a new `ValidationRequest` is created, models transition from their current status to `VALIDATION_IN_PROGRESS`.

**File:** `api/app/api/validation_workflow.py`

**Location:** `create_validation_request()` endpoint

### 4. Scheduled Expiration Check (Optional Background Job)

A periodic job could scan for models approaching or past expiration and update their status.

**Approach:** Since we're using computed status, this is mainly for proactive history recording. The computation will always return the correct current status.

```python
# Pseudo-code for scheduled job
def check_model_expirations(db: Session):
    """Check all models for expiration status changes."""
    models = db.query(Model).filter(Model.is_model == True).all()
    
    for model in models:
        current_status, _ = compute_model_approval_status(model, db)
        last_recorded = get_last_recorded_status(model, db)
        
        if current_status != last_recorded:
            record_status_change(
                model_id=model.model_id,
                old_status=last_recorded,
                new_status=current_status,
                trigger_type="EXPIRATION_CHECK",
                notes="Status updated during scheduled expiration check",
                db=db
            )
    
    db.commit()
```

---

## Frontend Changes

### 1. Model List Page (`ModelsPage.tsx`)

Add "Approval Status" column with badge styling:

| Status | Badge Color |
|--------|-------------|
| Never Validated | Gray |
| Approved | Green |
| Interim Approved | Yellow/Amber |
| Validation In Progress | Blue |
| Expired | Red |

Add filter dropdown: "Filter by Approval Status"

### 2. Model Details Page (`ModelDetailsPage.tsx`)

Add approval status badge in the model header/info card section.

Add new "Approval Status" tab or section showing:
- Current status with badge
- Latest approved validation link
- Next validation due date
- Days until due (or days overdue)
- Status history timeline

### 3. Dashboard Enhancements

**Admin Dashboard:**
- Add widget: "Models by Approval Status" (pie chart or counts)
- Add widget: "Expiring Soon" (models within 30/60/90 days of expiration)

**Model Owner Dashboard:**
- Show approval status for owned models
- Alert for models expiring soon or expired

### 4. Reports

Add approval status to:
- Regional Compliance Report (already has `is_validation_approved`, enhance with full status)
- Overdue Revalidation Report
- CSV exports

---

## Database Migration

```python
"""Add model approval status history table.

Revision ID: xxxx
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create model_approval_status_history table
    op.create_table(
        'model_approval_status_history',
        sa.Column('history_id', sa.Integer(), primary_key=True),
        sa.Column('model_id', sa.Integer(), sa.ForeignKey('models.model_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('old_status', sa.String(30), nullable=True),
        sa.Column('new_status', sa.String(30), nullable=False),
        sa.Column('changed_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('trigger_type', sa.String(50), nullable=False),
        sa.Column('trigger_entity_type', sa.String(50), nullable=True),
        sa.Column('trigger_entity_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
    )
    
    # Create indexes
    op.create_index(
        'ix_model_approval_status_history_model_changed',
        'model_approval_status_history',
        ['model_id', 'changed_at']
    )

def downgrade():
    op.drop_table('model_approval_status_history')
```

---

## Seed Data Migration

After creating the table, backfill initial status for all existing models:

```python
def backfill_model_approval_status_history(db: Session):
    """Create initial history records for all existing models."""
    from app.core.model_approval_status import compute_model_approval_status, record_status_change
    
    models = db.query(Model).filter(Model.is_model == True).all()
    
    for model in models:
        # Check if already has history
        existing = db.query(ModelApprovalStatusHistory).filter(
            ModelApprovalStatusHistory.model_id == model.model_id
        ).first()
        
        if not existing:
            current_status, context = compute_model_approval_status(model, db)
            if current_status:
                record_status_change(
                    model_id=model.model_id,
                    old_status=None,
                    new_status=current_status,
                    trigger_type="BACKFILL",
                    notes="Initial status record created during migration",
                    db=db
                )
    
    db.commit()
```

---

## Testing Plan

### Unit Tests (`api/tests/test_model_approval_status.py`)

1. **Status Computation Tests:**
   - `test_never_validated_status` - Model with no validations returns NEVER_VALIDATED
   - `test_approved_status` - Model with approved validation, all approvals complete, within window
   - `test_approved_status_with_active_validation_within_window` - Model stays APPROVED even when new validation started (not overdue yet)
   - `test_interim_approved_status` - Model with approved INTERIM validation
   - `test_expired_status_no_active_validation` - Model overdue with no active validation
   - `test_expired_status_intake_only` - Model overdue with validation in INTAKE stage only
   - `test_validation_in_progress_when_overdue_with_active` - Model overdue but has validation in ASSIGNED/IN_PROGRESS
   - `test_validation_in_progress_review_stage` - Model overdue with validation in REVIEW
   - `test_validation_in_progress_pending_approval_stage` - Model overdue with validation in PENDING_APPROVAL
   - `test_non_model_returns_null` - Non-model entities return null status

2. **Edge Case Tests:**
   - `test_approved_one_day_before_due` - Model is APPROVED on last day before expiration
   - `test_expired_one_day_after_due` - Model is EXPIRED/VALIDATION_IN_PROGRESS on first day after expiration
   - `test_status_with_pending_conditional_approvals_within_window` - Still APPROVED if within window even with pending approvals
   - `test_multiple_models_in_validation_request` - Status computed correctly for each model independently

3. **History Recording Tests:**
   - `test_history_recorded_on_validation_approval`
   - `test_history_recorded_on_status_transition_to_expired`
   - `test_history_recorded_on_transition_to_validation_in_progress`
   - `test_history_not_recorded_when_status_unchanged`
   - `test_history_trigger_type_captured_correctly`

4. **API Tests:**
   - `test_get_approval_status_endpoint`
   - `test_get_approval_status_history_endpoint`
   - `test_bulk_approval_status_endpoint`
   - `test_approval_status_context_fields_populated`

5. **Integration Tests:**
   - `test_full_lifecycle_never_validated_to_approved`
   - `test_full_lifecycle_approved_to_expired_to_approved`
   - `test_lifecycle_approved_to_validation_in_progress_when_overdue`
   - `test_interim_to_full_approval_transition`
   - `test_status_unchanged_during_revalidation_window`

---

## Implementation Phases

### Phase 1: Core Infrastructure
1. Create `ModelApprovalStatusHistory` model
2. Create Alembic migration
3. Create `model_approval_status.py` core module with computation logic
4. Add taxonomy seed data

### Phase 2: API Endpoints
1. Implement `GET /models/{id}/approval-status`
2. Implement `GET /models/{id}/approval-status/history`
3. Implement `POST /models/approval-status/bulk`
4. Add approval status to `ModelDetailResponse` schema

### Phase 3: Integration Points
1. Hook into `validation_workflow.py` status change handlers
2. Hook into approval submission handlers
3. Hook into validation request creation
4. Run backfill migration for existing data

### Phase 4: Frontend - Model Pages
1. Add approval status badge to Model list
2. Add filter by approval status
3. Add approval status section to Model details page
4. Add status history timeline component

### Phase 5: Frontend - Dashboards & Reports
1. Add dashboard widgets
2. Update reports with approval status
3. Add CSV export fields

### Phase 6: Testing & Documentation
1. Complete unit test suite
2. Integration tests
3. Update ARCHITECTURE.md
4. Update user documentation

---

## Open Questions / Future Considerations

1. **Caching:** For high-traffic deployments, consider caching computed status with invalidation on relevant events.

2. **Notifications:** Should users be notified when model approval status changes (especially to EXPIRED)?

3. **Bulk Operations:** For large model portfolios, consider async computation for bulk status requests.

4. **Audit Integration:** Should status changes also create `AuditLog` entries in addition to the dedicated history table?

5. **Regional Status (Deferred):** Per original discussion, regional approval status was deferred. This could be added later as an enhancement.
