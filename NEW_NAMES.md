# Plan: Add Shared Owner/Developer and Monitoring Manager with LOB Rollup

## Summary
Add `shared_owner_id`, `shared_developer_id`, and `monitoring_manager_id` to models, display all roles with LOB names rolled up to LOB4 level.

## Confirmed Requirements

| Requirement | Details |
|-------------|---------|
| LOB Rollup | LOB5+ → show LOB4 ancestor; LOB4 or higher → show actual LOB |
| Monitoring Manager | On Model (one per model), displayed in Monitoring tab |
| Default Data Provider | New MonitoringPlan defaults to model's monitoring_manager |
| Validation | shared_owner ≠ owner; shared_developer ≠ developer |
| Display Format | Just LOB name (e.g., "Global Markets") |

---

## Implementation Plan

### Phase 1: Database Migration

**File**: `api/alembic/versions/xxx_add_shared_roles_and_monitoring_manager.py`

```python
def upgrade():
    op.add_column('models', sa.Column('shared_owner_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_models_shared_owner', 'models', 'users',
                          ['shared_owner_id'], ['user_id'], ondelete='SET NULL')

    op.add_column('models', sa.Column('shared_developer_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_models_shared_developer', 'models', 'users',
                          ['shared_developer_id'], ['user_id'], ondelete='SET NULL')

    op.add_column('models', sa.Column('monitoring_manager_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_models_monitoring_manager', 'models', 'users',
                          ['monitoring_manager_id'], ['user_id'], ondelete='SET NULL')
```

---

### Phase 2: Backend Model Changes

**File**: `api/app/models/model.py` (after line 57, after `developer_id`)

Add columns:
```python
shared_owner_id: Mapped[Optional[int]] = mapped_column(
    Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
shared_developer_id: Mapped[Optional[int]] = mapped_column(
    Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
monitoring_manager_id: Mapped[Optional[int]] = mapped_column(
    Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
```

Add relationships (after line 107):
```python
shared_owner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[shared_owner_id])
shared_developer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[shared_developer_id])
monitoring_manager: Mapped[Optional["User"]] = relationship("User", foreign_keys=[monitoring_manager_id])
```

---

### Phase 3: LOB Rollup Utility

**New File**: `api/app/core/lob_utils.py`

```python
LOB4_LEVEL = 5  # 1=SBU, 2=LOB1, 3=LOB2, 4=LOB3, 5=LOB4

def get_lob_rollup_name(lob, target_level: int = LOB4_LEVEL) -> str | None:
    """Get LOB name rolled up to LOB4 (or current level if LOB3 or higher)."""
    if lob is None:
        return None
    if lob.level <= target_level:
        return lob.name
    # Traverse up to LOB4
    current = lob
    while current and current.level > target_level:
        current = current.parent
    return current.name if current else lob.name

def get_user_lob_rollup_name(user, target_level: int = LOB4_LEVEL) -> str | None:
    """Get user's LOB name rolled up to LOB4."""
    return get_lob_rollup_name(user.lob if user else None, target_level)
```

---

### Phase 4: Schema Updates

**File**: `api/app/schemas/model.py`

Update `ModelCreate`, `ModelUpdate`, `ModelResponse`:
```python
shared_owner_id: Optional[int] = None
shared_developer_id: Optional[int] = None
monitoring_manager_id: Optional[int] = None
```

Update `ModelDetailResponse`:
```python
shared_owner: Optional[UserResponse] = None
shared_developer: Optional[UserResponse] = None
monitoring_manager: Optional[UserResponse] = None
```

---

### Phase 5: API Validation

**File**: `api/app/api/models.py` (in create_model and update_model)

Add validation:
```python
if model_data.shared_owner_id and model_data.shared_owner_id == model_data.owner_id:
    raise HTTPException(400, "Shared owner must be different from owner")

if model_data.shared_developer_id and model_data.developer_id:
    if model_data.shared_developer_id == model_data.developer_id:
        raise HTTPException(400, "Shared developer must be different from developer")
```

Add new endpoint for LOB rollup data:
```python
@router.get("/{model_id}/roles-with-lob")
def get_model_roles_with_lob(model_id: int, db: Session, current_user: User):
    """Get all model roles with LOB names rolled up to LOB4."""
    # Returns owner, shared_owner, developer, shared_developer, monitoring_manager
    # Each with: user_id, full_name, email, lob_rollup_name
```

---

### Phase 6: Frontend - Model Details Page

**File**: `web/src/pages/ModelDetailsPage.tsx`

1. Update Model interface with new fields
2. Add state for LOB rollup data: `rolesWithLOB`
3. Fetch from `/models/{id}/roles-with-lob` on mount
4. Replace owner/developer section (~line 2403) with grouped "Model Roles" card:

```
┌──────────────────────────────────────────────────────────┐
│ Model Roles                                              │
├─────────────────┬────────────────┬───────────────────────┤
│ Owner           │ Shared Owner   │ Developer │ Shared Dev│
│ John Smith      │ Jane Doe       │ Bob J.    │ -         │
│ john@ex.com     │ jane@ex.com    │ bob@ex.com│           │
│ Global Markets  │ Equities       │ Technology│           │
└─────────────────┴────────────────┴───────────────────────┘
```

5. Add searchable dropdowns in edit form for new fields

---

### Phase 7: Frontend - Monitoring Tab

**File**: `web/src/components/ModelMonitoringTab.tsx`

1. Update props to receive `monitoringManager` with LOB rollup
2. Add Monitoring Manager display at top:

```
┌──────────────────────────────────────────────────────────┐
│ Monitoring Manager                                       │
│ Sarah Wilson • sarah@example.com • Risk Analytics        │
└──────────────────────────────────────────────────────────┘
```

3. Pass from ModelDetailsPage via props (from rolesWithLOB)

---

### Phase 8: Default Data Provider for New Plans

When model has a monitoring_manager, the "Add to Monitoring Plan" flow should pre-populate Data Provider with that user (if creating a new plan).

---

## Files to Modify

| Layer | File | Changes |
|-------|------|---------|
| DB | `api/alembic/versions/xxx_add_shared_roles.py` | New migration |
| Model | `api/app/models/model.py` | 3 columns + 3 relationships |
| Util | `api/app/core/lob_utils.py` | NEW - LOB rollup functions |
| Schema | `api/app/schemas/model.py` | Add fields to Create/Update/Response |
| API | `api/app/api/models.py` | Validation + new endpoint |
| Frontend | `web/src/pages/ModelDetailsPage.tsx` | Roles section + edit form |
| Frontend | `web/src/components/ModelMonitoringTab.tsx` | Manager display |

---

## Test Cases

1. Create model with shared_owner = owner → **400 error**
2. Create model with shared_developer = developer → **400 error**
3. Create model with valid shared roles → **success**
4. `/roles-with-lob` for LOB5 user → returns LOB4 name
5. `/roles-with-lob` for LOB3 user → returns LOB3 name
