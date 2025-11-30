# Recommendation Priority Configuration Implementation Plan

## Overview

This document tracks the implementation of:
1. Updated recommendation priority taxonomy codes to match labels (High, Medium, Low, Consideration)
2. Database-driven configuration for action plan requirements per priority
3. Workflow bypass allowing "Consideration" priority recommendations to skip action plans

---

## Phase 1: Database Schema Changes

### 1.1 Add `requires_action_plan` to RecommendationPriorityConfig

**File**: `api/alembic/versions/xxx_add_requires_action_plan.py`

```python
def upgrade():
    op.add_column(
        'recommendation_priority_configs',
        sa.Column('requires_action_plan', sa.Boolean(), nullable=False, server_default='true')
    )

def downgrade():
    op.drop_column('recommendation_priority_configs', 'requires_action_plan')
```

**Status**: [ ] Not Started

### 1.2 Update SQLAlchemy Model

**File**: `api/app/models/recommendation.py` (line ~370)

```python
class RecommendationPriorityConfig(Base):
    # ... existing fields ...
    requires_action_plan: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="If false, recommendations with this priority can skip action plan and go directly to acknowledgement"
    )
```

**Status**: [ ] Not Started

### 1.3 Update Pydantic Schemas

**File**: `api/app/schemas/recommendation.py`

Add to `PriorityConfigResponse`:
```python
requires_action_plan: bool
```

Add to `PriorityConfigUpdate`:
```python
requires_action_plan: Optional[bool] = None
```

**Status**: [ ] Not Started

---

## Phase 2: Priority Taxonomy Code Updates

### 2.1 Database Migration for Taxonomy Codes

**New Codes**:
| Old Code | New Code | Label | Sort Order |
|----------|----------|-------|------------|
| CRITICAL | HIGH | High | 1 |
| HIGH | MEDIUM | Medium | 2 |
| MEDIUM | LOW | Low | 3 |
| LOW | CONSIDERATION | Consideration | 4 |

**Migration SQL**:
```sql
-- Update taxonomy_values codes for Recommendation Priority
UPDATE taxonomy_values
SET code = 'NEW_CODE'
WHERE code = 'OLD_CODE'
  AND taxonomy_id = (SELECT taxonomy_id FROM taxonomies WHERE name = 'Recommendation Priority');
```

**Status**: [ ] Not Started - **User to confirm code mapping**

### 2.2 Update Seed Data

**File**: `api/app/seed.py` (lines 1198-1227)

```python
{
    "name": "Recommendation Priority",
    "description": "Priority levels for recommendations - determines closure approval requirements",
    "is_system": True,
    "values": [
        {
            "code": "HIGH",
            "label": "High",
            "description": "High priority - requires prompt attention and full action plan workflow.",
            "sort_order": 1
        },
        {
            "code": "MEDIUM",
            "label": "Medium",
            "description": "Standard priority - requires timely remediation with action plan.",
            "sort_order": 2
        },
        {
            "code": "LOW",
            "label": "Low",
            "description": "Low priority - can be scheduled as resources permit.",
            "sort_order": 3
        },
        {
            "code": "CONSIDERATION",
            "label": "Consideration",
            "description": "Informational - no action plan required, acknowledgement only.",
            "sort_order": 4
        },
    ]
}
```

**Status**: [ ] Not Started

### 2.3 Update Test Fixtures

**File**: `api/tests/test_recommendations.py` (lines 51-58)

Update from `REC_HIGH`, `REC_MEDIUM`, `REC_LOW` to new codes.

**Status**: [ ] Not Started

---

## Phase 3: Frontend Priority Color Updates

### 3.1 Files Requiring Update

| File | Function/Location | Current Codes | Update Required |
|------|-------------------|---------------|-----------------|
| `AdminDashboardPage.tsx:1206-1209` | Inline switch | CRITICAL, HIGH, MEDIUM | Yes |
| `RecommendationDetailPage.tsx:123-129` | `getPriorityColor()` | HIGH, MEDIUM, LOW | Yes |
| `RecommendationsPage.tsx:199-206` | `getPriorityColor()` | HIGH, MEDIUM, LOW | Yes |
| `ValidationRequestDetailPage.tsx:1795-1798` | Inline switch | HIGH, MEDIUM | Yes |
| `ModelDetailsPage.tsx:2699-2702` | Inline switch | HIGH, MEDIUM | Yes |

### 3.2 New Color Mapping

```typescript
const getPriorityColor = (code: string): string => {
    switch (code) {
        case 'HIGH': return 'bg-red-100 text-red-800';
        case 'MEDIUM': return 'bg-yellow-100 text-yellow-800';
        case 'LOW': return 'bg-blue-100 text-blue-800';
        case 'CONSIDERATION': return 'bg-gray-100 text-gray-600';
        default: return 'bg-gray-100 text-gray-800';
    }
};
```

**Status**: [ ] Not Started

---

## Phase 4: Workflow Logic for Action Plan Bypass

### 4.1 Backend API Changes

**File**: `api/app/api/recommendations.py`

#### 4.1.1 Helper Function to Check Action Plan Requirement

```python
def check_requires_action_plan(db: Session, recommendation: Recommendation) -> bool:
    """Check if recommendation's priority requires an action plan."""
    config = db.query(RecommendationPriorityConfig).filter(
        RecommendationPriorityConfig.priority_id == recommendation.priority_id
    ).first()

    if config:
        return config.requires_action_plan

    # Default to requiring action plan if no config found
    return True
```

**Status**: [ ] Not Started

#### 4.1.2 New Endpoint: Skip Action Plan (Option A - Validator Still Finalizes)

```python
@router.post("/{recommendation_id}/skip-action-plan", response_model=RecommendationResponse)
def skip_action_plan(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Skip action plan for low-priority recommendations.
    Only allowed for priorities with requires_action_plan=False.

    Workflow: PENDING_RESPONSE -> PENDING_VALIDATOR_REVIEW (validator still finalizes)
    Then validator finalizes -> PENDING_ACKNOWLEDGEMENT -> developer acknowledges -> OPEN
    """
    recommendation = db.query(Recommendation).filter(
        Recommendation.recommendation_id == recommendation_id
    ).first()

    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    check_not_terminal(recommendation, db)
    check_developer_or_admin(current_user, recommendation)

    # Verify priority allows skipping action plan
    if check_requires_action_plan(db, recommendation):
        raise HTTPException(
            status_code=400,
            detail="This priority level requires an action plan. Use the standard workflow."
        )

    # Check current status
    current_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == recommendation.current_status_id
    ).first()

    if current_status.code != "REC_PENDING_RESPONSE":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot skip action plan from {current_status.label} status. Expected PENDING_RESPONSE."
        )

    # Skip to PENDING_VALIDATOR_REVIEW (validator still needs to finalize)
    new_status = get_status_by_code(db, "REC_PENDING_VALIDATOR_REVIEW")
    create_status_history(
        db, recommendation, new_status, current_user,
        "Action plan skipped - not required for this priority level"
    )

    db.commit()
    db.refresh(recommendation)
    return recommendation
```

**Status**: [ ] Not Started

#### 4.1.3 Add Priority Config to Recommendation Response

Consider adding `requires_action_plan` to recommendation response so frontend knows what buttons to show.

**Status**: [ ] Not Started

### 4.2 Frontend UI Changes

#### 4.2.1 RecommendationDetailPage - Show Skip Action Plan Option

When recommendation is in `PENDING_RESPONSE` status and priority doesn't require action plan:

```tsx
{currentStatus === 'REC_PENDING_RESPONSE' && !requiresActionPlan && (
    <button
        onClick={handleSkipActionPlan}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
    >
        Skip Action Plan (Submit for Validator Review)
    </button>
)}
```

This sends recommendation to validator for finalization without requiring an action plan.

**Status**: [ ] Not Started

#### 4.2.2 Priority Config Admin UI

Update admin interface to show/edit `requires_action_plan` setting per priority.

**File**: Create new component or add to existing Taxonomy management page.

**Status**: [ ] Not Started

---

## Phase 5: Seed Data for Priority Configs

### 5.1 Update Seed Script

**File**: `api/app/seed.py`

Add seeding for `RecommendationPriorityConfig` with `requires_action_plan`:

```python
# After creating recommendation priority taxonomy values...
priority_configs = [
    {"priority_code": "HIGH", "requires_final_approval": True, "requires_action_plan": True},
    {"priority_code": "MEDIUM", "requires_final_approval": True, "requires_action_plan": True},
    {"priority_code": "LOW", "requires_final_approval": False, "requires_action_plan": True},
    {"priority_code": "CONSIDERATION", "requires_final_approval": False, "requires_action_plan": False},
]

for config in priority_configs:
    priority_value = db.query(TaxonomyValue).filter(
        TaxonomyValue.code == config["priority_code"]
    ).first()
    if priority_value:
        existing = db.query(RecommendationPriorityConfig).filter(
            RecommendationPriorityConfig.priority_id == priority_value.value_id
        ).first()
        if not existing:
            db.add(RecommendationPriorityConfig(
                priority_id=priority_value.value_id,
                requires_final_approval=config["requires_final_approval"],
                requires_action_plan=config["requires_action_plan"]
            ))
```

**Status**: [ ] Not Started

---

## Phase 6: Testing

### 6.1 Backend Tests

**File**: `api/tests/test_recommendations.py`

Add tests for:
- [ ] `acknowledge-direct` endpoint success for CONSIDERATION priority
- [ ] `acknowledge-direct` endpoint rejection for HIGH/MEDIUM/LOW priorities
- [ ] Priority config CRUD with `requires_action_plan`
- [ ] Workflow state transitions with action plan bypass

### 6.2 Frontend Tests

- [ ] Verify priority color rendering with new codes
- [ ] Verify "Acknowledge" button appears for CONSIDERATION priority
- [ ] Verify action plan form hidden for CONSIDERATION priority

**Status**: [ ] Not Started

---

## Implementation Order

1. **Phase 1**: Database schema changes (migration + model)
2. **Phase 2**: Priority taxonomy codes (if changing codes)
3. **Phase 3**: Frontend color updates
4. **Phase 4**: Workflow logic (backend API + frontend UI)
5. **Phase 5**: Seed data updates
6. **Phase 6**: Testing

---

## Questions to Resolve Before Implementation

1. ✅ **Priority code mapping**: User confirmed: High, Medium, Low, Consideration
2. ✅ **Workflow for Consideration**: Skip action plan entirely
3. ✅ **Configuration approach**: Database-driven via `RecommendationPriorityConfig`
4. ✅ **Workflow path**: Option A selected - validator still finalizes
   - PENDING_RESPONSE → PENDING_VALIDATOR_REVIEW → PENDING_ACKNOWLEDGEMENT → OPEN
   - (skips action plan submission, but validator still reviews and finalizes)

---

## Progress Tracking

| Phase | Task | Status | Notes |
|-------|------|--------|-------|
| 1.1 | Migration for `requires_action_plan` | [x] | b18069c182f0 migration created |
| 1.2 | Update SQLAlchemy model | [x] | Added to RecommendationPriorityConfig |
| 1.3 | Update Pydantic schemas | [x] | Updated create/update/response |
| 2.1 | Taxonomy code migration | [x] | Added CONSIDERATION, kept HIGH/MEDIUM/LOW |
| 2.2 | Update seed data | [x] | Added priority config seeding |
| 2.3 | Update test fixtures | [x] | Updated to HIGH/MEDIUM/LOW/CONSIDERATION |
| 3.1 | AdminDashboardPage colors | [ ] | Validation priorities - different taxonomy |
| 3.2 | RecommendationDetailPage colors | [x] | Added CONSIDERATION |
| 3.3 | RecommendationsPage colors | [x] | Added CONSIDERATION |
| 3.4 | ValidationRequestDetailPage colors | [ ] | Validation priorities - different taxonomy |
| 3.5 | ModelDetailsPage colors | [ ] | Validation priorities - different taxonomy |
| 4.1 | Helper function | [x] | check_requires_action_plan() |
| 4.2 | skip-action-plan endpoint | [x] | POST /recommendations/{id}/skip-action-plan |
| 4.3 | can-skip-action-plan endpoint | [x] | GET /recommendations/{id}/can-skip-action-plan |
| 4.4 | Frontend Skip Action Plan button | [x] | RecommendationWorkflowActions component |
| 4.5 | Priority config admin UI | [ ] | Future enhancement |
| 5.1 | Seed priority configs | [x] | CONSIDERATION has requires_action_plan=false |
| 6.1 | Backend tests | [ ] | Future enhancement |
| 6.2 | Frontend tests | [ ] | Future enhancement |

---

## Phase 7: Regional Override Enhancement

### 7.1 Overview

Extend priority configuration to allow regional overrides. The "regions impacted" for a recommendation
is determined by the union of all regions where the associated model is deployed.

**Resolution Logic**: Most Restrictive Wins - if ANY region requires action plan, require it.

### 7.2 Database Schema

**New Table**: `recommendation_priority_regional_overrides`

```sql
CREATE TABLE recommendation_priority_regional_overrides (
    override_id SERIAL PRIMARY KEY,
    priority_id INTEGER NOT NULL REFERENCES taxonomy_values(value_id),
    region_id INTEGER NOT NULL REFERENCES regions(region_id),
    requires_action_plan BOOLEAN,      -- NULL = inherit from base priority config
    requires_final_approval BOOLEAN,   -- NULL = inherit from base priority config
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(priority_id, region_id)
);
```

**Status**: [ ] Not Started

### 7.3 SQLAlchemy Model

**File**: `api/app/models/recommendation.py`

```python
class RecommendationPriorityRegionalOverride(Base):
    """Regional overrides for recommendation priority configuration.

    Allows different workflow requirements based on model deployment regions.
    NULL values inherit from base RecommendationPriorityConfig.
    """
    __tablename__ = "recommendation_priority_regional_overrides"

    override_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    priority_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    region_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("regions.region_id"), nullable=False
    )
    requires_action_plan: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    requires_final_approval: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    priority = relationship("TaxonomyValue", foreign_keys=[priority_id])
    region = relationship("Region", foreign_keys=[region_id])

    __table_args__ = (
        UniqueConstraint('priority_id', 'region_id', name='uq_priority_region'),
    )
```

**Status**: [ ] Not Started

### 7.4 Updated Helper Functions

**File**: `api/app/api/recommendations.py`

```python
def check_requires_action_plan(db: Session, recommendation: Recommendation) -> bool:
    """Check if recommendation's priority requires an action plan.

    Resolution order:
    1. Check regional overrides for model's deployed regions (most restrictive wins)
    2. Fall back to base priority config
    3. Default to True if no config found
    """
    # Get model's deployed regions
    model = recommendation.model
    region_ids = [d.region_id for d in model.regional_deployments] if model.regional_deployments else []

    # Check for regional overrides (most restrictive wins)
    if region_ids:
        overrides = db.query(RecommendationPriorityRegionalOverride).filter(
            RecommendationPriorityRegionalOverride.priority_id == recommendation.priority_id,
            RecommendationPriorityRegionalOverride.region_id.in_(region_ids),
            RecommendationPriorityRegionalOverride.requires_action_plan.isnot(None)
        ).all()

        if overrides:
            # Most restrictive: if ANY region requires it, require it
            if any(o.requires_action_plan for o in overrides):
                return True
            # All overrides explicitly say no action plan required
            return False

    # Fall back to base priority config
    config = db.query(RecommendationPriorityConfig).filter(
        RecommendationPriorityConfig.priority_id == recommendation.priority_id
    ).first()

    return config.requires_action_plan if config else True
```

**Status**: [ ] Not Started

### 7.5 API Endpoints

**New endpoints for regional override CRUD**:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/recommendations/priority-config/regional-overrides/` | List all regional overrides |
| GET | `/recommendations/priority-config/{priority_id}/regional-overrides/` | List overrides for priority |
| POST | `/recommendations/priority-config/{priority_id}/regional-overrides/` | Create regional override |
| PATCH | `/recommendations/priority-config/regional-overrides/{override_id}` | Update regional override |
| DELETE | `/recommendations/priority-config/regional-overrides/{override_id}` | Delete regional override |

**Status**: [ ] Not Started

### 7.6 Pydantic Schemas

```python
class RegionalOverrideCreate(BaseModel):
    region_id: int
    requires_action_plan: Optional[bool] = None
    requires_final_approval: Optional[bool] = None
    description: Optional[str] = None

class RegionalOverrideUpdate(BaseModel):
    requires_action_plan: Optional[bool] = None
    requires_final_approval: Optional[bool] = None
    description: Optional[str] = None

class RegionalOverrideResponse(BaseModel):
    override_id: int
    priority_id: int
    region_id: int
    requires_action_plan: Optional[bool]
    requires_final_approval: Optional[bool]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    priority: Optional[TaxonomyValueResponse] = None
    region: Optional[RegionResponse] = None

    model_config = ConfigDict(from_attributes=True)
```

**Status**: [ ] Not Started

### 7.7 Admin UI Enhancement

Extend Recommendation Priority tab in TaxonomyPage.tsx:

1. Show base configuration table (existing)
2. Add "Regional Overrides" section below with:
   - Grid/matrix view: Priorities × Regions
   - Cells show: "✓" (requires), "✗" (skip), "—" (inherit base)
   - Click cell to create/edit override
3. Add explanation text about resolution logic

**Status**: [ ] Not Started

### 7.8 Example Configuration

| Priority | Base Default | US Override | EMEA Override | Global-only Model | US-deployed Model |
|----------|-------------|-------------|---------------|-------------------|-------------------|
| HIGH | action_plan=✓ | — | — | Requires | Requires |
| MEDIUM | action_plan=✓ | — | — | Requires | Requires |
| LOW | action_plan=✓ | — | action_plan=✗ | Requires | Requires (US inherits base) |
| CONSIDERATION | action_plan=✗ | action_plan=✓ | — | Skip allowed | **Requires** (US override) |

### 7.9 Edge Cases

| Scenario | Behavior |
|----------|----------|
| Model with no regional deployments | Use base priority config only |
| Model added to new region after rec created | Dynamically re-evaluate |
| New region added to system | No overrides = inherits base defaults |
| Override with NULL values | Explicitly inherit from base |
| Model in multiple regions with mixed overrides | Most restrictive wins |

---

## Phase 7 Progress Tracking

| Task | Status | Notes |
|------|--------|-------|
| 7.1 | Write unit tests for regional overrides | [ ] | TDD approach |
| 7.2 | Database migration | [ ] | |
| 7.3 | SQLAlchemy model | [ ] | |
| 7.4 | Update check_requires_action_plan() | [ ] | |
| 7.5 | Update check_requires_final_approval() | [ ] | |
| 7.6 | Pydantic schemas | [ ] | |
| 7.7 | API endpoints (CRUD) | [ ] | |
| 7.8 | Seed data for regional overrides | [ ] | Optional |
| 7.9 | Admin UI - Regional Overrides section | [ ] | |
| 7.10 | User-facing - Show which region triggered requirement | [ ] | |

---

## Rollback Plan

If issues arise:
1. Revert migration: `alembic downgrade -1`
2. Frontend changes are isolated to color functions - easy to revert
3. New endpoint can be disabled without affecting existing workflow
4. Regional override table can be dropped without affecting base priority configs
