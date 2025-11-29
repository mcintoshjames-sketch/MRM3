# Component Definition Versioning & Grandfathering

## Problem Statement

When validation component definitions change (e.g., bank updates standards to make "Sensitivity Analysis" Required instead of IfApplicable for Medium-risk models), existing validation plans that are already under review or approved should NOT retroactively appear non-compliant.

**Regulatory Requirement**: An auditor reviewing a 2025 validation should see it evaluated against the standards that existed in 2025, not standards from 2027.

## Solution: Configuration Versioning

### Architecture

**Three-Table Approach**:

1. **validation_component_definitions** (Master List - Current Active)
   - Contains the latest/current component definitions
   - Used for creating NEW plans
   - Admin UI modifies this table

2. **component_definition_configurations** (Configuration Versions)
   - Tracks snapshots of the entire configuration over time
   - Each version has: name, description, effective_date, created_by
   - Only one configuration is "active" at a time

3. **component_definition_config_items** (Snapshot Items)
   - Stores the actual component expectations for each version
   - Links to both: config_id AND component_id
   - Preserves all fields that might change over time

4. **validation_plans** (Updated)
   - Gets new fields: `config_id`, `locked_at`, `locked_by_user_id`
   - When plan is locked, links to the active configuration version

### Data Model

```sql
-- Configuration version header
CREATE TABLE component_definition_configurations (
    config_id SERIAL PRIMARY KEY,
    config_name VARCHAR(200) NOT NULL,  -- "2025-11-22 Initial Configuration"
    description TEXT,                    -- "SR 11-7 baseline requirements"
    effective_date DATE NOT NULL,        -- When this config took effect
    created_by_user_id INTEGER REFERENCES users(user_id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE  -- Only one active at a time
);

-- Snapshot of component expectations at a specific version
CREATE TABLE component_definition_config_items (
    config_item_id SERIAL PRIMARY KEY,
    config_id INTEGER NOT NULL REFERENCES component_definition_configurations(config_id) ON DELETE CASCADE,
    component_id INTEGER NOT NULL REFERENCES validation_component_definitions(component_id),

    -- Snapshot of expectations (what matters for compliance)
    expectation_high VARCHAR(20) NOT NULL,
    expectation_medium VARCHAR(20) NOT NULL,
    expectation_low VARCHAR(20) NOT NULL,
    expectation_very_low VARCHAR(20) NOT NULL,

    -- Metadata snapshot (in case component titles/codes change)
    section_number VARCHAR(10) NOT NULL,
    section_title VARCHAR(200) NOT NULL,
    component_code VARCHAR(20) NOT NULL,
    component_title VARCHAR(200) NOT NULL,
    is_test_or_analysis BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    UNIQUE(config_id, component_id)  -- Each component appears once per config
);

-- Update validation_plans to track versioning
ALTER TABLE validation_plans
ADD COLUMN config_id INTEGER REFERENCES component_definition_configurations(config_id),
ADD COLUMN locked_at TIMESTAMP,
ADD COLUMN locked_by_user_id INTEGER REFERENCES users(user_id);
```

## Lifecycle & Workflow

### Phase 1: Initial Setup (Seed)

```python
# In seed.py after creating component definitions:
initial_config = ComponentDefinitionConfiguration(
    config_name="Initial SR 11-7 Configuration",
    description="Baseline validation standards per SR 11-7",
    effective_date=date.today(),
    created_by_user_id=admin_user.user_id,
    is_active=True
)
db.add(initial_config)
db.flush()

# Snapshot all components
for component in all_components:
    config_item = ComponentDefinitionConfigItem(
        config_id=initial_config.config_id,
        component_id=component.component_id,
        expectation_high=component.expectation_high,
        expectation_medium=component.expectation_medium,
        expectation_low=component.expectation_low,
        expectation_very_low=component.expectation_very_low,
        section_number=component.section_number,
        section_title=component.section_title,
        component_code=component.component_code,
        component_title=component.component_title,
        is_test_or_analysis=component.is_test_or_analysis,
        sort_order=component.sort_order,
        is_active=component.is_active
    )
    db.add(config_item)
```

### Phase 2: Creating New Plans

When creating a validation plan, use current active configuration:

```python
# In create_validation_plan endpoint:
active_config = db.query(ComponentDefinitionConfiguration).filter_by(is_active=True).first()

new_plan = ValidationPlan(
    request_id=request_id,
    config_id=active_config.config_id,  # Link to active config
    # ... other fields
)

# Create plan components based on active_config expectations
for component in active_components:
    # Use active_config's expectations
    config_item = db.query(ComponentDefinitionConfigItem).filter_by(
        config_id=active_config.config_id,
        component_id=component.component_id
    ).first()

    expectation = get_expectation_for_tier(config_item, risk_tier)
    # ... create plan component
```

### Phase 3: Locking Plans (Grandfathering Trigger)

When validation request transitions to "Review" or "Pending Approval" status:

```python
# In update_validation_request_status endpoint:
if new_status.code in ["REVIEW", "PENDING_APPROVAL"]:
    # Lock the validation plan if it exists
    if validation_request.validation_plan:
        plan = validation_request.validation_plan

        if not plan.locked_at:  # Only lock if not already locked
            active_config = db.query(ComponentDefinitionConfiguration).filter_by(is_active=True).first()

            plan.config_id = active_config.config_id
            plan.locked_at = datetime.utcnow()
            plan.locked_by_user_id = current_user.user_id

            # Audit log
            audit_log = AuditLog(
                entity_type="ValidationPlan",
                entity_id=plan.plan_id,
                action="LOCK",
                user_id=current_user.user_id,
                changes={
                    "config_id": active_config.config_id,
                    "config_name": active_config.config_name,
                    "reason": f"Plan locked when validation moved to {new_status.label}"
                },
                timestamp=datetime.utcnow()
            )
            db.add(audit_log)
```

### Phase 3b: Unlocking Plans (Sendback Scenario)

When reviewer or approver sends validation back to an earlier status (e.g., Review → In Progress, Pending Approval → Review):

```python
# In update_validation_request_status endpoint:
# Unlock plan if moving backward from Review/Pending Approval/Approved
old_status_code = validation_request.current_status.code if validation_request.current_status else None
new_status_code = new_status.code

locked_statuses = ["REVIEW", "PENDING_APPROVAL", "APPROVED"]
editable_statuses = ["INTAKE", "PLANNING", "IN_PROGRESS"]

# If moving FROM locked status TO editable status, unlock the plan
if old_status_code in locked_statuses and new_status_code in editable_statuses:
    if validation_request.validation_plan and validation_request.validation_plan.locked_at:
        plan = validation_request.validation_plan

        # Unlock the plan (config_id stays to preserve what it was locked to)
        plan.locked_at = None
        plan.locked_by_user_id = None

        # Audit log
        audit_log = AuditLog(
            entity_type="ValidationPlan",
            entity_id=plan.plan_id,
            action="UNLOCK",
            user_id=current_user.user_id,
            changes={
                "reason": f"Plan unlocked when validation sent back to {new_status.label}",
                "previous_status": old_status_code,
                "new_status": new_status_code
            },
            timestamp=datetime.utcnow()
        )
        db.add(audit_log)
```

**Business Rule**: When unlocked, the plan becomes editable again. The `config_id` remains set (preserving the configuration version it was created under), but validators can modify component planned_treatment and rationale until it's re-locked.

### Phase 4: Admin Updates Configuration

Admin UI allows editing component definitions. When saved, create new configuration version:

```python
# In update_component_definitions endpoint (Admin only):
@router.post("/admin/component-definitions/publish", tags=["Admin"])
def publish_new_configuration(
    payload: PublishConfigurationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Publish a new configuration version after admin edits component definitions.
    This creates a snapshot and makes it the new active configuration.
    """
    # Deactivate previous active config
    previous_active = db.query(ComponentDefinitionConfiguration).filter_by(is_active=True).first()
    if previous_active:
        previous_active.is_active = False

    # Create new config version
    new_config = ComponentDefinitionConfiguration(
        config_name=payload.config_name,
        description=payload.description,
        effective_date=payload.effective_date or date.today(),
        created_by_user_id=current_user.user_id,
        is_active=True
    )
    db.add(new_config)
    db.flush()

    # Snapshot current component definitions
    components = db.query(ValidationComponentDefinition).filter_by(is_active=True).all()
    for component in components:
        config_item = ComponentDefinitionConfigItem(
            config_id=new_config.config_id,
            component_id=component.component_id,
            expectation_high=component.expectation_high,
            expectation_medium=component.expectation_medium,
            expectation_low=component.expectation_low,
            expectation_very_low=component.expectation_very_low,
            section_number=component.section_number,
            section_title=component.section_title,
            component_code=component.component_code,
            component_title=component.component_title,
            is_test_or_analysis=component.is_test_or_analysis,
            sort_order=component.sort_order,
            is_active=component.is_active
        )
        db.add(config_item)

    db.commit()

    # Audit log
    audit_log = AuditLog(
        entity_type="ComponentDefinitionConfiguration",
        entity_id=new_config.config_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "config_name": new_config.config_name,
            "components_count": len(components),
            "effective_date": str(new_config.effective_date)
        },
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)
    db.commit()

    return {"config_id": new_config.config_id, "message": "New configuration published"}
```

### Phase 5: Viewing Historical Plans

When viewing a locked plan, use its linked configuration version:

```python
# In get_validation_plan endpoint:
plan = db.query(ValidationPlan).filter_by(request_id=request_id).first()

if plan.locked_at:
    # Plan is locked - show it with historical configuration
    config = db.query(ComponentDefinitionConfiguration).filter_by(
        config_id=plan.config_id
    ).first()

    return {
        "plan_id": plan.plan_id,
        "locked": True,
        "locked_at": plan.locked_at,
        "configuration": {
            "config_id": config.config_id,
            "config_name": config.config_name,
            "effective_date": config.effective_date
        },
        # ... components with historical expectations
    }
```

## Admin UI Features

### 1. Component Definitions Management Page

**Route**: `/admin/component-definitions`

**Features**:
- View all components grouped by section
- Edit expectations for each risk tier
- Add new components
- Deactivate components
- Preview impact of changes (how many active plans would be affected)

**Workflow**:
1. Admin navigates to Component Definitions
2. Edits expectations in-place (e.g., change component 4.3 from "IfApplicable" to "Required" for Medium-risk)
3. Clicks "Save Draft" (updates validation_component_definitions but doesn't publish)
4. Clicks "Publish New Configuration"
   - Modal opens asking for configuration name and description
   - Shows warning: "X active validation plans will continue using the old configuration"
   - Creates new configuration version
   - New plans created after this will use the new configuration

### 2. Configuration History Page

**Route**: `/admin/component-configurations`

**Features**:
- List all configuration versions
- View which plans are using which configuration
- Compare configurations side-by-side
- Export configuration as PDF for documentation

**Table Columns**:
- Configuration Name
- Effective Date
- Created By
- Status (Active / Historical)
- Plans Using This Config (count)
- Actions (View, Compare)

### 3. Component Definition Detail Modal

**Features**:
- Edit all fields: code, title, section, expectations per tier
- Show history of changes to this component
- Show which configurations included this component

## Plan Templating from Previous Validations

### Business Requirement

When creating a new validation plan, if a previous validation of the same **Validation Type** exists for the same model(s), offer to use that previous plan as a template. This saves validators significant time when performing periodic validations (e.g., comprehensive reviews of the same model).

### Implementation

**API Endpoint**:
```
GET /validation-workflow/requests/{request_id}/plan/template-suggestions

Response:
{
  "has_suggestions": true,
  "suggestions": [
    {
      "source_request_id": 5,
      "source_plan_id": 3,
      "validation_type": "Comprehensive Review",
      "model_names": ["Credit Risk RWA Model"],
      "completion_date": "2024-11-15",
      "validator_name": "Sarah Chen",
      "component_count": 30,
      "deviations_count": 2
    }
  ]
}
```

**Create Plan with Template**:
```
POST /validation-workflow/requests/{request_id}/plan
{
  "overall_scope_summary": "Annual review for 2025",
  "material_deviation_from_standard": false,
  "template_plan_id": 3,  // Optional: copy from this plan
  "components": []
}
```

**Templating Logic**:

1. **Find eligible templates**:
   - Same Validation Type (e.g., "Annual Review")
   - Same or overlapping models
   - Previous validation is complete (status = Approved)
   - Most recent takes precedence

2. **Copy plan components**:
   - Copy `planned_treatment` for each component
   - Copy `rationale` for each component
   - Copy `overall_scope_summary` (validator can edit)
   - Copy `material_deviation_from_standard` flag

3. **Preserve configuration**:
   - Do NOT copy `config_id` - always use active configuration
   - Recalculate `is_deviation` based on active configuration's expectations
   - This ensures new plan uses current standards while preserving validator's decisions

4. **Audit trail**:
   - Log that plan was created from template
   - Reference source plan_id

**Example Workflow**:

```python
# In create_validation_plan endpoint:
if template_plan_id:
    template_plan = db.query(ValidationPlan).filter_by(plan_id=template_plan_id).first()

    if template_plan:
        # Copy high-level plan fields
        new_plan.overall_scope_summary = template_plan.overall_scope_summary
        new_plan.material_deviation_from_standard = template_plan.material_deviation_from_standard
        new_plan.overall_deviation_rationale = template_plan.overall_deviation_rationale

        # Create components based on template
        for template_comp in template_plan.components:
            # Get active config expectation for this component
            active_config_item = db.query(ComponentDefinitionConfigItem).filter_by(
                config_id=active_config.config_id,
                component_id=template_comp.component_id
            ).first()

            default_expectation = get_expectation_for_tier(active_config_item, risk_tier_code)

            plan_component = ValidationPlanComponent(
                plan_id=new_plan.plan_id,
                component_id=template_comp.component_id,
                default_expectation=default_expectation,  # From ACTIVE config
                planned_treatment=template_comp.planned_treatment,  # From template
                rationale=template_comp.rationale,  # From template
                is_deviation=calculate_is_deviation(default_expectation, template_comp.planned_treatment)
            )
            db.add(plan_component)

        # Audit log
        audit_log = AuditLog(
            entity_type="ValidationPlan",
            entity_id=new_plan.plan_id,
            action="CREATE_FROM_TEMPLATE",
            user_id=current_user.user_id,
            changes={
                "template_plan_id": template_plan_id,
                "template_request_id": template_plan.request_id
            }
        )
        db.add(audit_log)
```

**UI/UX**:

When validator clicks "Create Validation Plan", if templates are available:

1. Show modal: "Previous Plans Available"
   - "We found X previous validation plan(s) for similar validations"
   - List template options with key details
   - Buttons: "Use Template" | "Start Fresh"

2. If "Use Template" clicked:
   - Pre-populate form with template values
   - Show info banner: "Plan created from [Validation #5 - Annual Review 2024]"
   - All fields remain editable

3. If "Start Fresh" clicked:
   - Use standard auto-defaults based on Figure 3 matrix

## API Endpoints

### Admin Component Management

```
GET    /admin/component-definitions          # List all components (editable)
PATCH  /admin/component-definitions/{id}     # Update component (draft mode)
POST   /admin/component-definitions          # Add new component
DELETE /admin/component-definitions/{id}     # Deactivate component

POST   /admin/component-definitions/publish  # Publish new configuration version
GET    /admin/component-configurations       # List all configuration versions
GET    /admin/component-configurations/{id}  # Get specific configuration with all items
GET    /admin/component-configurations/{id}/impact  # Preview impact on existing plans
```

### Public (Validator) Endpoints

```
GET /validation-workflow/component-definitions  # Get active configuration
GET /validation-workflow/requests/{id}/plan     # Get plan with its locked configuration
```

## Migration Strategy

### Step 1: Schema Migration

```bash
alembic revision --autogenerate -m "Add component definition versioning"
alembic upgrade head
```

### Step 2: Data Migration

```python
# In upgrade():
# 1. Create initial configuration
# 2. Snapshot all existing components
# 3. Link all existing plans to initial configuration
# 4. Set locked_at for plans in Review/Pending Approval/Approved status
```

### Step 3: Code Updates

1. Update validation plan creation logic
2. Add plan locking on status transitions
3. Update plan retrieval to use config_id
4. Create admin API endpoints
5. Create admin UI components

## Benefits

1. **Compliance**: Auditors see historical plans evaluated against historical standards
2. **Flexibility**: Admin can update standards without breaking existing validations
3. **Transparency**: Clear audit trail of when and why standards changed
4. **Data Integrity**: Plans locked at specific points in workflow can't be retroactively invalidated

## Testing Scenarios

### Test 1: Plan Grandfathering

1. Create validation plan for Low-risk model
2. Component 4.3 expectation is "IfApplicable"
3. Plan component defaults to "Planned"
4. Move validation to "Review" status → plan locks
5. Admin changes component 4.3 expectation to "Required" for Low-risk
6. Create NEW validation plan → uses new expectation
7. View OLD locked plan → still shows "IfApplicable" expectation, no deviation

### Test 2: Configuration History

1. Admin publishes configuration "Q1 2025 Update"
2. 5 new plans created using this configuration
3. Admin publishes configuration "Q2 2025 Update"
4. 3 new plans created using new configuration
5. View configuration history:
   - Q2 2025: 3 active plans
   - Q1 2025: 5 locked plans
   - Initial: 10 locked plans

### Test 3: Unlocked Plan Updates

1. Create validation plan (not locked)
2. Admin publishes new configuration
3. Plan should automatically use new configuration when loaded
4. Once plan locks, it freezes to that configuration

## Future Enhancements

- **Configuration comparison tool**: Side-by-side diff of two configurations
- **Impact analysis**: Before publishing, show which components changed and estimate impact
- **Scheduled configuration releases**: Set effective_date in future, auto-activate
- **Configuration approval workflow**: Require senior approval before publishing new config
- **Export/import configurations**: Support regulatory documentation requirements
