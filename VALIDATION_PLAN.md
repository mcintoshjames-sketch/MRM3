# Validation Plan Feature

## Overview

The Validation Plan feature allows validators to document which validation components will be performed for a model validation, based on the bank's validation standards (Figure 3 matrix). The feature provides:

- **Lightweight planning** - Validators can quickly specify scope before/during validation
- **Deviation tracking** - Automatically flags when validators deviate from bank standards
- **Required rationale** - Forces documentation of why deviations are necessary
- **Standards-based defaults** - Pre-populates based on model risk tier expectations

## Business Context

### The Bank's Validation Standard

The bank has a validation standard that defines **11 sections** of a model validation report:

1. **Executive Summary** (5 subsections)
2. **Introduction** (4 subsections)
3. **Evaluation of Conceptual Soundness** (6 subsections)
4. **Ongoing Monitoring / Benchmarking** (3 subsections)
5. **Outcome Analysis / Model Assessment and Testing** (6 subsections)
6. **Model Risk: Limitations and Weakness**
7. **Conclusion**
8. **Model Deployment**
9. **Model Performance Monitoring Requirements**
10. **Reference**
11. **Appendix**

**Total: 30 validation components** seeded in the system.

### Figure 3 Matrix: Minimum Requirements for Validation Approach

The standard defines expectations per **risk tier** and **validation approach**:

| Risk Tier | Validation Approach | Example Expectation |
|-----------|-------------------|---------------------|
| **High** | Comprehensive | Most components Required |
| **Medium** | Standard | Many components Required, some IfApplicable |
| **Low** | Conceptual | Fewer Required, more IfApplicable |
| **Very Low** | Executive Summary | Minimal Required components |

Each component has one of three expectations per tier:
- **Required** - Must be performed
- **IfApplicable** - Perform if relevant to the model
- **NotExpected** - Typically not needed for this tier

## Data Model

### Tables

**validation_component_definitions** (Master List)
```sql
- component_id (PK)
- section_number (e.g., "1", "3")
- section_title (e.g., "Executive Summary")
- component_code (unique, e.g., "1.1", "3.4")
- component_title (e.g., "Summary", "Model Inputs and Outputs")
- is_test_or_analysis (boolean)
- expectation_high (Required/IfApplicable/NotExpected)
- expectation_medium (Required/IfApplicable/NotExpected)
- expectation_low (Required/IfApplicable/NotExpected)
- expectation_very_low (Required/IfApplicable/NotExpected)
- sort_order
- is_active
```

**validation_plans** (One per validation request)
```sql
- plan_id (PK)
- request_id (FK to validation_requests, unique)
- overall_scope_summary (text)
- material_deviation_from_standard (boolean)
- overall_deviation_rationale (text, required if deviation=true)
- created_at, updated_at
```

**validation_plan_components** (30 rows per plan)
```sql
- plan_component_id (PK)
- plan_id (FK to validation_plans)
- component_id (FK to validation_component_definitions)
- default_expectation (copied from master based on risk tier)
- planned_treatment (Planned/NotPlanned/NotApplicable)
- is_deviation (computed: true if planned != expected)
- rationale (text, required when is_deviation=true)
- additional_notes (text, optional)
- created_at, updated_at
```

### Relationships

```
ValidationRequest (1) <---> (1) ValidationPlan
ValidationPlan (1) <---> (many) ValidationPlanComponent
ValidationPlanComponent (many) <---> (1) ValidationComponentDefinition
```

## API Endpoints

Base path: `/validation-workflow`

### Get Component Definitions
```
GET /component-definitions
```
Returns all 30 validation components with Figure 3 matrix.

**Response:**
```json
[
  {
    "component_id": 1,
    "section_number": "1",
    "section_title": "Executive Summary",
    "component_code": "1.1",
    "component_title": "Summary",
    "is_test_or_analysis": false,
    "expectation_high": "Required",
    "expectation_medium": "Required",
    "expectation_low": "Required",
    "expectation_very_low": "Required",
    "sort_order": 1,
    "is_active": true
  },
  ...
]
```

### Create Validation Plan
```
POST /requests/{request_id}/plan
```

**Request Body:**
```json
{
  "overall_scope_summary": "This validation will focus on...",
  "material_deviation_from_standard": false,
  "overall_deviation_rationale": null,
  "components": []  // Empty = auto-create defaults for all 30
}
```

**Response:**
```json
{
  "plan_id": 1,
  "request_id": 1,
  "overall_scope_summary": "This validation will focus on...",
  "material_deviation_from_standard": false,
  "overall_deviation_rationale": null,
  "components": [
    {
      "plan_component_id": 1,
      "component_id": 1,
      "default_expectation": "Required",
      "planned_treatment": "Planned",
      "is_deviation": false,
      "rationale": null,
      "component_definition": { ... }
    },
    ...
  ],
  "model_id": 39,
  "model_name": "ALM QRM",
  "risk_tier": "High",
  "validation_approach": "Comprehensive"
}
```

### Get Validation Plan
```
GET /requests/{request_id}/plan
```

Returns the validation plan with all 30 components.

### Update Validation Plan
```
PATCH /requests/{request_id}/plan
```

**Request Body:**
```json
{
  "overall_scope_summary": "Updated scope...",
  "material_deviation_from_standard": false,
  "components": [
    {
      "component_id": 5,
      "planned_treatment": "NotPlanned",
      "rationale": "Not applicable because model is fully vendor-managed"
    }
  ]
}
```

### Delete Validation Plan
```
DELETE /requests/{request_id}/plan
```

Returns 204 No Content.

## Business Rules

### Deviation Detection

A component is considered a **deviation** when:

1. **Default Expectation = "Required"** AND **Planned Treatment = "NotPlanned" or "NotApplicable"**
   - Example: Bank requires Sensitivity Analysis for High-risk model, but validator marks it NotPlanned

2. **Default Expectation = "NotExpected"** AND **Planned Treatment = "Planned"**
   - Example: Bank doesn't expect Back-testing for Low-risk model, but validator plans to do it anyway

3. **Default Expectation = "IfApplicable"**
   - No automatic deviation - validator uses judgment

### Validation Rules

1. **Deviation rationale required**
   - API returns 400 Bad Request if `is_deviation=true` and `rationale` is blank
   - Frontend shows required field indicator and validates before save

2. **Material deviation rationale required**
   - If `material_deviation_from_standard=true`, must provide `overall_deviation_rationale`
   - Use this when changing the overall validation approach (e.g., treating Medium-risk model with Comprehensive approach)

3. **Plan immutability**
   - Plans can be created/updated until validation reaches certain statuses
   - Once in Pending Approval or Approved status, plan should be locked (future enhancement)

## UI/UX

### Location

The Validation Plan form is accessible via the **"Plan"** tab on the Validation Request Detail page:

```
/validation-workflow/{request_id} → Plan tab
```

### Form Structure

**Header Section:**
- Model Name (read-only)
- Risk Tier (read-only)
- Validation Approach (read-only, derived from risk tier)
- Overall Scope Summary (textarea)
- Material Deviation checkbox + rationale field (appears when checked)

**Components Table:**
- Grouped by Section (1-11)
- Columns:
  - Component (code + title)
  - Bank Expectation (badge: Required/IfApplicable/NotExpected)
  - Planned Status (dropdown: Planned/NotPlanned/NotApplicable)
  - Rationale (textarea, required when deviating)

**Visual Indicators:**
- ⚠️ Warning icon for deviations
- Yellow row highlighting for deviations
- Color-coded expectation badges (blue=Required, gray=IfApplicable, red=NotExpected)

### Default Behavior

To minimize validator effort:

1. **Auto-create defaults** - When creating a plan with empty components array, API creates all 30 with smart defaults:
   - Required → Planned
   - NotExpected → NotPlanned
   - IfApplicable → Planned (validator can change)

2. **Real-time deviation detection** - Dropdown change immediately shows/hides rationale field and deviation flag

3. **Validation on save** - Frontend validates all deviations have rationale before submitting

## Examples

### Example 1: High-Risk Model - Standard Validation

Model: Credit Risk RWA Model
Risk Tier: High
Validation Approach: Comprehensive

**Components (selected):**

| Component | Bank Expectation | Planned | Deviation? | Rationale |
|-----------|------------------|---------|------------|-----------|
| 1.1 Summary | Required | Planned | No | - |
| 3.5 Alternative Modelling | IfApplicable | NotApplicable | No | - |
| 4.3 Sensitivity Analysis | Required | Planned | No | - |
| 5.1 Back-testing | IfApplicable | Planned | No | - |

**Result:** No deviations, validator accepted all Required components.

### Example 2: High-Risk Model - Deviation from Standard

Model: Trading Book VaR
Risk Tier: High
Validation Approach: Comprehensive

**Deviation:**

| Component | Bank Expectation | Planned | Deviation? | Rationale |
|-----------|------------------|---------|------------|-----------|
| 4.2 Process Verification / Replication Testing | Required | NotPlanned | **YES ⚠️** | "Model is a licensed vendor solution (Bloomberg BVAL). Vendor provides certification of calculation accuracy. Replication testing not feasible without source code access. Will rely on vendor certification plus independent benchmarking." |

**Material Deviation:** No (still following Comprehensive approach overall)

### Example 3: Medium-Risk Model - Scaled Up Approach

Model: Customer Behavior Model
Risk Tier: Medium
Validation Approach: Standard → **Upgraded to Comprehensive**

**Material Deviation:** Yes
**Overall Rationale:** "Model drives critical CCAR balance sheet projections. Recent regulatory feedback indicated Standard approach insufficient. Performing Comprehensive validation to address regulator concerns."

**Deviations:**

| Component | Bank Expectation | Planned | Deviation? | Rationale |
|-----------|------------------|---------|------------|-----------|
| 3.5 Alternative Modelling | IfApplicable | Planned | No | Beneficial for regulator engagement |
| 5.1 Back-testing | IfApplicable | Planned | No | Requested by regulator |
| 5.3 Boundary Testing | IfApplicable | Planned | No | Best practice for CCAR models |

**Result:** Material deviation flag set due to upgrade from Standard → Comprehensive.

## Configuration & Maintenance

### Adding New Components

To add a new validation component to the standard:

1. **Database:** Insert into `validation_component_definitions`
```sql
INSERT INTO validation_component_definitions (
    section_number, section_title, component_code, component_title,
    is_test_or_analysis, expectation_high, expectation_medium,
    expectation_low, expectation_very_low, sort_order, is_active
) VALUES (
    '12', 'Model Change Management', '12.1', 'Change Control Documentation',
    false, 'Required', 'Required', 'IfApplicable', 'NotExpected', 31, true
);
```

2. **Existing Plans:** New component will not appear in existing plans (historical integrity preserved)

3. **New Plans:** New component will auto-appear in newly created plans

### Updating Expectations (Figure 3 Matrix)

To change expectations (e.g., making Sensitivity Analysis Required for Medium-risk):

```sql
UPDATE validation_component_definitions
SET expectation_medium = 'Required'
WHERE component_code = '4.3';
```

**Impact:**
- Existing plans: No change (preserves historical decisions)
- New plans: Will use updated expectation as default

### Deactivating Components

To deprecate a component without deleting:

```sql
UPDATE validation_component_definitions
SET is_active = false
WHERE component_code = '10';
```

Component will not appear in new plans but remains in existing plans.

## Testing

### API Tests

See `/tmp/test_validation_plan.sh` for comprehensive API tests:

```bash
# Run validation plan API tests
./test_validation_plan.sh
```

**Coverage:**
- ✅ Get component definitions (30 components)
- ✅ Create plan with auto-defaults
- ✅ Get plan
- ✅ Update plan with deviations
- ✅ Delete plan

### Frontend Testing

Manual testing checklist:

1. ✅ Navigate to Validation Request detail page
2. ✅ Click "Plan" tab
3. ✅ Click "Create Validation Plan" (if not exists)
4. ✅ Verify all 30 components appear grouped by section
5. ✅ Change a Required component to NotPlanned → verify deviation flag appears
6. ✅ Enter rationale for deviation
7. ✅ Try to save without rationale → verify error
8. ✅ Save with rationale → verify success
9. ✅ Reload page → verify plan persists

## Future Enhancements

### Phase 1 Completed ✅
- [x] Master component definitions with Figure 3 matrix
- [x] Validation plan CRUD APIs
- [x] Deviation detection and rationale enforcement
- [x] Frontend form with visual deviation indicators
- [x] Auto-default behavior to minimize effort

### Phase 2 - Component Versioning & Grandfathering ✅

**Status**: Complete

#### Completed Features

**Component Definition Versioning**
- [x] **Configuration snapshots** - System tracks versions of component definitions over time
- [x] **Grandfathering support** - Plans lock to configuration version when submitted for review
- [x] **Historical compliance** - Auditors can see what standards existed at time of validation
- [x] **Plan locking** - Automatic lock when validation moves to Review/Pending Approval/Approved
- [x] **Plan unlocking** - Automatic unlock when reviewer/approver sends validation back
- [x] **Audit trail** - Complete logging of lock/unlock events with reasons

**Plan Templating**
- [x] **Plan Templates (Backend)** - API endpoints for template suggestions and creation
- [x] **Plan Templates (Frontend)** - UI integration with modal for template selection
- [x] **Configuration awareness** - Warnings when template uses different requirements version
- [x] **Smart recalculation** - Uses active configuration expectations, not template's

**Admin UI for Component Management**
- [x] **Component Definitions Page** - View and edit Figure 3 validation matrix (`/component-definitions`)
- [x] **Inline editing** - Update component expectations by risk tier
- [x] **Configuration publishing** - Create new configuration snapshots with audit logs
- [x] **Admin-only access** - Role-based security for configuration changes
- [x] **API endpoints** - Complete backend support for CRUD operations
- [x] **Configuration History View** - Dedicated page showing all configuration versions (`/configuration-history`)

#### Optional Future Enhancements (Phase 3)

- [ ] **Bulk Operations** - Apply same rationale to multiple components
- [ ] **Export Plan** - PDF export of validation plan for documentation
- [ ] **Smart Suggestions** - AI-powered rationale suggestions based on model type
- [ ] **Compliance Reports** - Track deviation trends across all validations

#### Architecture: Configuration Versioning

**Purpose**: Ensure validation plans remain compliant with standards that existed at the time of validation, even if standards change later.

**Three-Table Design**:

1. **component_definition_configurations** - Configuration versions
   ```sql
   - config_id (PK)
   - config_name (e.g., "Initial SR 11-7 Configuration", "Q2 2026 SR 11-7 Update")
   - description (what changed in this version)
   - effective_date (when this configuration took effect)
   - created_by_user_id (admin who published it)
   - created_at
   - is_active (only one configuration is active at a time)
   ```

2. **component_definition_config_items** - Snapshots of individual components
   ```sql
   - config_item_id (PK)
   - config_id (FK to configurations)
   - component_id (FK to component_definitions)
   - expectation_high/medium/low/very_low (Figure 3 matrix values at this version)
   - section_number, section_title, component_code, component_title (metadata snapshot)
   - is_test_or_analysis, sort_order, is_active
   ```

3. **validation_plans** - Updated with versioning fields
   ```sql
   - config_id (FK to configurations) - Links plan to configuration version
   - locked_at (timestamp when plan was locked)
   - locked_by_user_id (user who triggered the lock)
   ```

**How It Works**:

1. **Initial State**: System has one active configuration (config_id=1) with 30 component snapshots
2. **Plan Creation**: New plans use current active configuration to determine default expectations
3. **Plan Editing**: Plans remain editable (config_id=null, locked_at=null)
4. **Plan Locking**: When validation moves to Review/Pending Approval/Approved:
   - Plan.config_id = active configuration ID
   - Plan.locked_at = current timestamp
   - Plan.locked_by_user_id = user who triggered status change
   - Audit log created: "Plan locked when validation moved to Review"
5. **Plan Unlocking**: When reviewer/approver sends validation back (e.g., Review → In Progress):
   - Plan.locked_at = null
   - Plan.locked_by_user_id = null
   - Plan.config_id preserved (maintains historical link)
   - Audit log created: "Plan unlocked when validation sent back to In Progress"
6. **Configuration Changes**: Admin publishes new configuration (e.g., config_id=2):
   - New configuration becomes active
   - New plans use new configuration for defaults
   - Locked plans remain linked to original configuration (grandfathering)

**Example Scenario**:

```
Timeline:
- Jan 2025: Initial config created (config_id=1)
  - Component 4.3 "Sensitivity Analysis" = Required for Medium-risk

- Feb 2025: Validation #123 (Medium-risk model)
  - Creates plan → uses config_id=1
  - Component 4.3 default = Required
  - Validator marks it "Planned"
  - Moves to Review → Plan locks to config_id=1

- Jun 2025: Bank updates standards (new config_id=2)
  - Component 4.3 "Sensitivity Analysis" = IfApplicable for Medium-risk (relaxed)

- Jul 2025: Auditor reviews Validation #123
  - Plan shows config_id=1
  - Component 4.3 expectation was "Required" at time of validation
  - Plan is compliant with standards that existed in Feb 2025
  - Auditor does NOT incorrectly flag deviation based on current standards

- Aug 2025: New Validation #456 (Medium-risk model)
  - Creates plan → uses config_id=2 (active)
  - Component 4.3 default = IfApplicable (new standard)
```

**Benefits**:
- ✅ Historical accuracy - Plans reflect standards at time of validation
- ✅ Audit compliance - Regulators can see what was required when
- ✅ No retroactive non-compliance - Old plans don't become "wrong" when standards change
- ✅ Complete audit trail - Lock/unlock events logged with reasons

#### Database Migration

**Migration**: `373700cdc73d_add_component_definition_versioning_and_`

**Applied**: Yes

**Changes**:
- Created `component_definition_configurations` table
- Created `component_definition_config_items` table
- Added `config_id`, `locked_at`, `locked_by_user_id` to `validation_plans`
- Set up foreign key relationships

#### Initial Configuration

**Seed Script**: Updated to create initial configuration version

**What It Does**:
1. Creates initial configuration: "Initial SR 11-7 Configuration"
2. Snapshots all 30 validation components with current expectations
3. Sets effective_date to today
4. Marks as active configuration

**Result**: System has config_id=1 with 30 component snapshots ready for plan locking

#### Plan Locking Logic

**Location**: [api/app/api/validation_workflow.py:1415-1470](api/app/api/validation_workflow.py#L1415-L1470)

**Trigger**: Status transitions in `update_validation_request_status` endpoint

**Lock Conditions**:
- Validation moves TO: Review, Pending Approval, or Approved
- Plan exists and is not already locked (locked_at is null)

**Lock Actions**:
1. Set plan.config_id = active configuration ID
2. Set plan.locked_at = current timestamp
3. Set plan.locked_by_user_id = user who triggered transition
4. Create audit log: entity_type="ValidationPlan", action="LOCK"

**Unlock Conditions**:
- Validation moves FROM: Review, Pending Approval, or Approved
- Validation moves TO: Intake, Planning, or In Progress (sendback scenario)
- Plan is currently locked (locked_at is not null)

**Unlock Actions**:
1. Set plan.locked_at = null
2. Set plan.locked_by_user_id = null
3. Preserve plan.config_id (maintains historical link)
4. Create audit log: entity_type="ValidationPlan", action="UNLOCK"

**Example Lock Event (audit log)**:
```json
{
  "entity_type": "ValidationPlan",
  "entity_id": 1,
  "action": "LOCK",
  "user_id": 5,
  "changes": {
    "config_id": 1,
    "config_name": "Initial SR 11-7 Configuration",
    "reason": "Plan locked when validation moved to Review",
    "old_status": "In Progress",
    "new_status": "Review"
  }
}
```

**Example Unlock Event (audit log)**:
```json
{
  "entity_type": "ValidationPlan",
  "entity_id": 1,
  "action": "UNLOCK",
  "user_id": 5,
  "changes": {
    "reason": "Plan unlocked when validation sent back to In Progress",
    "previous_status": "Review",
    "new_status": "In Progress",
    "config_id_preserved": 1
  }
}
```

#### Plan Templating ✅

**Business Requirement**: When creating a new validation plan, if a previous validation of the same Validation Type exists for this model, offer to automatically use that previous plan as a template.

**Status**: Complete ✅

**Implementation** (see [COMPONENT_VERSIONING.md](COMPONENT_VERSIONING.md) for full details):

1. **✅ Template Suggestion API**: `GET /validation-workflow/requests/{request_id}/plan/template-suggestions`
   - Finds previous APPROVED validations with same Validation Type and overlapping models
   - Returns up to 5 suggestions ordered by most recent
   - **Configuration awareness**: Includes `is_different_config` flag to warn if template uses outdated requirements
   - Response includes: source IDs, validation type, models, completion date, validator, component/deviation counts, config details

2. **✅ Create with Template**: Enhanced `POST /validation-workflow/requests/{request_id}/plan`
   - Added optional `template_plan_id` parameter
   - Copies: `overall_scope_summary`, `material_deviation_from_standard`, `overall_deviation_rationale`
   - Copies: `planned_treatment` and `rationale` for each component
   - **Smart recalculation**: Uses ACTIVE configuration's expectations (not template's)
   - Recalculates `is_deviation` based on current requirements
   - Creates audit log: `CREATE_FROM_TEMPLATE` with template metadata

3. **✅ UI Integration**: Frontend modal to display template suggestions
   - Automatically fetches templates when no plan exists
   - Shows modal with template options including all key metadata
   - Highlights configuration version warnings with yellow banner when `is_different_config=true`
   - Allows user to select template or create from scratch
   - Passes selected `template_plan_id` to create endpoint
   - Displays formatted dates, validator names, component/deviation counts

**Configuration Version Handling**:
- Template shows original `config_id` and `config_name` it was created under
- `is_different_config` flag warns user if requirements changed since template
- Component expectations are recalculated using ACTIVE config (not template's)
- This ensures new plan complies with current standards while preserving validator decisions

**Example Template Suggestion**:
```json
{
  "source_request_id": 5,
  "source_plan_id": 3,
  "validation_type": "Annual Review",
  "model_names": ["Credit Risk RWA Model"],
  "completion_date": "2024-11-15",
  "validator_name": "Sarah Chen",
  "component_count": 30,
  "deviations_count": 2,
  "config_id": 1,
  "config_name": "Initial SR 11-7 Configuration",
  "is_different_config": false  // ✅ Safe - same requirements
}
```

**Audit Trail**:
```json
{
  "entity_type": "ValidationPlan",
  "entity_id": 7,
  "action": "CREATE_FROM_TEMPLATE",
  "user_id": 3,
  "changes": {
    "template_plan_id": 3,
    "template_request_id": 5,
    "template_config_id": 1,
    "template_config_name": "Initial SR 11-7 Configuration"
  }
}
```

#### Component Definition Management ✅

**Business Requirement**: Admins must be able to update validation component definitions (Figure 3 matrix) through the UI instead of SQL, and publish new configuration versions to make changes effective.

**Status**: Complete ✅

**Implementation**:

1. **✅ Admin UI Page**: `/component-definitions` - Dedicated page for managing validation standards
   - **Component editing**: Inline editing of expectations by risk tier
   - **Grouped by section**: Components organized by SR 11-7 sections
   - **Color-coded badges**: Visual indicators for Required/IfApplicable/NotExpected
   - **Save with audit logging**: All changes tracked with before/after values
   - **Configuration publishing**: Modal to create new configuration snapshots

2. **✅ Backend API Endpoints**:
   - `GET /validation-workflow/component-definitions` - List all components
   - `GET /validation-workflow/component-definitions/{id}` - Get single component
   - `PATCH /validation-workflow/component-definitions/{id}` - Update component (Admin only)
   - `GET /validation-workflow/configurations` - List all configuration versions
   - `GET /validation-workflow/configurations/{id}` - Get configuration with all snapshots
   - `POST /validation-workflow/configurations/publish` - Publish new configuration (Admin only)

3. **✅ Admin Workflow**:
   - Admin edits component expectations in UI
   - Changes saved immediately to `validation_component_definitions` table
   - Changes not retroactive - existing plans unaffected
   - When ready, admin publishes new configuration version
   - System creates snapshot of all 30 components
   - Previous active configuration marked inactive (preserved for history)
   - New configuration becomes active
   - Future validation plans use new configuration
   - Existing locked plans remain linked to their original configuration

4. **✅ Security & Authorization**:
   - Component updates: Admin role required
   - Configuration publishing: Admin role required
   - Role check via `check_admin(current_user)` function
   - Complete audit trail of all changes

**Example Configuration Publish**:
```json
{
  "config_name": "Q4 2025 SR 11-7 Updates",
  "description": "Updated expectations for data quality components per regulatory guidance",
  "effective_date": "2025-12-01"
}
```

**Result**: Creates new configuration (e.g., config_id=2), snapshots all 30 components, marks as active, deactivates previous config, creates audit log.

5. **✅ Configuration History View**: `/configuration-history` - View all configuration versions
   - **Version timeline**: All published configurations displayed in reverse chronological order
   - **Expandable details**: Click to view complete Figure 3 matrix for each version
   - **Active indicator**: Clear badge showing which configuration is currently active
   - **Grouped by section**: Component snapshots organized by SR 11-7 sections
   - **Color-coded expectations**: Same visual indicators as component definitions page
   - **Admin-only access**: Only administrators can view configuration history
   - **Audit compliance**: Enables auditors to verify historical standards

#### Next Steps

1. ✅ Test plan locking/unlocking functionality
2. ✅ Implement plan templating backend API
3. ✅ Integrate plan templating in frontend UI (ValidationPlanForm)
4. ✅ Create Admin API endpoints for component definition management
5. ✅ Create Admin UI page for managing component definitions
6. ✅ Create configuration version history view

### Phase 3 - Additional Improvements
- [ ] **Version History** - Track plan changes over time (change log)
- [ ] **Export Plan** - PDF export of validation plan for documentation
- [ ] **Smart Suggestions** - AI-powered rationale suggestions based on model type
- [ ] **Compliance Reports** - Track deviation trends across all validations

## Technical Details

### Files Modified/Created

**Backend:**
- `api/app/models/validation.py` - Added 3 new models (lines 665-748)
- `api/app/schemas/validation.py` - Added plan schemas (lines 502-591)
- `api/app/api/validation_workflow.py` - Added 4 endpoints (lines 3117-3516)
- `api/app/seed.py` - Added component seeding (lines 227-330)
- `api/alembic/versions/cc568f455fb3_add_validation_plan_tables.py` - Migration

**Frontend:**
- `web/src/components/ValidationPlanForm.tsx` - New component (460 lines)
- `web/src/pages/ValidationRequestDetailPage.tsx` - Added Plan tab integration

### Performance Considerations

- **Component definitions:** Cached in memory, 30 rows total (negligible)
- **Plan retrieval:** Single query with joinedload for all 30 components
- **Plan creation:** Bulk insert of 30 components in single transaction
- **Expected load:** ~100 validations/year × 30 components = 3,000 plan component rows/year

### Security

- **Authorization:** Validator or Admin role required for create/update/delete
- **Row-level security:** Users can view plans for validations they have access to
- **Audit trail:** created_at/updated_at timestamps on all tables

## Support & Documentation

- **User Guide:** See CLAUDE.md section on Validation Plan
- **API Documentation:** http://localhost:8001/docs (FastAPI auto-generated)
- **Questions:** Contact Model Risk Management team
