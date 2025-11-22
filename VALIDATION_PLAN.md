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

### Phase 2 - Potential Improvements
- [ ] **Admin UI** - Manage component definitions via UI instead of SQL
- [ ] **Version History** - Track plan changes over time
- [ ] **Plan Templates** - Save common deviation patterns for reuse
- [ ] **Approval Workflow** - Lock plan when validation enters Review status
- [ ] **Bulk Operations** - Apply same rationale to multiple components
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
