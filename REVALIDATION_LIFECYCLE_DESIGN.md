# Revalidation Lifecycle Workflow Design

## Executive Summary

This document outlines the design for automated periodic revalidation tracking with proper grace periods and SLA calculations based on submission due dates (not received dates).

**Status**: Design Phase
**Target**: Automated revalidation scheduling and tracking with compliance monitoring

---

## 1. Revalidation Lifecycle Overview

### Timeline Phases

```
[Last Validation] ──(Frequency)──> [Submission Due] ──(3mo grace)──> [Grace End] ──(Lead Time)──> [Validation Due]
     Completed                          │                                    │                            │
     Date                               │                                    │                            │
                                        │                                    │ [Validation SLA Starts]    │
                                 [Submission Received]                       │                            │
                                   (Actual Date)                             │                            │
                                        │                                    │                            │
                                        └────────────(validation work)───────┴───────────────────────────> [Validation Complete]
```

### Key Dates (All Dynamically Calculated)

1. **Last Validation Completed Date** - Starting point for countdown (from approved validation)
2. **Submission Due Date** = Last Validation Date + Re-validation Frequency (from policy)
3. **Grace Period End Date** = Submission Due Date + 3 months
4. **Submission Received Date** - When model owner actually submits documentation
5. **Validation Due Date** = Submission Due Date + 3 months + Lead Time
   - Equivalently: = Grace Period End + Lead Time
6. **Validation Completed Date** - When validation is approved

### Critical Business Rules

1. **Two Different "Due Dates" to Track**:
   - **Model Validation Due Date** (Compliance): Submission Due + 3mo grace + Lead Time
     - Fixed date based on last validation + policy
     - Model is "overdue" if not validated by this date (regardless of submission timing)
   - **Validation Team SLA**: Lead Time from submission received date
     - Measures validation team performance
     - Starts when documentation is actually received

2. **Example Timeline**:
   - Last Validation: 2024-01-01
   - Frequency: 12 months → Submission Due: 2025-01-01
   - Grace Period: 3mo → Grace End: 2025-04-01
   - Lead Time: 90 days → Model Validation Due: 2025-06-30

   **Scenario 1**: Submission received on-time (2025-01-01)
   - Validation Team SLA Due: 2025-04-01 (submission + 90 days)
   - Model Validation Due: 2025-06-30 (unchanged)
   - Result: Team has extra time buffer

   **Scenario 2**: Submission received late (2025-03-01)
   - Validation Team SLA Due: 2025-05-30 (submission + 90 days)
   - Model Validation Due: 2025-06-30 (unchanged)
   - Result: Team still has 90 days, but less buffer for model compliance

   **Scenario 3**: Submission received very late (2025-05-01)
   - Validation Team SLA Due: 2025-07-30 (submission + 90 days)
   - Model Validation Due: 2025-06-30 (unchanged)
   - Result: Model is overdue even though team gets full 90 days

3. **Grace Period is 3 months** for documentation submission
   - Submission is "due" after due date but not "overdue" until grace period expires
   - After grace period expires, submission is "overdue"

4. **Validation Type Determines if Periodic**
   - COMPREHENSIVE = periodic revalidations (follows this lifecycle)
   - TARGETED, INTERIM = change-driven (different rules)
   - No need for separate `is_periodic_revalidation` flag

5. **No Automated Background Jobs** (Initial Design)
   - Everything calculated dynamically from existing data
   - No auto-creation of validation requests
   - Admin/Model Owner visibility into upcoming revalidations via dashboard queries

---

## 2. Schema Design

### Enhancement to `validation_requests` Table

Add revalidation lifecycle tracking fields:

```python
class ValidationRequest(Base):
    """Main validation request entity - workflow-based."""
    __tablename__ = "validation_requests"

    # ... existing fields ...

    # Revalidation Lifecycle Fields (NEW - Only 2 fields!)
    prior_validation_request_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("validation_requests.request_id", ondelete="SET NULL"),
        nullable=True,
        comment="Link to the previous validation that this revalidation follows"
    )

    submission_received_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Date model owner actually submitted documentation"
    )

    # Computed properties (dynamically calculated, no stored dates)
    @property
    def is_periodic_revalidation(self) -> bool:
        """Determine if this is a periodic revalidation based on validation type."""
        # COMPREHENSIVE is periodic revalidation
        # TARGETED, INTERIM are change-driven
        if not self.validation_type:
            return False
        return self.validation_type.code == "COMPREHENSIVE"

    @property
    def submission_due_date(self) -> Optional[date]:
        """Calculate submission due date from prior validation + frequency."""
        if not self.is_periodic_revalidation or not self.prior_validation_request_id:
            return None

        # Get prior validation
        prior = self.prior_validation_request
        if not prior or prior.current_status.code != "APPROVED":
            return None

        # Find when prior was approved (use updated_at as proxy for approval date)
        prior_completed = prior.updated_at.date()

        # Get model to find risk tier
        model = self.model_versions_assoc[0].model

        # Get policy for this risk tier
        from app.models.validation import ValidationPolicy
        policy = Session.object_session(self).query(ValidationPolicy).filter(
            ValidationPolicy.risk_tier_id == model.risk_tier_id
        ).first()

        if not policy:
            return None

        # Calculate: prior_completed + frequency_months
        from dateutil.relativedelta import relativedelta
        return prior_completed + relativedelta(months=policy.frequency_months)

    @property
    def submission_grace_period_end(self) -> Optional[date]:
        """Calculate grace period end (submission_due + 3 months)."""
        if not self.submission_due_date:
            return None
        from dateutil.relativedelta import relativedelta
        return self.submission_due_date + relativedelta(months=3)

    @property
    def model_validation_due_date(self) -> Optional[date]:
        """
        Model compliance due date (fixed based on policy).
        = Submission Due + 3mo grace + Lead Time
        Model is "overdue" if not validated by this date.
        """
        if not self.submission_grace_period_end:
            return None

        # Get model to find risk tier
        model = self.model_versions_assoc[0].model

        # Get policy for this risk tier
        from app.models.validation import ValidationPolicy
        policy = Session.object_session(self).query(ValidationPolicy).filter(
            ValidationPolicy.risk_tier_id == model.risk_tier_id
        ).first()

        if not policy:
            return None

        from datetime import timedelta
        return self.submission_grace_period_end + timedelta(days=policy.model_change_lead_time_days)

    @property
    def validation_team_sla_due_date(self) -> Optional[date]:
        """
        Validation team SLA due date (based on actual submission).
        = Submission Received + Lead Time
        Measures team performance independent of submission timing.
        """
        if not self.submission_received_date:
            return None  # SLA doesn't start until submission received

        # Get model to find risk tier
        model = self.model_versions_assoc[0].model

        # Get policy for this risk tier
        from app.models.validation import ValidationPolicy
        policy = Session.object_session(self).query(ValidationPolicy).filter(
            ValidationPolicy.risk_tier_id == model.risk_tier_id
        ).first()

        if not policy:
            return None

        from datetime import timedelta
        return self.submission_received_date + timedelta(days=policy.model_change_lead_time_days)

    @property
    def submission_status(self) -> str:
        """Calculate current submission status."""
        if not self.is_periodic_revalidation:
            return "N/A"

        if self.submission_received_date:
            if self.submission_received_date <= self.submission_due_date:
                return "Submitted On Time"
            elif self.submission_received_date <= self.submission_grace_period_end:
                return "Submitted In Grace Period"
            else:
                return "Submitted Late"

        today = date.today()
        if not self.submission_due_date:
            return "Unknown"
        if today < self.submission_due_date:
            return "Not Yet Due"
        elif today <= self.submission_grace_period_end:
            return "Due (In Grace Period)"
        else:
            return "Overdue"

    @property
    def model_compliance_status(self) -> str:
        """
        Is the MODEL overdue for validation (regardless of team performance)?
        Based on model_validation_due_date.
        """
        if not self.is_periodic_revalidation:
            return "N/A"

        if self.current_status.code == "APPROVED":
            # Check if completed on time
            completed_date = self.updated_at.date()
            if completed_date <= self.model_validation_due_date:
                return "Validated On Time"
            else:
                return "Validated Late"

        today = date.today()
        if not self.model_validation_due_date:
            return "Unknown"

        if today <= self.submission_due_date:
            return "On Track"
        elif today <= self.submission_grace_period_end:
            return "In Grace Period"
        elif today <= self.model_validation_due_date:
            return "At Risk"
        else:
            return "Overdue"

    @property
    def validation_team_sla_status(self) -> str:
        """
        Is the validation TEAM behind on their SLA?
        Based on validation_team_sla_due_date (from submission received).
        """
        if not self.is_periodic_revalidation:
            return "N/A"

        if not self.submission_received_date:
            return "Awaiting Submission"

        if self.current_status.code == "APPROVED":
            # Check if completed within SLA
            completed_date = self.updated_at.date()
            if completed_date <= self.validation_team_sla_due_date:
                return "Completed Within SLA"
            else:
                return "Completed Past SLA"

        today = date.today()
        if not self.validation_team_sla_due_date:
            return "Unknown"

        if today <= self.validation_team_sla_due_date:
            return "In Progress (On Time)"
        else:
            return "In Progress (Past SLA)"

    @property
    def days_until_submission_due(self) -> Optional[int]:
        """Days until submission due (negative if past)."""
        if not self.submission_due_date:
            return None
        return (self.submission_due_date - date.today()).days

    @property
    def days_until_model_validation_due(self) -> Optional[int]:
        """Days until model validation due (negative if overdue)."""
        if not self.model_validation_due_date:
            return None
        return (self.model_validation_due_date - date.today()).days

    @property
    def days_until_team_sla_due(self) -> Optional[int]:
        """Days until validation team SLA expires (negative if past)."""
        if not self.validation_team_sla_due_date:
            return None
        return (self.validation_team_sla_due_date - date.today()).days

    # Relationships
    prior_validation_request = relationship(
        "ValidationRequest",
        foreign_keys=[prior_validation_request_id],
        remote_side=[request_id]
    )
```

---

## 3. Dynamic Revalidation Calculation (No Background Jobs)

### Query Helper: Get Models Needing Revalidation

Calculate upcoming revalidations on-the-fly from existing data:

```python
def calculate_model_revalidation_status(model: Model, db: Session) -> dict:
    """
    Calculate revalidation status for a model dynamically.
    No stored schedule - computed from last validation + policy.
    """

    # Find most recent APPROVED validation for this model
    last_validation = db.query(ValidationRequest).join(
        ValidationRequestModelVersion
    ).filter(
        ValidationRequestModelVersion.model_id == model.model_id,
        ValidationRequest.current_status.has(TaxonomyValue.code == "APPROVED")
    ).order_by(
        ValidationRequest.updated_at.desc()
    ).first()

    if not last_validation:
        return {
            "model_id": model.model_id,
            "model_name": model.model_name,
            "status": "Never Validated",
            "last_validation_date": None,
            "next_submission_due": None,
            "next_validation_due": None
        }

    # Get validation policy for this model's risk tier
    policy = db.query(ValidationPolicy).filter(
        ValidationPolicy.risk_tier_id == model.risk_tier_id
    ).first()

    if not policy:
        return {
            "model_id": model.model_id,
            "model_name": model.model_name,
            "status": "No Policy Configured",
            "last_validation_date": last_validation.updated_at.date(),
            "next_submission_due": None,
            "next_validation_due": None
        }

    # Calculate dates
    last_completed = last_validation.updated_at.date()
    from dateutil.relativedelta import relativedelta
    submission_due = last_completed + relativedelta(months=policy.frequency_months)
    grace_period_end = submission_due + relativedelta(months=3)
    validation_due = grace_period_end + timedelta(days=policy.model_change_lead_time_days)

    # Check if active revalidation request exists
    active_request = db.query(ValidationRequest).join(
        ValidationRequestModelVersion
    ).filter(
        ValidationRequestModelVersion.model_id == model.model_id,
        ValidationRequest.is_periodic_revalidation == True,
        ValidationRequest.prior_validation_request_id == last_validation.request_id,
        ValidationRequest.current_status.has(TaxonomyValue.code.not_in(["APPROVED", "CANCELLED"]))
    ).first()

    today = date.today()

    # Determine status
    if active_request:
        if not active_request.submission_received_date:
            if today > grace_period_end:
                status = "Submission Overdue"
            elif today > submission_due:
                status = "In Grace Period"
            else:
                status = "Awaiting Submission"
        else:
            if today > validation_due:
                status = "Validation Overdue"
            else:
                status = "Validation In Progress"
    else:
        # No active request
        if today > validation_due:
            status = "Revalidation Overdue (No Request)"
        elif today > grace_period_end:
            status = "Should Create Request"
        else:
            status = "Upcoming"

    return {
        "model_id": model.model_id,
        "model_name": model.model_name,
        "model_owner": model.owner.full_name,
        "risk_tier": model.risk_tier.label if model.risk_tier else None,
        "status": status,
        "last_validation_date": last_completed,
        "next_submission_due": submission_due,
        "grace_period_end": grace_period_end,
        "next_validation_due": validation_due,
        "days_until_submission_due": (submission_due - today).days,
        "days_until_validation_due": (validation_due - today).days,
        "active_request_id": active_request.request_id if active_request else None,
        "submission_received": active_request.submission_received_date if active_request else None
    }


def get_models_needing_revalidation(
    db: Session,
    days_ahead: int = 90,
    include_overdue: bool = True
) -> List[dict]:
    """
    Get all models that need revalidation (upcoming or overdue).
    Calculates dynamically - no stored schedule.
    """

    today = date.today()
    results = []

    # Get all active models
    models = db.query(Model).filter(
        Model.status == "Active"
    ).all()

    for model in models:
        revalidation_status = calculate_model_revalidation_status(model, db)

        # Filter based on criteria
        if include_overdue and "Overdue" in revalidation_status["status"]:
            results.append(revalidation_status)
        elif revalidation_status["days_until_submission_due"] is not None:
            if revalidation_status["days_until_submission_due"] <= days_ahead:
                results.append(revalidation_status)

    # Sort by submission due date
    results.sort(key=lambda x: x["next_submission_due"] if x["next_submission_due"] else date.max)

    return results
```

---

## 4. Submission Tracking

### API Endpoint: Mark Submission Received

```python
@router.patch("/validation-workflow/requests/{request_id}/submit-documentation")
async def mark_documentation_submitted(
    request_id: int,
    submission_data: SubmissionReceived,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark that model owner has submitted documentation for revalidation.

    IMPORTANT: This does NOT change the validation_due_date, which is
    calculated from submission_due_date, not submission_received_date.
    """

    validation_request = db.query(ValidationRequest).filter(
        ValidationRequest.request_id == request_id
    ).first()

    if not validation_request:
        raise HTTPException(status_code=404, detail="Validation request not found")

    if not validation_request.is_periodic_revalidation:
        raise HTTPException(
            status_code=400,
            detail="This endpoint only applies to periodic revalidations"
        )

    # Record submission
    validation_request.submission_received_date = submission_data.received_date or date.today()
    validation_request.updated_at = datetime.utcnow()

    # Transition to "PLANNING" status if still in INTAKE
    if validation_request.current_status.code == "INTAKE":
        planning_status = db.query(TaxonomyValue).join(Taxonomy).filter(
            Taxonomy.name == "Validation Request Status",
            TaxonomyValue.code == "PLANNING"
        ).first()

        if planning_status:
            validation_request.current_status_id = planning_status.value_id

            # Create status history
            status_history = ValidationStatusHistory(
                request_id=request_id,
                old_status_id=validation_request.current_status_id,
                new_status_id=planning_status.value_id,
                changed_by_id=current_user.user_id,
                changed_at=datetime.utcnow(),
                change_reason="Documentation submitted by model owner"
            )
            db.add(status_history)

    # Create audit log
    audit = AuditLog(
        entity_type="ValidationRequest",
        entity_id=request_id,
        action="DOCUMENTATION_SUBMITTED",
        performed_by_id=current_user.user_id,
        details=f"Documentation submitted on {validation_request.submission_received_date}",
        timestamp=datetime.utcnow()
    )
    db.add(audit)

    db.commit()
    db.refresh(validation_request)

    return {
        "request_id": request_id,
        "submission_received_date": validation_request.submission_received_date,
        "submission_status": validation_request.submission_status,
        "validation_due_date": validation_request.validation_due_date,
        "days_until_validation_due": validation_request.days_until_validation_due,
        "message": "Documentation submission recorded. Note: Validation due date is based on original submission due date, not received date."
    }
```

---

## 5. Dashboard & Monitoring

### Admin Dashboard Widgets

#### 1. Overdue Submissions Widget

```python
@router.get("/validation-workflow/dashboard/overdue-submissions")
async def get_overdue_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    """
    Get models with overdue documentation submissions (past grace period).
    Uses dynamic calculation.
    """

    today = date.today()

    # Find active revalidation requests without submissions
    overdue_requests = db.query(ValidationRequest).filter(
        ValidationRequest.is_periodic_revalidation == True,
        ValidationRequest.submission_received_date == None,
        ValidationRequest.current_status.has(TaxonomyValue.code.in_(["INTAKE", "PLANNING"]))
    ).all()

    results = []
    for req in overdue_requests:
        # Use computed properties
        if req.submission_grace_period_end and today > req.submission_grace_period_end:
            results.append({
                "request_id": req.request_id,
                "model_id": req.model_versions_assoc[0].model_id,
                "model_name": req.model_versions_assoc[0].model.model_name,
                "model_owner": req.model_versions_assoc[0].model.owner.full_name,
                "submission_due_date": req.submission_due_date,
                "grace_period_end": req.submission_grace_period_end,
                "days_overdue": (today - req.submission_grace_period_end).days,
                "validation_due_date": req.validation_due_date,
                "submission_status": req.submission_status
            })

    return results
```

#### 2. Overdue Validations Widget

```python
@router.get("/validation-workflow/dashboard/overdue-validations")
async def get_overdue_validations(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    """
    Get validations past their due date (regardless of when submission received).
    """

    today = date.today()

    overdue = db.query(ValidationRequest).filter(
        ValidationRequest.is_periodic_revalidation == True,
        ValidationRequest.validation_due_date < today,
        ValidationRequest.current_status.has(TaxonomyValue.code.not_in(["APPROVED", "CANCELLED"]))
    ).all()

    return [
        {
            "request_id": req.request_id,
            "model_id": req.model_versions_assoc[0].model_id,
            "model_name": req.model_versions_assoc[0].model.model_name,
            "submission_received_date": req.submission_received_date,
            "submission_was_late": req.submission_received_date and req.submission_received_date > req.submission_due_date,
            "validation_due_date": req.validation_due_date,
            "days_overdue": (today - req.validation_due_date).days,
            "current_status": req.current_status.label,
            "primary_validator": req.assignments[0].validator.full_name if req.assignments else None
        }
        for req in overdue
    ]
```

#### 3. Upcoming Revalidations Widget

```python
@router.get("/validation-workflow/dashboard/upcoming-revalidations")
async def get_upcoming_revalidations(
    days_ahead: int = 90,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    """
    Get models with revalidations due in next N days.
    Uses dynamic calculation - no stored schedule table.
    """

    # Use helper function to calculate all revalidations
    from app.api.validation_workflow import get_models_needing_revalidation

    upcoming = get_models_needing_revalidation(
        db=db,
        days_ahead=days_ahead,
        include_overdue=False  # Only upcoming, not overdue
    )

    return upcoming
```

---

## 6. Model Owner Dashboard

### My Pending Submissions View

```python
@router.get("/validation-workflow/my-pending-submissions")
async def get_my_pending_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get validation requests awaiting documentation submission for models I own.
    """

    # Get models I own
    my_models = db.query(Model).filter(
        Model.owner_id == current_user.user_id
    ).all()

    model_ids = [m.model_id for m in my_models]

    # Find pending revalidations
    pending = db.query(ValidationRequest).join(
        ValidationRequestModelVersion
    ).filter(
        ValidationRequest.is_periodic_revalidation == True,
        ValidationRequest.submission_received_date == None,
        ValidationRequestModelVersion.model_id.in_(model_ids),
        ValidationRequest.current_status.has(TaxonomyValue.code.in_(["INTAKE", "PLANNING"]))
    ).all()

    today = date.today()

    return [
        {
            "request_id": req.request_id,
            "model_id": req.model_versions_assoc[0].model_id,
            "model_name": req.model_versions_assoc[0].model.model_name,
            "submission_due_date": req.submission_due_date,
            "grace_period_end": req.submission_grace_period_end,
            "days_until_due": (req.submission_due_date - today).days,
            "is_in_grace_period": today > req.submission_due_date and today < req.submission_grace_period_end,
            "is_overdue": today > req.submission_grace_period_end,
            "validation_due_date": req.validation_due_date,
            "status": req.submission_status
        }
        for req in pending
    ]
```

---

## 7. UI Components

### 1. New Page: RevalidationsDashboardPage (Admin)

**Route**: `/revalidations-dashboard`

**Sections**:
- Overdue Submissions (past grace period)
- Overdue Validations (past validation due date)
- Upcoming in Next 30/60/90 days
- Filter by risk tier, model owner

### 2. New Page: MyPendingSubmissionsPage (Model Owner)

**Route**: `/my-pending-submissions`

**Features**:
- Table of models needing documentation
- Status badges: "Not Yet Due", "Due", "In Grace Period", "Overdue"
- "Submit Documentation" button → modal with date picker
- Upload area for documentation files

### 3. Enhancement: ValidationRequestDetailPage

**New Section**: "Revalidation Timeline" (if is_periodic_revalidation)

```typescript
interface RevalidationTimeline {
  priorValidationDate: string;
  submissionDueDate: string;
  submissionGracePeriodEnd: string;
  submissionReceivedDate: string | null;
  validationDueDate: string;
  submissionStatus: "Not Yet Due" | "Due" | "In Grace Period" | "Overdue" | "Submitted";
  validationStatus: "Awaiting Submission" | "In Progress" | "Overdue" | "Completed";
}

// Display as visual timeline with color-coded status indicators
```

---

## 8. Implementation Steps

### Phase 1: Schema Updates

**Files**:
- Migration: `add_revalidation_lifecycle_fields.py`
- Update `ValidationRequest` model with new fields:
  - `prior_validation_request_id` (FK to self) - links revalidation to prior validation
  - `submission_received_date` (date) - when docs actually received
  - Computed properties for all calculated dates:
    - `is_periodic_revalidation` (derived from validation_type.code)
    - `submission_due_date`, `submission_grace_period_end`
    - `model_validation_due_date` (model compliance deadline)
    - `validation_team_sla_due_date` (team performance deadline)
    - Status properties: `submission_status`, `model_compliance_status`, `validation_team_sla_status`
- Update schemas (ValidationRequestResponse to include computed fields)
- Install `python-dateutil` dependency for relativedelta

**Migration**:
```python
def upgrade():
    # Only 2 new columns!
    op.add_column('validation_requests', sa.Column('prior_validation_request_id', sa.Integer(), nullable=True))
    op.add_column('validation_requests', sa.Column('submission_received_date', sa.Date(), nullable=True))

    op.create_foreign_key(
        'fk_validation_requests_prior',
        'validation_requests', 'validation_requests',
        ['prior_validation_request_id'], ['request_id'],
        ondelete='SET NULL'
    )

def downgrade():
    op.drop_constraint('fk_validation_requests_prior', 'validation_requests', type_='foreignkey')
    op.drop_column('validation_requests', 'submission_received_date')
    op.drop_column('validation_requests', 'prior_validation_request_id')
```

### Phase 2: Helper Functions

**Files**:
- `api/app/api/validation_workflow.py` - Add calculation helpers:
  - `calculate_model_revalidation_status(model, db)`
  - `get_models_needing_revalidation(db, days_ahead, include_overdue)`

### Phase 3: API Endpoints

**New Endpoints**:
- `PATCH /validation-workflow/requests/{id}/submit-documentation`
- `GET /validation-workflow/dashboard/overdue-submissions`
- `GET /validation-workflow/dashboard/overdue-validations`
- `GET /validation-workflow/dashboard/upcoming-revalidations`
- `GET /validation-workflow/my-pending-submissions`
- `GET /models/{id}/revalidation-status` - Get revalidation status for single model

### Phase 4: UI Components

**New Pages**:
- RevalidationsDashboardPage (`/revalidations-dashboard`)
- MyPendingSubmissionsPage (`/my-pending-submissions`)

**Enhanced Pages**:
- ValidationRequestDetailPage - add revalidation timeline section
- AdminDashboardPage - add revalidation widgets
- ModelDetailsPage - show revalidation status

---

## 9. Key Design Decisions

### Why Two Different "Due Dates"?

**Rationale**:
- **Model Validation Due** = Fixed compliance deadline (protects organization from risk)
- **Validation Team SLA Due** = Fair performance metric (doesn't penalize team for late submissions)
- Separates model owner accountability from validation team accountability
- Late submissions are visible but don't skew team metrics

**Calculation**:
- **Model Validation Due** = Submission Due + 3mo grace + Lead Time (FIXED)
- **Team SLA Due** = Submission Received + Lead Time (VARIABLE)

**Example**:
- Last Validation: 2024-01-01
- Frequency: 12 months → Submission Due: 2025-01-01
- Grace: 3mo → Grace End: 2025-04-01
- Lead Time: 90 days
- **Model Validation Due**: 2025-06-30 (fixed)

**Scenario A** (On-time submission 2025-01-01):
- Team SLA Due: 2025-04-01
- Team has 90 days, completes well before model due date
- Result: ✅ Submission on time, ✅ Team within SLA, ✅ Model validated on time

**Scenario B** (Late submission 2025-05-01):
- Team SLA Due: 2025-07-30 (submission + 90 days)
- Team still gets full 90 days
- But model due date remains 2025-06-30
- Result: ❌ Submission late, ✅ Team within SLA (if complete by 7/30), ❌ Model overdue (if complete after 6/30)

This design allows separate reporting:
- "X models overdue for validation" (compliance risk)
- "Y validation projects behind SLA" (team performance)

### Why 3-Month Grace Period?

**Rationale**:
- Reasonable buffer for busy model owners
- Aligns with quarterly planning cycles
- Not so long that it encourages procrastination
- Gives validation team advance notice to plan resources

**Configurable**: Could make this a policy setting if different risk tiers need different grace periods

### Why Auto-Create Requests 30 Days Before Due?

**Rationale**:
- Gives model owners advance notice
- Allows validation team to plan resource allocation
- Creates accountability (request exists = obligation visible)
- 30 days = roughly one month lead time

**Alternative Considered**: Create on due date
**Rejected Because**: No advance warning; reactive rather than proactive

---

## 10. Compliance & Audit

### Audit Trail Requirements

All revalidation lifecycle events must be logged:
- Validation request auto-creation
- Documentation submission (with date)
- Status transitions
- Deadline extensions (if admin feature added)
- Schedule updates

### Reporting Requirements

**Monthly Report**: Models Overdue for Revalidation
- Group by risk tier
- Show days overdue
- Highlight submission vs. validation delays

**Quarterly Report**: Revalidation Compliance Rate
- % of revalidations completed on time
- Average delay by risk tier
- Model owners with most overdue submissions

---

## 11. Future Enhancements

### 1. Email Notifications

**Trigger Points**:
- 30 days before submission due
- 7 days before submission due
- Day of submission due
- Entry into grace period
- End of grace period (now overdue)
- Validation due date approaching
- Validation overdue

### 2. Submission Workflow

**Enhanced Features**:
- Document upload requirement
- Checklist of required materials
- Model owner attestation
- Delegate can submit on behalf

### 3. Grace Period Extensions

**Admin Feature**:
- One-time extension of grace period
- Requires justification
- Recorded in audit log
- Notification to validation team

### 4. Revalidation Grouping

**Integration with Model Grouping**:
- If models were last validated together
- Suggest creating single revalidation request for group
- Synchronize submission due dates

---

**End of Design Document**
