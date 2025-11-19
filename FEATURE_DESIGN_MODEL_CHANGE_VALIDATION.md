# Model Change & Validation Feature Design

## Executive Summary

This document outlines the design for implementing intelligent model grouping, regional scope detection, model change tracking, and automated validation triggering in the MRM system.

**Status**: Implementation Phase - Phases 1, 2, 3, & 4 Complete (as of 2025-11-19)
**Target**: Build on existing multi-model validation foundation
**Approach**: Non-breaking, additive changes to current schema

---

## 1. Model Grouping Memory

### Objective
When creating a validation for a model, suggest including other models that were validated together previously.

### Schema Design

#### New Table: `validation_grouping_memory`

```python
class ValidationGroupingMemory(Base):
    """Tracks the most recent multi-model validation for each model."""
    __tablename__ = "validation_grouping_memory"

    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("models.model_id", ondelete="CASCADE"),
        primary_key=True
    )
    last_validation_request_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("validation_requests.request_id", ondelete="CASCADE"),
        nullable=False
    )
    grouped_model_ids: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )  # JSON array: [2, 5, 8]
    is_regular_validation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )  # True for regular revalidations, False for targeted/change-driven
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    model = relationship("Model")
    last_validation = relationship("ValidationRequest")
```

**Key Behaviors**:
- One row per model_id (primary key)
- Only stores the MOST RECENT multi-model validation
- If a model is validated alone, no row is created/row is deleted
- **ONLY updated for regular validations** (validation_type = Annual Review, Comprehensive, etc.)
- **NOT updated for targeted validations** (validation_type = Targeted Review, triggered by model changes)
- Updated automatically when validation request reaches "Approved" status

### API Endpoints

#### GET `/models/{model_id}/validation-suggestions`

**Response**:
```json
{
  "model_id": 42,
  "model_name": "Credit Risk Scorecard v2",
  "suggestions": {
    "grouped_models": [
      {
        "model_id": 43,
        "model_name": "Credit Risk Scorecard v1",
        "last_validated_together": "2025-01-15",
        "validation_request_id": 123
      },
      {
        "model_id": 44,
        "model_name": "Credit Risk PD Model",
        "last_validated_together": "2025-01-15",
        "validation_request_id": 123
      }
    ],
    "suggested_regions": [
      {
        "region_id": 1,
        "region_code": "US",
        "region_name": "United States",
        "source": "from_model_42"
      },
      {
        "region_id": 2,
        "region_code": "UK",
        "region_name": "United Kingdom",
        "source": "from_model_43"
      }
    ]
  }
}
```

### UI Implementation

**Location**: ValidationWorkflowPage - Create New Validation form

**Behavior**:
1. When user selects first model from dropdown
2. Auto-fetch suggestions via API
3. Display info box if grouping suggestions exist:

```
ℹ️ This model was last validated with:
  • Credit Risk Scorecard v1
  • Credit Risk PD Model

[Include these models?] [No, validate alone]
```

4. If user clicks "Include these models", auto-populate model_ids multiselect

---

## 2. Regional Approval Configuration

### Objective
Configure which regions require regional approver sign-off vs. which can be approved by global approvers.

### Schema Design

#### Enhancement to `regions` Table

```python
# Add to Region model:
requires_regional_approval: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=False
)  # If True, validations affecting this region require regional approver
```

### UI Implementation

**Location**: RegionsPage - Add checkbox column "Requires Regional Approval"

**Behavior**:
- Admin can toggle per region
- Used during approver assignment logic

---

## 3. Validation Request Lifecycle Enhancements

### Admin Decline Validation Request

#### New API Endpoint: PATCH `/validation-workflow/requests/{id}/decline`

**Request**:
```json
{
  "decline_reason": "Minor documentation update, validation not required"
}
```

**Response**:
```json
{
  "request_id": 42,
  "status": "Cancelled",
  "declined_by": "Admin User",
  "decline_reason": "Minor documentation update, validation not required",
  "declined_at": "2025-01-20T15:30:00Z"
}
```

**Business Logic**:
- Only available to Admin users
- Changes status to "Cancelled"
- Records decline reason in audit log
- Notifies requestor

### Admin Unlink Regional Approval (Unblock Stalled Validation)

#### New API Endpoint: DELETE `/validation-workflow/approvals/{approval_id}/unlink`

**Request**:
```json
{
  "unlink_reason": "Regional approver unavailable, proceeding with global approval only"
}
```

**Response**:
```json
{
  "approval_id": 15,
  "status": "Removed",
  "unlinked_by": "Admin User",
  "unlink_reason": "Regional approver unavailable, proceeding with global approval only",
  "unlinked_at": "2025-01-20T16:00:00Z"
}
```

**Business Logic**:
- Only available to Admin users
- Removes the approval requirement
- Audit logs the action
- Validation can proceed without this approval

---

## 4. Regional Scope Intelligence

### Objective
Automatically suggest all regions from all selected models as the default validation scope.

### Implementation (No Schema Changes)

**API Logic** (in validation creation endpoint):

```python
def compute_suggested_regions(model_ids: List[int], db: Session) -> List[int]:
    """Compute union of all regions from selected models."""
    # Get all model-region links for selected models
    model_regions = db.query(ModelRegion).filter(
        ModelRegion.model_id.in_(model_ids)
    ).all()

    # Extract unique region IDs
    region_ids = list(set(mr.region_id for mr in model_regions))

    return region_ids
```

### API Endpoint Enhancement

#### POST `/validation-workflow/requests/preview`

**Request**:
```json
{
  "model_ids": [42, 43, 44]
}
```

**Response**:
```json
{
  "suggested_regions": [
    {"region_id": 1, "code": "US", "name": "United States"},
    {"region_id": 2, "code": "UK", "name": "United Kingdom"},
    {"region_id": 3, "code": "EU", "name": "European Union"}
  ],
  "suggested_approvers": [
    {
      "user_id": 10,
      "full_name": "Global Approver",
      "role": "Global Approver",
      "reason": "Validation spans multiple regions"
    },
    {
      "user_id": 11,
      "full_name": "US Regional Approver",
      "role": "Regional Approver",
      "regions": ["US"],
      "reason": "US region is in scope"
    }
  ]
}
```

### UI Enhancement

**ValidationWorkflowPage**:

When user selects multiple models:
1. Call preview API
2. Display suggested regions with ALL checkboxes checked by default
3. User can uncheck regions to narrow scope
4. Display suggested approvers as read-only info (approvers auto-assigned on submit)

---

## 3. Model Change & Version Management

### Objective
Track model changes as first-class entities that automatically trigger validation requests.

### Schema Design

#### New Table: `model_changes`

```python
class ModelChange(Base):
    """Records a model change that triggers validation."""
    __tablename__ = "model_changes"

    change_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("models.model_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("model_versions.version_id", ondelete="CASCADE"),
        nullable=False
    )
    change_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("model_change_types.change_type_id"),
        nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Regional Scope
    scope: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )  # GLOBAL or REGIONAL
    affected_region_ids: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )  # JSON array: [1, 2, 3] for regional changes

    # Timeline
    planned_production_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_production_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Audit
    created_by_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    # Validation Link
    validation_request_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("validation_requests.request_id", ondelete="SET NULL"),
        nullable=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING_VALIDATION"
    )  # PENDING_VALIDATION | VALIDATED | DEPLOYED | CANCELLED

    # Relationships
    model = relationship("Model", back_populates="changes")
    version = relationship("ModelVersion")
    change_type = relationship("ModelChangeType")
    created_by = relationship("User")
    validation_request = relationship("ValidationRequest")
```

#### Enhancement to `model_regions` Table

Add fields to track regional version deployments:

```python
# Add to ModelRegion model:
current_version_id: Mapped[Optional[int]] = mapped_column(
    Integer,
    ForeignKey("model_versions.version_id", ondelete="SET NULL"),
    nullable=True
)
deployed_at: Mapped[Optional[datetime]] = mapped_column(
    DateTime,
    nullable=True
)
deployment_notes: Mapped[Optional[str]] = mapped_column(
    Text,
    nullable=True
)
```

### API Endpoints

#### POST `/models/{model_id}/changes`

**Request**:
```json
{
  "version_number": "2.1.0",
  "change_type_id": 5,
  "description": "Updated credit score thresholds based on recent data",
  "scope": "REGIONAL",
  "affected_region_ids": [1, 2],
  "planned_production_date": "2025-05-01",
  "auto_create_validation": true
}
```

**Response**:
```json
{
  "change_id": 42,
  "model_id": 10,
  "version_id": 103,
  "scope": "REGIONAL",
  "affected_regions": [
    {"region_id": 1, "code": "US"},
    {"region_id": 2, "code": "UK"}
  ],
  "planned_production_date": "2025-05-01",
  "validation_request": {
    "request_id": 456,
    "status": "Intake",
    "target_completion_date": "2025-04-21"
  },
  "created_at": "2025-01-20T10:30:00Z"
}
```

**Business Logic**:
1. Create new ModelVersion record with status=DRAFT
2. Create ModelChange record
3. If `auto_create_validation=true`:
   - Calculate target_completion_date = planned_production_date - lead_time (from SLA config)
   - Create ValidationRequest with:
     - model_ids: [model_id]
     - region_id: first affected region if scope=REGIONAL, null if GLOBAL
     - trigger_reason: "Model change planned for production on {date}"
     - Auto-assign appropriate approvers based on scope
4. Return complete change record with validation details

#### GET `/models/{model_id}/regional-versions`

**Response**:
```json
{
  "model_id": 10,
  "model_name": "Credit Risk Scorecard",
  "global_version": {
    "version_id": 101,
    "version_number": "2.0.0",
    "status": "ACTIVE",
    "production_date": "2024-11-01"
  },
  "regional_versions": [
    {
      "region_id": 1,
      "region_code": "US",
      "region_name": "United States",
      "current_version_id": 101,
      "version_number": "2.0.0",
      "deployed_at": "2024-11-01T08:00:00Z",
      "is_same_as_global": true
    },
    {
      "region_id": 2,
      "region_code": "UK",
      "region_name": "United Kingdom",
      "current_version_id": 102,
      "version_number": "1.9.5",
      "deployed_at": "2024-10-15T08:00:00Z",
      "is_same_as_global": false,
      "deployment_notes": "UK regulators require additional documentation before v2.0 deployment"
    }
  ]
}
```

### UI Components

#### 1. New Page: ModelChangeRecordPage

**Route**: `/models/:id/record-change`

**Features**:
- Form to record model change
- Change type dropdown (from ModelChangeType taxonomy)
- Version number input
- Description textarea
- Scope selector (Global / Regional)
- If Regional: Region checkboxes (multi-select)
- Planned production date picker
- Checkbox: "Automatically create validation request"
- Submit creates change record and optionally validation request

#### 2. Enhancement: ModelDetailsPage

**New Section**: "Version Deployments"

**Display**:
- Table showing current version per region
- Highlight regional overrides (different from global version)
- Button: "Record New Change"

---

## 6. Smart Approver Assignment

### Objective
Automatically assign required approvers based on validation scope and regional configuration.

### Implementation (Uses Regional Approval Configuration)

**Business Rules**:

1. **Global Validations** (region_id is NULL):
   - Require: Global Approver

2. **Regional Validations** (region_id is set):
   - If `region.requires_regional_approval == True`:
     - Require: Regional Approver for that specific region
   - Else:
     - Require: Global Approver

3. **Multi-Region Validations** (affects multiple regions in trigger_reason/model changes):
   - For each affected region where `requires_regional_approval == True`:
     - Require: Regional Approver for that region
   - Always require: Global Approver as fallback/coordinator

### API Logic

```python
def auto_assign_approvers(
    validation_request: ValidationRequest,
    db: Session
) -> List[ValidationApproval]:
    """Auto-create approval requirements based on scope."""
    approvals = []

    # Determine scope
    if validation_request.region_id is None:
        # Global validation - need global approver
        global_approvers = db.query(User).filter(
            User.role == UserRole.GLOBAL_APPROVER
        ).all()

        for approver in global_approvers:
            approvals.append(ValidationApproval(
                request_id=validation_request.request_id,
                approver_id=approver.user_id,
                approver_role="Global Approver",
                is_required=True,
                approval_status="Pending"
            ))

    else:
        # Regional validation - need regional approver for that region
        regional_approvers = db.query(User).join(user_regions).filter(
            User.role == UserRole.REGIONAL_APPROVER,
            user_regions.c.region_id == validation_request.region_id
        ).all()

        for approver in regional_approvers:
            approvals.append(ValidationApproval(
                request_id=validation_request.request_id,
                approver_id=approver.user_id,
                approver_role="Regional Approver",
                is_required=True,
                approval_status="Pending"
            ))

    # Add model owner approval if high risk
    if is_high_risk(validation_request.models):
        for model in validation_request.models:
            approvals.append(ValidationApproval(
                request_id=validation_request.request_id,
                approver_id=model.owner_id,
                approver_role="Model Owner",
                is_required=True,
                approval_status="Pending"
            ))

    return approvals
```

**Integration Point**: Called automatically in `create_validation_request` endpoint after creating the ValidationRequest record.

---

## 7. Per-Risk-Tier Lead Times

### Objective
Calculate validation target completion dates based on model risk tier, not a global SLA.

### Schema Design

#### Enhancement to `validation_policies` Table

```python
# Add to ValidationPolicy model:
model_change_lead_time_days: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=90
)  # Days before production date that validation must be complete
```

**Current Table Structure**:
- `policy_id` (PK)
- `risk_tier_id` (FK to TaxonomyValue) - Unique constraint
- `frequency_months` - Existing field for regular revalidation frequency
- `model_change_lead_time_days` - NEW field

### API Logic

```python
def calculate_target_completion_date(
    model: Model,
    planned_production_date: date,
    db: Session
) -> date:
    """Calculate target completion date based on model's risk tier."""
    # Get validation policy for this model's risk tier
    policy = db.query(ValidationPolicy).filter(
        ValidationPolicy.risk_tier_id == model.risk_tier_id
    ).first()

    if not policy:
        # Fallback to global SLA if no policy configured
        sla = db.query(ValidationWorkflowSLA).filter(
            ValidationWorkflowSLA.workflow_type == "Validation"
        ).first()
        lead_time_days = sla.model_change_lead_time if sla else 90
    else:
        lead_time_days = policy.model_change_lead_time_days

    # Target = production date - lead time
    from datetime import timedelta
    return planned_production_date - timedelta(days=lead_time_days)
```

### UI Enhancement

**Location**: Workflow Configuration Page (existing) or Taxonomy Page (for Risk Tier values)

**New Section**: "Validation Lead Times by Risk Tier"

| Risk Tier | Regular Revalidation (months) | Model Change Lead Time (days) |
|-----------|-------------------------------|-------------------------------|
| Tier 1 (High) | 12 | 120 |
| Tier 2 (Medium) | 18 | 90 |
| Tier 3 (Low) | 24 | 60 |

---

## 8. Model Owner Ratification of Version Deployments

### Objective
Require Model Owners (or delegates) to confirm when a model version actually reaches production.

### Schema Design

#### New Table: `version_deployment_tasks`

```python
class VersionDeploymentTask(Base):
    """Tracks Model Owner confirmation of version deployments."""
    __tablename__ = "version_deployment_tasks"

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("model_versions.version_id", ondelete="CASCADE"),
        nullable=False
    )
    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("models.model_id", ondelete="CASCADE"),
        nullable=False
    )
    region_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("regions.region_id", ondelete="CASCADE"),
        nullable=True
    )  # NULL for global deployment

    # Task details
    planned_production_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_production_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Assignment
    assigned_to_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False
    )  # Model Owner or delegate

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING"
    )  # PENDING | CONFIRMED | ADJUSTED | CANCELLED

    confirmation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    confirmed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    # Relationships
    version = relationship("ModelVersion")
    model = relationship("Model")
    region = relationship("Region")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    confirmed_by = relationship("User", foreign_keys=[confirmed_by_id])
```

### API Endpoints

#### POST `/version-deployment-tasks/` (Auto-created when version reaches production_date)

#### GET `/version-deployment-tasks/my-tasks` (For Model Owners)

**Response**:
```json
[
  {
    "task_id": 10,
    "model_name": "Credit Risk Scorecard",
    "version_number": "2.1.0",
    "region": "US",
    "planned_production_date": "2025-03-01",
    "days_until_due": -5,
    "status": "PENDING",
    "assigned_to": "Model Owner Name"
  }
]
```

#### PATCH `/version-deployment-tasks/{task_id}/confirm`

**Request**:
```json
{
  "actual_production_date": "2025-03-01",
  "confirmation_notes": "Deployed to production at 08:00 UTC"
}
```

**Response**:
```json
{
  "task_id": 10,
  "status": "CONFIRMED",
  "actual_production_date": "2025-03-01",
  "confirmed_at": "2025-03-01T09:30:00Z"
}
```

**Side Effects**:
- Updates `model_versions.production_date` if adjusted
- Updates `model_regions.current_version_id` and `deployed_at`
- Sends confirmation to validation team

### UI Implementation

**New Page**: MyDeploymentTasksPage

**Route**: `/my-deployment-tasks`

**Features**:
- Table of pending deployment tasks
- Confirm/Adjust production date
- Enter confirmation notes
- Mark as completed

---

## 9. Conditional Auto-Validation Based on Change Type

### Objective
Skip auto-validation for model changes that don't require approval (e.g., documentation updates).

### Implementation (Uses Existing Schema)

**Existing Table**: `model_change_types`
- Field: `requires_mv_approval` (Boolean)

### API Logic Enhancement

```python
def create_model_change(
    model_id: int,
    change_data: ModelChangeCreate,
    db: Session
) -> ModelChange:
    """Create model change and conditionally create validation."""

    # Get change type
    change_type = db.query(ModelChangeType).filter(
        ModelChangeType.change_type_id == change_data.change_type_id
    ).first()

    # Create the change record
    model_change = ModelChange(...)
    db.add(model_change)
    db.flush()

    # Only auto-create validation if change type requires approval
    if change_type.requires_mv_approval and change_data.auto_create_validation:
        validation_request = create_validation_from_change(
            model_change, db
        )
        model_change.validation_request_id = validation_request.request_id

    db.commit()
    return model_change
```

### UI Enhancement

**Location**: ModelChangeRecordPage

**Conditional Display**:
```typescript
// Show auto-validation checkbox only if change type requires approval
{selectedChangeType?.requires_mv_approval && (
  <label>
    <input type="checkbox" checked={autoCreateValidation} />
    Automatically create validation request
  </label>
)}

{!selectedChangeType?.requires_mv_approval && (
  <div className="text-sm text-gray-600">
    ℹ️ This change type does not require validation
  </div>
)}
```

---

## 10. Migration Plan

### Phase 1: Model Grouping Memory

**Files**:
- `api/app/models/validation_grouping.py` - New model
- Migration: `add_validation_grouping_memory.py`
- `api/app/api/validation_workflow.py` - Update create endpoint to populate grouping memory
- `api/app/api/models.py` - Add `/models/{id}/validation-suggestions` endpoint
- `web/src/pages/ValidationWorkflowPage.tsx` - Add grouping suggestions UI

**Testing**:
1. Create multi-model validation request
2. Mark it as Approved
3. Verify grouping_memory table populated
4. Create new validation for one of the models
5. Verify suggestions appear

### Phase 2: Regional Scope Intelligence

**Files**:
- `api/app/api/validation_workflow.py` - Add `/requests/preview` endpoint
- `web/src/pages/ValidationWorkflowPage.tsx` - Call preview API when models selected
- Update form to show suggested regions with all checked

**Testing**:
1. Select models from different regions
2. Verify all regions appear as suggestions
3. Verify all checkboxes checked by default
4. Uncheck some regions, submit
5. Verify validation created with selected scope

### Phase 3: Model Change Tracking

**Files**:
- `api/app/models/model_change.py` - New ModelChange model
- `api/app/models/model_region.py` - Add version deployment fields
- Migration: `add_model_change_tracking.py`
- `api/app/api/model_changes.py` - New router for change endpoints
- `web/src/pages/ModelChangeRecordPage.tsx` - New page for recording changes
- `web/src/pages/ModelDetailsPage.tsx` - Add version deployments section

**Testing**:
1. Record a global model change
2. Verify validation request auto-created
3. Verify target date = production_date - lead_time
4. Record regional change
5. Verify only affected regions in validation scope

### Phase 4: Smart Approver Assignment

**Files**:
- `api/app/api/validation_workflow.py` - Add auto_assign_approvers function
- Call from create_validation_request endpoint
- Update to populate ValidationApproval records automatically

**Testing**:
1. Create global validation
2. Verify Global Approver assigned
3. Create regional validation for US
4. Verify US Regional Approver assigned
5. Create validation affecting US + UK
6. Verify both regional approvers assigned

---

## 11. Implementation Status

### ✅ Phase 1: Model Grouping Memory (COMPLETED - 2025-11-19)

**Completed Work**:
- ✅ Created `ValidationGroupingMemory` model ([api/app/models/validation_grouping.py](api/app/models/validation_grouping.py))
- ✅ Created database migration `c1f27142d859_add_validation_grouping_memory`
- ✅ Added API endpoint `GET /models/{model_id}/validation-suggestions` ([api/app/api/models.py:203-266](api/app/api/models.py#L203-L266))
- ✅ Added `update_grouping_memory()` helper function to populate memory on validation creation ([api/app/api/validation_workflow.py:134-183](api/app/api/validation_workflow.py#L134-L183))
- ✅ Updated ValidationWorkflowPage UI to show grouping suggestions ([web/src/pages/ValidationWorkflowPage.tsx](web/src/pages/ValidationWorkflowPage.tsx))

**Key Features Delivered**:
- System tracks most recent multi-model validation for each model
- Only regular validations (INITIAL, ANNUAL, COMPREHENSIVE, ONGOING) update grouping memory
- Targeted validations (TARGETED, INTERIM) are excluded
- Suggestions appear when selecting a single model for validation
- Users can add suggested models individually or all at once

**Ready for Testing**:
1. Create multi-model validation request with regular validation type
2. System automatically populates grouping_memory table
3. Create new validation, select one of those models
4. Verify suggestions appear with "Add" and "Add All" buttons

### ✅ Phase 2: Regional Approval Configuration (COMPLETED - 2025-11-19)

**Completed Work**:
- ✅ Added `requires_regional_approval` boolean to Region model ([api/app/models/region.py](api/app/models/region.py))
- ✅ Updated Region schemas to include new field ([api/app/schemas/region.py](api/app/schemas/region.py))
- ✅ Created database migration `f1cc30cb20bf_add_requires_regional_approval_to_`
- ✅ Updated RegionsPage UI with checkbox toggle ([web/src/pages/RegionsPage.tsx](web/src/pages/RegionsPage.tsx))
- ✅ Added "Approval Required" column to regions table display

**Key Features Delivered**:
- Admin can configure which regions require regional approver sign-off
- Default value is `false` for all regions
- UI shows clear Yes/No badge in regions table
- Checkbox in form with helpful description text
- Ready for use in approver assignment logic (Phase 5)

### ✅ Phase 3: Validation Request Lifecycle Enhancements (COMPLETED - 2025-11-19)

**Completed Work**:
- ✅ Added decline fields to ValidationRequest model ([api/app/models/validation.py:87-91](api/app/models/validation.py#L87-L91))
- ✅ Added unlink fields to ValidationApproval model ([api/app/models/validation.py:295-300](api/app/models/validation.py#L295-L300))
- ✅ Created database migration `033fd221e8cf_add_decline_and_unlink_fields_for_phase_`
- ✅ Implemented `PATCH /validation-workflow/requests/{id}/decline` endpoint ([api/app/api/validation_workflow.py:535-606](api/app/api/validation_workflow.py#L535-L606))
- ✅ Implemented `DELETE /validation-workflow/approvals/{id}/unlink` endpoint ([api/app/api/validation_workflow.py:1380-1426](api/app/api/validation_workflow.py#L1380-L1426))
- ✅ Added ValidationRequestDecline and ValidationApprovalUnlink schemas
- ✅ Created comprehensive test suite (6 tests)

**Key Features Delivered**:
- Admin-only decline validation endpoint that sets status to CANCELLED
- Admin-only unlink approval endpoint that marks approval as "Removed" and not required
- Both endpoints create comprehensive audit logs with reason tracking
- Declined validations track who declined, when, and why
- Unlinked approvals track who unlinked, when, and why
- Full validation request and approval tracking for compliance

### ✅ Phase 4: Regional Scope Intelligence (COMPLETED - 2025-11-19)

**Implementation Summary**:
- Added `compute_suggested_regions()` helper function in [validation_workflow.py](api/app/api/validation_workflow.py:188-215)
- Created `/validation-workflow/requests/preview-regions` GET endpoint to compute union of regions from selected models
- Updated [ValidationWorkflowPage.tsx](web/src/pages/ValidationWorkflowPage.tsx:187-208) with region suggestions useEffect hook
- UI displays suggested regions with "Approval Required" badges for regions requiring regional approval
- Users can click "Select" to choose a suggested region for the validation

**Backend Tests** (8 tests - all passing):
- Added to [test_validation_workflow.py](api/tests/test_validation_workflow.py:1600-1806)
- Tests cover single model, multiple models, overlapping regions, models without regions, mixed scenarios, and error cases
- All 8 tests passing ✅

**Frontend Integration Tests** (13 tests - all passing):
- Added [ValidationWorkflowPage.test.tsx](web/src/pages/ValidationWorkflowPage.test.tsx)
- Test categories: Initial State (3), API Integration (2), Form Structure (2), Data Loading (3), Form Validation (1), Accessibility (2)
- Tests verify: loading states, API calls, region dropdown population, error handling, form validation, accessibility
- All 13 tests passing ✅

### 🔄 Phase 5: Smart Approver Assignment (PENDING)

**Planned Work**:
- Auto-assign approvers based on validation scope
- Use regional approval configuration
- Create ValidationApproval records automatically

### 🔄 Phase 6: Per-Risk-Tier Lead Times (PENDING)

**Planned Work**:
- Add `model_change_lead_time_days` to ValidationPolicy
- Calculate target dates based on risk tier
- Admin UI for configuring lead times

### 🔄 Phase 7: Model Change Tracking (PENDING)

**Planned Work**:
- ModelChange and VersionDeploymentTask tables
- Auto-create validation from model changes
- Regional version management

### 🔄 Phase 8: Model Owner Deployment Ratification (PENDING)

**Planned Work**:
- VersionDeploymentTask workflow
- Model owner confirmation UI
- Update model_regions on confirmation

### 🔄 Phase 9: Conditional Auto-Validation (PENDING)

**Planned Work**:
- Skip auto-validation for changes not requiring approval
- Use existing `requires_mv_approval` field
- Conditional UI display

---

## 6. Backward Compatibility

**Guaranteed Non-Breaking**:
- All new fields are nullable or have defaults
- Existing validations continue to work without grouping suggestions
- Manual approver assignment still possible
- Model versions work without change records
- Regional deployments optional (defaults to global version)

**Data Migration**:
- No need to backfill grouping_memory for historical validations
- Existing model_regions rows get current_version_id=NULL (meaning "use global version")
- Existing validations without approvals can be left as-is

---

## 7. Future Enhancements (Out of Scope for MVP)

1. **Lead-Time Notifications**:
   - Email alerts when model change approaching production without validation
   - Dashboard widget for "Changes at Risk"

2. **Field-Level Change Tracking**:
   - Track which specific model fields changed
   - Store before/after values
   - More granular change impact analysis

3. **Conditional Approval Rules**:
   - "Risk Officer approval required only if change is MAJOR"
   - "Model Owner approval waived for MINOR documentation changes"

4. **Approval Escalation**:
   - Auto-escalate if approval pending > X days
   - Notify approval manager

5. **Version Comparison View**:
   - Side-by-side diff of model versions
   - Highlight changed fields

---

## 8. Key Design Decisions

### Why Only Store Most Recent Grouping?

**Rationale**:
- Simplicity - avoid complex history management
- Most relevant - recent groupings most likely still applicable
- Performance - single lookup, no sorting
- Storage - minimal footprint

**Alternative Considered**: Store full grouping history
**Rejected Because**: Added complexity with minimal benefit; if groupings change frequently, older history becomes noise

### Why Union (Not Intersection) of Regions?

**Rationale**:
- Conservative approach - suggest broadest possible scope
- Users can easily narrow by unchecking regions
- Prevents accidentally omitting critical regions
- Aligns with risk-averse compliance mindset

**Alternative Considered**: Intersection (only common regions)
**Rejected Because**: Could result in empty set; users would need to manually discover missing regions

### Why Auto-Create Validation on Model Change?

**Rationale**:
- Ensures compliance - no changes slip through
- Reduces manual overhead
- Enforces lead-time discipline
- Audit trail - every change links to validation

**Alternative Considered**: Make validation creation optional
**Current Design**: Optional via `auto_create_validation` flag, but defaults to true

### Why Store Version Per Region in model_regions?

**Rationale**:
- Flexibility - regions can deploy at different paces
- Regulatory support - some jurisdictions have longer approval cycles
- Rollback capability - can revert specific regions independently
- Audit trail - know exactly when each region deployed each version

**Alternative Considered**: Single global version with override flags
**Rejected Because**: Doesn't handle multi-region deployments clearly; ambiguous state representation

---

## 9. API Summary Reference

### New Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/models/{id}/validation-suggestions` | Get grouping and region suggestions |
| POST | `/validation-workflow/requests/preview` | Preview suggested regions and approvers |
| POST | `/models/{id}/changes` | Record model change (auto-creates validation) |
| GET | `/models/{id}/changes` | List all changes for a model |
| GET | `/models/{id}/changes/{change_id}` | Get specific change details |
| PATCH | `/models/{id}/changes/{change_id}` | Update change (e.g., actual production date) |
| GET | `/models/{id}/regional-versions` | Get version deployments by region |
| POST | `/models/{id}/regional-versions/deploy` | Deploy version to specific regions |

### Enhanced Endpoints

| Method | Path | Enhancement |
|--------|------|-------------|
| POST | `/validation-workflow/requests/` | Auto-assigns approvers based on scope |

---

## 10. UI Component Summary

### New Components

1. **ValidationGroupingSuggestion** (component)
   - Props: `modelId`, `onAccept`, `onDecline`
   - Displays suggested models from last validation
   - Inline in ValidationWorkflowPage form

2. **RegionalScopeSelector** (component)
   - Props: `modelIds`, `selectedRegionIds`, `onChange`
   - Computes union of regions from models
   - Multi-checkbox UI with all checked by default

3. **ModelChangeRecordPage** (page)
   - Route: `/models/:id/record-change`
   - Full form for recording changes
   - Auto-creates validation option

4. **RegionalVersionsTable** (component)
   - Props: `modelId`
   - Displays version per region
   - Highlights regional overrides
   - Used in ModelDetailsPage

### Enhanced Components

1. **ValidationWorkflowPage**
   - Integrates ValidationGroupingSuggestion
   - Uses RegionalScopeSelector
   - Shows auto-assigned approvers (read-only)

2. **ModelDetailsPage**
   - Adds "Version Deployments" section
   - Includes RegionalVersionsTable
   - "Record New Change" button

---

## Appendix: Database Schema Diagram

```
┌─────────────────┐
│ models          │
└────────┬────────┘
         │
         │ 1:N
         ▼
┌─────────────────────┐     1:N     ┌──────────────────┐
│ model_changes  [NEW]│────────────▶│ model_versions   │
└─────────┬───────────┘             └──────────────────┘
          │                                  │
          │ 1:1                              │
          ▼                                  │
┌──────────────────────┐                     │
│ validation_requests  │                     │
└──────────┬───────────┘                     │
           │ M:N                             │
           ▼                                 │
┌──────────────────────────┐                │
│ validation_request_models│                │
└──────────────────────────┘                │
                                            │
┌─────────────────┐                         │
│ model_regions   │◀────────────────────────┘
└────┬───────┬────┘      current_version_id (FK)
     │       │
     │ M:1   │ M:1
     ▼       ▼
┌─────────┐ ┌──────────────┐
│ models  │ │ regions      │
└─────────┘ └──────────────┘

┌──────────────────────────────┐
│ validation_grouping_memory   │
│ [NEW]                        │
└───────┬──────────────────────┘
        │ M:1
        ▼
┌─────────────────┐
│ models          │
└─────────────────┘
```

---

**End of Design Document**
