# Monitoring Plan Versioning & Validation Workflow Integration Sub-Plan

## Implementation Status

| Phase | Description | Status | Date |
|-------|-------------|--------|------|
| **A** | Database & Models | ✅ Complete | 2025-11-27 |
| **B** | Version CRUD API | ✅ Complete | 2025-11-27 |
| **C** | Component 9b Backend | ✅ Complete | 2025-11-27 |
| **D** | Version Management UI | ✅ Complete | 2025-11-27 |
| **E** | Component 9b UI | ✅ Complete | 2025-11-27 |
| **F** | Testing & Documentation | ⏳ Pending | - |

---

## Executive Summary

This sub-plan addresses two interconnected requirements:
1. **Monitoring Plan Versioning**: Enable tracking of monitoring plan configurations over time so cycles can be tied to specific plan versions
2. **Validation Workflow Component 9b**: Add a configurable validation component for validators to document their assessment of the model's performance monitoring plan

---

## Confirmed Design Decisions

Based on discussion, the following decisions are confirmed:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Version trigger** | Manual "Publish" action | Matches existing `ComponentDefinitionConfiguration` pattern; intentional versioning |
| **Cycle version binding** | At cycle start (DATA_COLLECTION) | Similar to ValidationPlan locking on status transition |
| **Version comparison** | Deferred; export metrics for manual comparison | Keep Phase 1 simple |
| **Metric changes with active cycles** | Allow with warning | Flexibility over strictness; warning informs user |
| **9b completion timing** | Any point, but required before Review/Approval | Flexible workflow, enforced gate at key transition |

---

## Part 1: Data Model Changes

### 1.1 Monitoring Plan Version Table

```sql
CREATE TABLE monitoring_plan_versions (
    version_id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES monitoring_plans(plan_id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,           -- Sequential per plan (1, 2, 3...)
    version_name VARCHAR(200),                 -- Optional: "Q4 2025 Threshold Update"
    description TEXT,                          -- Changelog or notes
    effective_date DATE NOT NULL,
    published_by_user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    published_at TIMESTAMP NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,   -- Latest published version for this plan

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE(plan_id, version_number)
);

CREATE INDEX idx_mpv_plan_id ON monitoring_plan_versions(plan_id);
CREATE INDEX idx_mpv_is_active ON monitoring_plan_versions(is_active);
```

### 1.2 Monitoring Plan Metric Snapshot Table

```sql
CREATE TABLE monitoring_plan_metric_snapshots (
    snapshot_id SERIAL PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES monitoring_plan_versions(version_id) ON DELETE CASCADE,

    -- Reference to original metric (may be deleted later)
    original_metric_id INTEGER,
    kpm_id INTEGER NOT NULL REFERENCES kpms(kpm_id),

    -- Snapshot of threshold configuration at this version
    yellow_min FLOAT,
    yellow_max FLOAT,
    red_min FLOAT,
    red_max FLOAT,
    qualitative_guidance TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Snapshot of KPM metadata (in case KPM changes)
    kpm_name VARCHAR(200) NOT NULL,
    kpm_category_name VARCHAR(200),
    evaluation_type VARCHAR(50) NOT NULL DEFAULT 'Quantitative',

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE(version_id, kpm_id)
);

CREATE INDEX idx_mpms_version_id ON monitoring_plan_metric_snapshots(version_id);
```

### 1.3 Update MonitoringCycle Table

```sql
ALTER TABLE monitoring_cycles
ADD COLUMN plan_version_id INTEGER REFERENCES monitoring_plan_versions(version_id) ON DELETE SET NULL,
ADD COLUMN version_locked_at TIMESTAMP,
ADD COLUMN version_locked_by_user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL;

COMMENT ON COLUMN monitoring_cycles.plan_version_id IS 'Version of monitoring plan this cycle is bound to (locked at DATA_COLLECTION start)';
COMMENT ON COLUMN monitoring_cycles.version_locked_at IS 'When the version was locked for this cycle';
```

### 1.4 Update ValidationPolicy Table

```sql
ALTER TABLE validation_policies
ADD COLUMN monitoring_plan_review_required BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN monitoring_plan_review_description TEXT;

COMMENT ON COLUMN validation_policies.monitoring_plan_review_required IS 'If true, component 9b (Performance Monitoring Plan Review) requires Planned or comment';
```

### 1.5 Update ValidationPlanComponent Table

```sql
ALTER TABLE validation_plan_components
ADD COLUMN monitoring_plan_version_id INTEGER REFERENCES monitoring_plan_versions(version_id) ON DELETE SET NULL,
ADD COLUMN monitoring_review_notes TEXT;

COMMENT ON COLUMN validation_plan_components.monitoring_plan_version_id IS 'For component 9b: which monitoring plan version was reviewed';
COMMENT ON COLUMN validation_plan_components.monitoring_review_notes IS 'For component 9b: notes about the monitoring plan review';
```

---

## Part 2: SQLAlchemy Models

### 2.1 MonitoringPlanVersion Model

```python
# In api/app/models/monitoring.py

class MonitoringPlanVersion(Base):
    """Version snapshot of a monitoring plan's metric configuration."""
    __tablename__ = "monitoring_plan_versions"

    version_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("monitoring_plans.plan_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    published_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint('plan_id', 'version_number', name='uq_plan_version'),
    )

    # Relationships
    plan: Mapped["MonitoringPlan"] = relationship(
        "MonitoringPlan", back_populates="versions"
    )
    published_by: Mapped[Optional["User"]] = relationship("User")
    metric_snapshots: Mapped[List["MonitoringPlanMetricSnapshot"]] = relationship(
        "MonitoringPlanMetricSnapshot", back_populates="version",
        cascade="all, delete-orphan"
    )
    cycles: Mapped[List["MonitoringCycle"]] = relationship(
        "MonitoringCycle", back_populates="plan_version"
    )


class MonitoringPlanMetricSnapshot(Base):
    """Snapshot of a metric's configuration at a specific plan version."""
    __tablename__ = "monitoring_plan_metric_snapshots"

    snapshot_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("monitoring_plan_versions.version_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    original_metric_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    kpm_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("kpms.kpm_id"), nullable=False
    )

    # Threshold snapshot
    yellow_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    yellow_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    red_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    red_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    qualitative_guidance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # KPM metadata snapshot
    kpm_name: Mapped[str] = mapped_column(String(200), nullable=False)
    kpm_category_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    evaluation_type: Mapped[str] = mapped_column(String(50), nullable=False, default="Quantitative")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint('version_id', 'kpm_id', name='uq_version_kpm'),
    )

    # Relationships
    version: Mapped["MonitoringPlanVersion"] = relationship(
        "MonitoringPlanVersion", back_populates="metric_snapshots"
    )
    kpm: Mapped["Kpm"] = relationship("Kpm")
```

### 2.2 Update MonitoringPlan Model

```python
# Add to MonitoringPlan class:
versions: Mapped[List["MonitoringPlanVersion"]] = relationship(
    "MonitoringPlanVersion", back_populates="plan",
    cascade="all, delete-orphan",
    order_by="desc(MonitoringPlanVersion.version_number)"
)
```

### 2.3 Update MonitoringCycle Model

```python
# Add to MonitoringCycle class:
plan_version_id: Mapped[Optional[int]] = mapped_column(
    Integer, ForeignKey("monitoring_plan_versions.version_id", ondelete="SET NULL"),
    nullable=True, index=True
)
version_locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
version_locked_by_user_id: Mapped[Optional[int]] = mapped_column(
    Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
)

# Add relationships:
plan_version: Mapped[Optional["MonitoringPlanVersion"]] = relationship(
    "MonitoringPlanVersion", back_populates="cycles"
)
version_locked_by: Mapped[Optional["User"]] = relationship(
    "User", foreign_keys=[version_locked_by_user_id]
)
```

---

## Part 3: Business Logic

### 3.1 Publish New Version

```python
def publish_monitoring_plan_version(
    db: Session,
    plan_id: int,
    version_name: Optional[str],
    description: Optional[str],
    effective_date: date,
    current_user: User
) -> MonitoringPlanVersion:
    """
    Publish a new version of the monitoring plan.
    Snapshots all current active metrics with their thresholds.
    """
    plan = db.query(MonitoringPlan).filter(
        MonitoringPlan.plan_id == plan_id
    ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Get next version number
    max_version = db.query(func.max(MonitoringPlanVersion.version_number)).filter(
        MonitoringPlanVersion.plan_id == plan_id
    ).scalar() or 0

    new_version_number = max_version + 1

    # Deactivate previous active version
    db.query(MonitoringPlanVersion).filter(
        MonitoringPlanVersion.plan_id == plan_id,
        MonitoringPlanVersion.is_active == True
    ).update({"is_active": False})

    # Create new version
    new_version = MonitoringPlanVersion(
        plan_id=plan_id,
        version_number=new_version_number,
        version_name=version_name or f"Version {new_version_number}",
        description=description,
        effective_date=effective_date,
        published_by_user_id=current_user.user_id,
        is_active=True
    )
    db.add(new_version)
    db.flush()

    # Snapshot all active metrics
    active_metrics = db.query(MonitoringPlanMetric).options(
        joinedload(MonitoringPlanMetric.kpm).joinedload(Kpm.category)
    ).filter(
        MonitoringPlanMetric.plan_id == plan_id,
        MonitoringPlanMetric.is_active == True
    ).all()

    for metric in active_metrics:
        snapshot = MonitoringPlanMetricSnapshot(
            version_id=new_version.version_id,
            original_metric_id=metric.metric_id,
            kpm_id=metric.kpm_id,
            yellow_min=metric.yellow_min,
            yellow_max=metric.yellow_max,
            red_min=metric.red_min,
            red_max=metric.red_max,
            qualitative_guidance=metric.qualitative_guidance,
            sort_order=metric.sort_order,
            is_active=metric.is_active,
            kpm_name=metric.kpm.name,
            kpm_category_name=metric.kpm.category.name if metric.kpm.category else None,
            evaluation_type=metric.kpm.evaluation_type or "Quantitative"
        )
        db.add(snapshot)

    # Audit log
    create_audit_log(
        db=db,
        entity_type="MonitoringPlanVersion",
        entity_id=new_version.version_id,
        action="PUBLISH",
        user_id=current_user.user_id,
        changes={
            "plan_id": plan_id,
            "plan_name": plan.name,
            "version_number": new_version_number,
            "version_name": new_version.version_name,
            "metrics_count": len(active_metrics)
        }
    )

    return new_version
```

### 3.2 Lock Cycle to Version (on start)

```python
def start_monitoring_cycle(
    db: Session,
    cycle_id: int,
    current_user: User
) -> MonitoringCycle:
    """
    Start a monitoring cycle (PENDING -> DATA_COLLECTION).
    Locks the cycle to the current active plan version.
    """
    cycle = db.query(MonitoringCycle).filter(
        MonitoringCycle.cycle_id == cycle_id
    ).first()

    if cycle.status != MonitoringCycleStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail="Can only start a cycle in PENDING status"
        )

    # Get active version for this plan
    active_version = db.query(MonitoringPlanVersion).filter(
        MonitoringPlanVersion.plan_id == cycle.plan_id,
        MonitoringPlanVersion.is_active == True
    ).first()

    if not active_version:
        raise HTTPException(
            status_code=400,
            detail="No published version exists for this plan. Please publish a version first."
        )

    # Lock cycle to version
    cycle.plan_version_id = active_version.version_id
    cycle.version_locked_at = datetime.utcnow()
    cycle.version_locked_by_user_id = current_user.user_id
    cycle.status = MonitoringCycleStatus.DATA_COLLECTION.value

    # Audit log
    create_audit_log(
        db=db,
        entity_type="MonitoringCycle",
        entity_id=cycle_id,
        action="START",
        user_id=current_user.user_id,
        changes={
            "status": {"old": "PENDING", "new": "DATA_COLLECTION"},
            "plan_version_id": active_version.version_id,
            "version_number": active_version.version_number,
            "version_name": active_version.version_name
        }
    )

    return cycle
```

### 3.3 Warn on Metric Changes with Active Cycles

```python
def check_active_cycles_warning(db: Session, plan_id: int) -> Optional[dict]:
    """
    Check if there are active cycles that would not be affected by metric changes.
    Returns warning info if applicable.
    """
    active_statuses = [
        MonitoringCycleStatus.DATA_COLLECTION.value,
        MonitoringCycleStatus.UNDER_REVIEW.value,
        MonitoringCycleStatus.PENDING_APPROVAL.value
    ]

    active_cycles = db.query(MonitoringCycle).filter(
        MonitoringCycle.plan_id == plan_id,
        MonitoringCycle.status.in_(active_statuses),
        MonitoringCycle.plan_version_id.isnot(None)
    ).count()

    if active_cycles > 0:
        return {
            "warning": True,
            "message": f"There are {active_cycles} active cycle(s) locked to previous versions. "
                      f"Changes will only affect new cycles after a new version is published.",
            "active_cycle_count": active_cycles
        }

    return None
```

### 3.4 Component 9b Validation Logic

```python
def validate_monitoring_review_component(
    db: Session,
    component: ValidationPlanComponent,
    validation_request: ValidationRequest,
    target_status_code: str
) -> None:
    """
    Validate component 9b (Performance Monitoring Plan Review) before status transition.
    Called when transitioning to REVIEW or PENDING_APPROVAL.
    """
    # Only validate if this is component 9b
    if component.component_definition.component_code != "9b":
        return

    # Get the model(s) for this validation
    models = validation_request.models
    if not models:
        return

    model = models[0]  # Primary model

    # Get policy for this risk tier
    policy = db.query(ValidationPolicy).filter(
        ValidationPolicy.risk_tier_id == model.risk_tier_id
    ).first()

    is_required = policy.monitoring_plan_review_required if policy else False

    # Get monitoring plans for this model
    monitoring_plans = db.query(MonitoringPlan).filter(
        MonitoringPlan.models.any(Model.model_id == model.model_id),
        MonitoringPlan.is_active == True
    ).all()

    has_monitoring_plan = len(monitoring_plans) > 0

    # Validation rules
    if component.planned_treatment == "Planned":
        # Must have selected a version
        if not component.monitoring_plan_version_id:
            raise HTTPException(
                status_code=400,
                detail="Component 9b: Must select a monitoring plan version when review is Planned"
            )

        # Validate version belongs to a plan covering this model
        version = db.query(MonitoringPlanVersion).filter(
            MonitoringPlanVersion.version_id == component.monitoring_plan_version_id
        ).first()

        if not version:
            raise HTTPException(
                status_code=400,
                detail="Component 9b: Selected monitoring plan version not found"
            )

        valid_plan_ids = [p.plan_id for p in monitoring_plans]
        if version.plan_id not in valid_plan_ids:
            raise HTTPException(
                status_code=400,
                detail="Component 9b: Selected version does not belong to a monitoring plan covering this model"
            )

    elif component.planned_treatment in ["NotPlanned", "NotApplicable"]:
        # If required by policy, must have rationale
        if is_required and not component.rationale:
            raise HTTPException(
                status_code=400,
                detail=f"Component 9b: Rationale required when selecting '{component.planned_treatment}' "
                       f"(monitoring plan review is required for this risk tier)"
            )

        # If model has monitoring plan but Not Applicable selected, require explanation
        if component.planned_treatment == "NotApplicable" and has_monitoring_plan:
            if not component.rationale:
                raise HTTPException(
                    status_code=400,
                    detail="Component 9b: Rationale required - model has an active monitoring plan"
                )
```

---

## Part 4: API Endpoints

### 4.1 Version Management Endpoints

```python
# In api/app/api/monitoring.py

@router.get("/monitoring/plans/{plan_id}/versions", response_model=List[MonitoringPlanVersionResponse])
def list_plan_versions(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all versions for a monitoring plan."""
    pass


@router.get("/monitoring/plans/{plan_id}/versions/{version_id}", response_model=MonitoringPlanVersionDetailResponse)
def get_plan_version(
    plan_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific version with its metric snapshots."""
    pass


@router.post("/monitoring/plans/{plan_id}/versions/publish", response_model=MonitoringPlanVersionResponse)
def publish_plan_version(
    plan_id: int,
    payload: PublishVersionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Publish a new version of the monitoring plan (Admin only)."""
    pass


@router.get("/monitoring/plans/{plan_id}/versions/{version_id}/export")
def export_version_metrics(
    plan_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export version metrics as CSV for manual comparison."""
    pass
```

### 4.2 Model Monitoring Plans Lookup

```python
@router.get("/models/{model_id}/monitoring-plans", response_model=List[ModelMonitoringPlanResponse])
def get_model_monitoring_plans(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get monitoring plans covering this model.
    Used for component 9b version selection.
    """
    pass
```

### 4.3 Validation Policy Update

```python
# Existing endpoint - add new fields to schema
@router.patch("/validation-workflow/policies/{policy_id}")
def update_validation_policy(
    policy_id: int,
    payload: ValidationPolicyUpdate,  # Add monitoring_plan_review_required
    ...
):
    pass
```

---

## Part 5: Pydantic Schemas

```python
# In api/app/schemas/monitoring.py

class PublishVersionRequest(BaseModel):
    """Request to publish a new plan version."""
    version_name: Optional[str] = None
    description: Optional[str] = None
    effective_date: Optional[date] = None  # Defaults to today


class MonitoringPlanVersionResponse(BaseModel):
    """Summary response for a plan version."""
    version_id: int
    plan_id: int
    version_number: int
    version_name: Optional[str]
    description: Optional[str]
    effective_date: date
    published_by: Optional[UserRef]
    published_at: datetime
    is_active: bool
    metrics_count: int = 0
    cycles_count: int = 0

    class Config:
        from_attributes = True


class MetricSnapshotResponse(BaseModel):
    """Response for a metric snapshot within a version."""
    snapshot_id: int
    kpm_id: int
    kpm_name: str
    kpm_category_name: Optional[str]
    evaluation_type: str
    yellow_min: Optional[float]
    yellow_max: Optional[float]
    red_min: Optional[float]
    red_max: Optional[float]
    qualitative_guidance: Optional[str]
    sort_order: int

    class Config:
        from_attributes = True


class MonitoringPlanVersionDetailResponse(MonitoringPlanVersionResponse):
    """Detailed response including metric snapshots."""
    metric_snapshots: List[MetricSnapshotResponse] = []


class ModelMonitoringPlanResponse(BaseModel):
    """Monitoring plan info for model lookup (component 9b)."""
    plan_id: int
    plan_name: str
    frequency: str
    active_version: Optional[MonitoringPlanVersionResponse]
    all_versions: List[MonitoringPlanVersionResponse] = []
    latest_cycle_status: Optional[str]
    latest_cycle_outcome_summary: Optional[str]
```

---

## Part 6: Implementation Phases

### Phase A: Database & Models (Backend) - ~2 days ✅ COMPLETE (2025-11-27)

| Task | Status | Notes |
|------|--------|-------|
| Create migration for new tables and columns | ✅ | `l2m3n4o5p6q7_add_monitoring_plan_versioning.py` |
| Add SQLAlchemy models | ✅ | `MonitoringPlanVersion`, `MonitoringPlanMetricSnapshot` in `monitoring.py` |
| Update MonitoringCycle model | ✅ | Added `plan_version_id`, `version_locked_at`, `version_locked_by_user_id` |
| Update ValidationPolicy model | ✅ | Added `monitoring_plan_review_required`, `monitoring_plan_review_description` |
| Update ValidationPlanComponent model | ✅ | Added `monitoring_plan_version_id`, `monitoring_review_notes` |
| Update __init__.py exports | ✅ | Both new models exported |
| Create Pydantic schemas | ✅ | All version schemas in `monitoring.py` |
| Write unit tests for models | ⏸️ | Deferred to Phase F (will test with API) |
| Update list_monitoring_plans API | ✅ | Added `version_count`, `active_version_number` |
| Migration backfill | ✅ | v1 created for existing plans, metrics snapshotted, active cycles linked |

**Verified Working:**
- Migration applies successfully
- v1 backfilled for existing plan (1 version with 3 metric snapshots)
- API returns `version_count: 1`, `active_version_number: 1`

### Phase B: Version CRUD API (Backend) - ~2 days
1. Implement list versions endpoint
2. Implement get version with snapshots endpoint
3. Implement publish version endpoint with metric snapshotting
4. Implement export version metrics as CSV
5. Update cycle start to lock version
6. Add warning when editing metrics with active cycles
7. Write API tests

### Phase C: Component 9b Backend - ~2 days
1. Add component 9b to seed data (validation_component_definitions)
2. Update ValidationPolicy model and endpoints
3. Implement validation logic for 9b before status transitions
4. Implement model → monitoring plans lookup endpoint
5. Update validation plan component update endpoint
6. Write tests for 9b validation rules

### Phase D: Version Management UI (Frontend) - ~2 days
1. Add "Versions" tab to monitoring plan detail page
2. Create version list component with badges
3. Create "Publish Version" modal
4. Create version detail modal (view snapshots)
5. Add export CSV button
6. Add warning banner when editing metrics with active cycles

### Phase E: Component 9b UI (Frontend) - ~2 days
1. Add special handling for component 9b in ValidationPlanForm
2. Create monitoring plan version picker dropdown
3. Add version summary display (metrics, last cycle)
4. Handle "no monitoring plan" case (auto-set Not Applicable)
5. Add validation feedback before status transition

### Phase F: Testing & Documentation - ~1 day
1. Run full regression suite
2. Manual E2E testing
3. Update ARCHITECTURE.md
4. Update REGRESSION_TESTS.md
5. Update PLAN.md

---

## Part 7: Component 9b Definition (Seed Data)

```python
# Add to validation_component_definitions seed:
{
    "section_number": "9",
    "section_title": "Additional Considerations",
    "component_code": "9b",
    "component_title": "Performance Monitoring Plan Review",
    "is_test_or_analysis": False,
    "expectation_high": "Required",      # Tier 1: always review monitoring plan
    "expectation_medium": "Required",    # Tier 2: always review monitoring plan
    "expectation_low": "IfApplicable",   # Tier 3: if plan exists
    "expectation_very_low": "NotExpected", # Tier 4: not expected
    "sort_order": 92
}
```

---

## Part 8: UX Mockups

### 8.1 Versions Tab (Monitoring Plan Detail)

```
┌─────────────────────────────────────────────────────────────┐
│ Monitoring Plan: Credit Risk Stability Plan                 │
├─────────────────────────────────────────────────────────────┤
│ [Overview] [Metrics] [Cycles] [Versions] [Team]             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Version History                    [Publish New Version]    │
│                                                             │
│ ┌─ v3 (Active) ────────────────────────────────────────────┐│
│ │  Q4 2025 Threshold Update                                ││
│ │  Published: 2025-11-15 by Admin                          ││
│ │  5 metrics | 2 cycles using this version                 ││
│ │  [View Details] [Export CSV]                             ││
│ └──────────────────────────────────────────────────────────┘│
│                                                             │
│ ┌─ v2 ─────────────────────────────────────────────────────┐│
│ │  Added PSI Metric                                        ││
│ │  Published: 2025-08-01 by Admin                          ││
│ │  4 metrics | 3 cycles using this version                 ││
│ │  [View Details] [Export CSV]                             ││
│ └──────────────────────────────────────────────────────────┘│
│                                                             │
│ ┌─ v1 (Initial) ───────────────────────────────────────────┐│
│ │  Initial Configuration                                   ││
│ │  Published: 2025-01-15 by Admin                          ││
│ │  3 metrics | 4 cycles using this version                 ││
│ │  [View Details] [Export CSV]                             ││
│ └──────────────────────────────────────────────────────────┘│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Component 9b in Validation Plan Form

```
┌─────────────────────────────────────────────────────────────┐
│ Section 9 – Additional Considerations                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─ 9b. Performance Monitoring Plan Review ─────────────────┐│
│ │                                                          ││
│ │ Bank Expectation: [Required]     (Tier 1 model)         ││
│ │                                                          ││
│ │ Planned Status: [Planned ▼]                              ││
│ │                                                          ││
│ │ ┌─ Select Monitoring Plan Version ──────────────────────┐││
│ │ │                                                       │││
│ │ │ Plan: Credit Risk Stability Monitoring                │││
│ │ │       [View Plan →]                                   │││
│ │ │                                                       │││
│ │ │ Version: [v3 - Q4 2025 Update (2025-11-15) ▼]        │││
│ │ │                                                       │││
│ │ │ ┌─ Version Summary ──────────────────────────────┐   │││
│ │ │ │ • 5 KPMs configured                            │   │││
│ │ │ │ • Thresholds: PSI <0.1, KS <0.15, Gini >0.4   │   │││
│ │ │ │ • Last cycle: Q3 2025 (APPROVED)              │   │││
│ │ │ │ • Outcome: 4 Green, 1 Yellow                  │   │││
│ │ │ └────────────────────────────────────────────────┘   │││
│ │ │                                                       │││
│ │ └───────────────────────────────────────────────────────┘││
│ │                                                          ││
│ │ Review Notes:                                            ││
│ │ [____________________________________________]           ││
│ │                                                          ││
│ └──────────────────────────────────────────────────────────┘│
│                                                             │
│ ┌─ ℹ️ No Monitoring Plan ──────────────────────────────────┐│
│ │ No active monitoring plan covers this model.             ││
│ │ Planned Status automatically set to "Not Applicable".    ││
│ └──────────────────────────────────────────────────────────┘│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 8.3 Warning Banner (Metrics Tab)

```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ Active Cycles Warning                                    │
│                                                             │
│ There are 2 active cycle(s) locked to previous versions.    │
│ Changes made here will only affect cycles created after     │
│ a new version is published.                                 │
│                                                             │
│ Active cycles: Q3 2025 (v2), Q4 2025 (v3)                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 9: Test Coverage Plan

### Backend Tests (api/tests/test_monitoring_versioning.py)

#### Version CRUD
- [ ] List versions when none exist
- [ ] Publish first version creates v1
- [ ] Publish second version increments to v2
- [ ] Publish version deactivates previous active
- [ ] Get version includes metric snapshots
- [ ] Get non-existent version returns 404
- [ ] Export version metrics as CSV
- [ ] Non-admin cannot publish version (403)

#### Cycle Version Binding
- [ ] Start cycle locks to active version
- [ ] Start cycle without published version fails
- [ ] Locked cycle version not affected by metric changes
- [ ] Cycle response includes version info

#### Component 9b Validation
- [ ] 9b Planned without version fails
- [ ] 9b Planned with invalid version fails
- [ ] 9b NotPlanned without rationale fails (when required)
- [ ] 9b NotApplicable auto-allowed when no plan exists
- [ ] 9b validation blocks status transition to Review
- [ ] 9b validation blocks status transition to Pending Approval
- [ ] Valid 9b allows status transition

---

## Part 10: Migration Strategy

### Data Migration for Existing Data

```python
def upgrade():
    # 1. Create tables
    op.create_table('monitoring_plan_versions', ...)
    op.create_table('monitoring_plan_metric_snapshots', ...)

    # 2. Add columns
    op.add_column('monitoring_cycles', ...)
    op.add_column('validation_policies', ...)
    op.add_column('validation_plan_components', ...)

    # 3. Backfill: Create v1 for all existing plans
    connection = op.get_bind()

    # Get all plans
    plans = connection.execute(text("SELECT plan_id FROM monitoring_plans")).fetchall()

    for (plan_id,) in plans:
        # Create v1
        connection.execute(text("""
            INSERT INTO monitoring_plan_versions
            (plan_id, version_number, version_name, effective_date, is_active, published_at)
            VALUES (:plan_id, 1, 'Initial Version (Migrated)', CURRENT_DATE, TRUE, NOW())
            RETURNING version_id
        """), {"plan_id": plan_id})

        version_id = connection.execute(text(
            "SELECT version_id FROM monitoring_plan_versions WHERE plan_id = :plan_id"
        ), {"plan_id": plan_id}).scalar()

        # Snapshot current metrics
        connection.execute(text("""
            INSERT INTO monitoring_plan_metric_snapshots
            (version_id, original_metric_id, kpm_id, yellow_min, yellow_max,
             red_min, red_max, qualitative_guidance, sort_order, is_active,
             kpm_name, kpm_category_name, evaluation_type)
            SELECT :version_id, m.metric_id, m.kpm_id, m.yellow_min, m.yellow_max,
                   m.red_min, m.red_max, m.qualitative_guidance, m.sort_order, m.is_active,
                   k.name, c.name, COALESCE(k.evaluation_type, 'Quantitative')
            FROM monitoring_plan_metrics m
            JOIN kpms k ON m.kpm_id = k.kpm_id
            LEFT JOIN kpm_categories c ON k.category_id = c.category_id
            WHERE m.plan_id = :plan_id
        """), {"version_id": version_id, "plan_id": plan_id})

    # 4. Backfill: Link existing active cycles to v1
    connection.execute(text("""
        UPDATE monitoring_cycles c
        SET plan_version_id = v.version_id,
            version_locked_at = c.created_at
        FROM monitoring_plan_versions v
        WHERE c.plan_id = v.plan_id
        AND v.version_number = 1
        AND c.status NOT IN ('PENDING', 'CANCELLED')
        AND c.plan_version_id IS NULL
    """))
```

---

## Summary

This sub-plan provides a complete design for:

1. **Monitoring Plan Versioning** with manual publish workflow, metric snapshotting, and cycle-version binding
2. **Component 9b** as a configurable validation plan component for reviewing performance monitoring plans
3. **Risk-tier configuration** to make 9b required/optional per tier
4. **Validation gates** to ensure 9b is completed before Review/Approval status

The estimated total effort is approximately **11 days** across 6 phases.

**Ready for your approval to proceed with Phase A (Database & Models).**
