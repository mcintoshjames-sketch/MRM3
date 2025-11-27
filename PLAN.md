# Monitoring Results Feature Design Plan

## Overview
Add functionality to capture, calculate, and report on monitoring results for specific monitoring periods (cycles). This enables tracking model performance over time with Red/Yellow/Green (R/Y/G) outcomes.

## Data Model

### New Tables

#### 1. MonitoringCycle
Represents one monitoring period for a plan.

```sql
CREATE TABLE monitoring_cycles (
    cycle_id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES monitoring_plans(plan_id) ON DELETE CASCADE,

    -- Period definition
    period_start_date DATE NOT NULL,
    period_end_date DATE NOT NULL,
    submission_due_date DATE NOT NULL,
    report_due_date DATE NOT NULL,

    -- Workflow status
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    -- Status values: PENDING, DATA_COLLECTION, UNDER_REVIEW, COMPLETED, CANCELLED

    -- Assignment (optional override of plan's data_provider)
    assigned_to_user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,

    -- Submission tracking
    submitted_at TIMESTAMP,
    submitted_by_user_id INTEGER REFERENCES users(user_id),

    -- Completion tracking
    completed_at TIMESTAMP,
    completed_by_user_id INTEGER REFERENCES users(user_id),

    -- Notes
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_period CHECK (period_end_date >= period_start_date),
    CONSTRAINT valid_due_dates CHECK (report_due_date >= submission_due_date)
);

CREATE INDEX idx_monitoring_cycles_plan_id ON monitoring_cycles(plan_id);
CREATE INDEX idx_monitoring_cycles_status ON monitoring_cycles(status);
```

#### 2. MonitoringCycleApproval
Approval records for monitoring cycles (similar to ValidationApproval but simplified).

```sql
CREATE TABLE monitoring_cycle_approvals (
    approval_id SERIAL PRIMARY KEY,
    cycle_id INTEGER NOT NULL REFERENCES monitoring_cycles(cycle_id) ON DELETE CASCADE,

    -- Approver info
    approver_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,

    -- Approval type: 'Global' or 'Regional'
    approval_type VARCHAR(20) NOT NULL DEFAULT 'Global',

    -- Region for regional approvals (NULL for Global)
    region_id INTEGER REFERENCES regions(region_id) ON DELETE SET NULL,

    -- Historical context: which region did approver represent at approval time
    represented_region_id INTEGER REFERENCES regions(region_id) ON DELETE SET NULL,

    -- Approval status
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    approval_status VARCHAR(50) NOT NULL DEFAULT 'Pending',  -- Pending, Approved, Rejected
    comments TEXT,
    approved_at TIMESTAMP,

    -- Voiding (Admin can void approval requirements)
    voided_by_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    void_reason TEXT,
    voided_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Unique constraint: one approval per type per region per cycle
    CONSTRAINT unique_cycle_approval UNIQUE (cycle_id, approval_type, region_id)
);

CREATE INDEX idx_monitoring_cycle_approvals_cycle ON monitoring_cycle_approvals(cycle_id);
CREATE INDEX idx_monitoring_cycle_approvals_status ON monitoring_cycle_approvals(approval_status);
```

#### 3. MonitoringResult
Individual metric result for a cycle.

```sql
CREATE TABLE monitoring_results (
    result_id SERIAL PRIMARY KEY,
    cycle_id INTEGER NOT NULL REFERENCES monitoring_cycles(cycle_id) ON DELETE CASCADE,
    plan_metric_id INTEGER NOT NULL REFERENCES monitoring_plan_metrics(metric_id) ON DELETE CASCADE,

    -- Optional model-specific result (when plan covers multiple models)
    model_id INTEGER REFERENCES models(model_id) ON DELETE CASCADE,

    -- Quantitative data
    numeric_value FLOAT,

    -- Qualitative/Outcome data (taxonomy value for R/Y/G)
    outcome_value_id INTEGER REFERENCES taxonomy_values(value_id),

    -- Calculated outcome (GREEN, YELLOW, RED, N/A)
    calculated_outcome VARCHAR(20),

    -- Supporting narrative (required for qualitative, optional for quantitative)
    narrative TEXT,

    -- Additional structured data (JSON for flexibility)
    supporting_data JSONB,

    -- Audit fields
    entered_by_user_id INTEGER NOT NULL REFERENCES users(user_id),
    entered_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Unique constraint: one result per metric per model per cycle
    CONSTRAINT unique_result UNIQUE (cycle_id, plan_metric_id, model_id)
);

CREATE INDEX idx_monitoring_results_cycle ON monitoring_results(cycle_id);
CREATE INDEX idx_monitoring_results_metric ON monitoring_results(plan_metric_id);
CREATE INDEX idx_monitoring_results_model ON monitoring_results(model_id);
CREATE INDEX idx_monitoring_results_outcome ON monitoring_results(calculated_outcome);
```

### Cycle Status Workflow

```
PENDING → DATA_COLLECTION → UNDER_REVIEW → PENDING_APPROVAL → APPROVED
                                      ↘ CANCELLED          ↗
```

- **PENDING**: Cycle created, awaiting start of data collection period
- **DATA_COLLECTION**: Active data entry period
- **UNDER_REVIEW**: All results submitted, team is reviewing data quality
- **PENDING_APPROVAL**: Awaiting required approvals (Global + Regional)
- **APPROVED**: All approvals obtained, cycle complete and locked
- **CANCELLED**: Terminated before completion

### Approval Workflow

When a cycle moves to PENDING_APPROVAL:
1. System auto-creates approval requirements based on models in the plan:
   - **Global Approval**: Always required (1 approval)
   - **Regional Approvals**: One per region where models are deployed (uses model_regions table)
2. Approvers are not pre-assigned - any user with the appropriate approver role can approve
3. When all required approvals are obtained, cycle auto-transitions to APPROVED
4. Admin can void approval requirements with documented reason

**Approval Logic:**
- Global Approval: Required for all cycles
- Regional Approvals: Determined by regions where models in the plan's scope are deployed
  - Query: `SELECT DISTINCT region_id FROM model_regions WHERE model_id IN (plan.model_ids)`
  - Only regions with `requires_approval = TRUE` generate approval requirements

### Outcome Calculation Logic

For **Quantitative** metrics (based on MonitoringPlanMetric thresholds):

```python
def calculate_outcome(value: float, metric: MonitoringPlanMetric) -> str:
    """
    Threshold interpretation:
    - GREEN: Within acceptable range (not triggering yellow or red)
    - YELLOW: Warning zone (yellow_min <= value <= yellow_max OR outside green but not red)
    - RED: Critical zone (value < red_min OR value > red_max)

    The thresholds support different scenarios:
    1. Lower is better (e.g., error rate): red_max=0.1, yellow_max=0.05
    2. Higher is better (e.g., accuracy): red_min=0.8, yellow_min=0.9
    3. Range-based (e.g., PSI): red_min=0.1, red_max=0.25, yellow_min=0.05, yellow_max=0.1
    """
    if value is None:
        return "N/A"

    # Check red thresholds first (highest severity)
    if metric.red_min is not None and value < metric.red_min:
        return "RED"
    if metric.red_max is not None and value > metric.red_max:
        return "RED"

    # Check yellow thresholds
    if metric.yellow_min is not None and value < metric.yellow_min:
        return "YELLOW"
    if metric.yellow_max is not None and value > metric.yellow_max:
        return "YELLOW"

    # If passed all threshold checks, it's green
    return "GREEN"
```

For **Qualitative** and **Outcome Only** metrics:
- User directly selects the outcome (GREEN/YELLOW/RED)
- Qualitative requires narrative/rationale
- Outcome Only accepts optional notes

## API Endpoints

### Cycle Management

```
POST   /monitoring/plans/{plan_id}/cycles
       - Create new cycle for current period
       - Auto-calculates period based on plan frequency and last cycle
       - Request: { assigned_to_user_id?, notes? }

GET    /monitoring/plans/{plan_id}/cycles
       - List all cycles for a plan
       - Query params: status?, include_results=false

GET    /monitoring/cycles/{cycle_id}
       - Get cycle details with all results

PATCH  /monitoring/cycles/{cycle_id}
       - Update cycle (assignment, notes, status)
       - Can only change status through defined transitions

DELETE /monitoring/cycles/{cycle_id}
       - Delete cycle (only if PENDING or CANCELLED, no results)
```

### Result Entry

```
POST   /monitoring/cycles/{cycle_id}/results
       - Enter result for a metric
       - Request: {
           plan_metric_id: int,
           model_id?: int,          // Optional for multi-model plans
           numeric_value?: float,   // For quantitative
           outcome_value_id?: int,  // For qualitative/outcome-only
           narrative?: string,      // Required for qualitative
           supporting_data?: object
         }
       - Returns: result with calculated_outcome

PATCH  /monitoring/results/{result_id}
       - Update existing result
       - Only allowed when cycle not COMPLETED

DELETE /monitoring/results/{result_id}
       - Delete result
       - Only allowed when cycle not COMPLETED

GET    /monitoring/cycles/{cycle_id}/results
       - Get all results for a cycle
       - Includes metric details and KPM info
```

### Workflow Actions

```
POST   /monitoring/cycles/{cycle_id}/start
       - Move cycle from PENDING to DATA_COLLECTION

POST   /monitoring/cycles/{cycle_id}/submit
       - Move cycle from DATA_COLLECTION to UNDER_REVIEW
       - Validates all required metrics have results

POST   /monitoring/cycles/{cycle_id}/request-approval
       - Move cycle from UNDER_REVIEW to PENDING_APPROVAL
       - Auto-creates approval requirements (Global + Regional)
       - Returns list of required approvals

POST   /monitoring/cycles/{cycle_id}/cancel
       - Cancel cycle (with reason)
       - Only allowed before APPROVED
```

### Approval Endpoints

```
GET    /monitoring/cycles/{cycle_id}/approvals
       - Get all approval requirements for a cycle
       - Returns: [{ approval_id, approval_type, region, status, approver, ... }]

POST   /monitoring/cycles/{cycle_id}/approvals/{approval_id}/approve
       - Submit approval
       - Request: { comments? }
       - Auto-checks if all approvals complete → transitions to APPROVED

POST   /monitoring/cycles/{cycle_id}/approvals/{approval_id}/reject
       - Reject approval (sends back to UNDER_REVIEW)
       - Request: { comments: string }  // Required

POST   /monitoring/cycles/{cycle_id}/approvals/{approval_id}/void
       - Admin voids an approval requirement
       - Request: { void_reason: string }  // Required
       - Auto-checks if remaining approvals complete → transitions to APPROVED
```

### Reporting

```
GET    /monitoring/metrics/{plan_metric_id}/trend
       - Get time series data for a specific metric
       - Query params: model_id?, start_date?, end_date?
       - Returns: [{ period_end_date, value, outcome, ... }]

GET    /monitoring/plans/{plan_id}/performance-summary
       - Get aggregate performance across all models
       - Query params: cycles=5 (last N cycles)
       - Returns: { green_count, yellow_count, red_count, by_metric: [...] }

GET    /monitoring/plans/{plan_id}/cycles/{cycle_id}/export
       - Export cycle results to CSV
```

## Permission Model

| Role | Cycles | Results | Approvals | View |
|------|--------|---------|-----------|------|
| Admin | Full CRUD | Full CRUD | Approve, Void | All |
| Team Member (of plan's team) | Full CRUD | Full CRUD | Request Approval | All |
| Data Provider (assigned to cycle) | View, Submit | Create, Update own | - | All |
| Global Approver | View | View | Approve Global | All |
| Regional Approver | View | View | Approve for their region | All |
| Other Users | View | View | - | All |

### Approver Roles
- **Global Approver**: Can approve Global approval requirements for any cycle
- **Regional Approver**: Can approve Regional approval requirements for regions they're assigned to
- Uses existing `approver_roles` and `user_regions` tables from validation workflow

## Frontend UX

### 1. Monitoring Plan Detail Page - Cycles Tab

```
┌─────────────────────────────────────────────────────────────┐
│ Monitoring Plan: Credit Risk Model Monitoring               │
├─────────────────────────────────────────────────────────────┤
│ [Overview] [Models] [Metrics] [Cycles] [History]            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  CURRENT CYCLE                                   [+ New]    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Q3 2025 (Jul-Sep)              Status: ● Pending Approval│
│  │ Submission Due: 2025-10-15     Report Due: 2025-11-14 │  │
│  │ Assigned to: John Smith                               │  │
│  │                                                       │  │
│  │  Results: 8/8 metrics entered                         │  │
│  │  Summary: 🟢 5  🟡 2  🔴 1                            │  │
│  │                                                       │  │
│  │  APPROVALS: 1/3 obtained                              │  │
│  │  ✓ Global  ● Americas  ● EMEA                         │  │
│  │                                                       │  │
│  │  [View Results]  [View Approvals]                     │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  PREVIOUS CYCLES                                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Q2 2025  │ Apr-Jun  │ ✓ Approved   │ 🟢5 🟡2 🔴1   │    │
│  │ Q1 2025  │ Jan-Mar  │ ✓ Approved   │ 🟢6 🟡2 🔴0   │    │
│  │ Q4 2024  │ Oct-Dec  │ ✓ Approved   │ 🟢4 🟡3 🔴1   │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. Results Entry View

```
┌─────────────────────────────────────────────────────────────┐
│ Enter Results - Q3 2025                        [Save All]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  MODEL: Credit Risk Scorecard v2.1                          │
│                                                             │
│  ┌─ QUANTITATIVE METRICS ────────────────────────────────┐  │
│  │                                                       │  │
│  │  PSI (Population Stability Index)                     │  │
│  │  Thresholds: 🟢 <0.10  🟡 0.10-0.25  🔴 >0.25        │  │
│  │  Value: [  0.08  ]                   → 🟢 GREEN      │  │
│  │  Notes: [                                        ]    │  │
│  │                                                       │  │
│  │  ──────────────────────────────────────────────────   │  │
│  │                                                       │  │
│  │  Gini Coefficient                                     │  │
│  │  Thresholds: 🔴 <0.30  🟡 0.30-0.40  🟢 >0.40        │  │
│  │  Value: [  0.45  ]                   → 🟢 GREEN      │  │
│  │  Notes: [                                        ]    │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─ QUALITATIVE METRICS ─────────────────────────────────┐  │
│  │                                                       │  │
│  │  Data Quality Assessment                              │  │
│  │  Guidance: Evaluate completeness and accuracy of      │  │
│  │            input data against specifications.         │  │
│  │                                                       │  │
│  │  Outcome: [ 🟢 Green ▼ ]                              │  │
│  │                                                       │  │
│  │  Rationale (required):                                │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │ All data sources validated. Coverage at 99.2%  │  │  │
│  │  │ with no significant gaps identified.           │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3. Approval Status View (when cycle is in PENDING_APPROVAL)

```
┌─────────────────────────────────────────────────────────────┐
│ Cycle Approvals - Q3 2025                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  APPROVAL STATUS                                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                                                       │  │
│  │  Global Approval                                      │  │
│  │  Status: ● Pending                                    │  │
│  │  [Approve]  [Reject]                                  │  │
│  │                                                       │  │
│  │  ─────────────────────────────────────────────────    │  │
│  │                                                       │  │
│  │  Americas Regional Approval                           │  │
│  │  Status: ✓ Approved                                   │  │
│  │  Approved by: John Smith on 2025-10-18                │  │
│  │  Comments: "Q3 results reviewed and accepted"         │  │
│  │                                                       │  │
│  │  ─────────────────────────────────────────────────    │  │
│  │                                                       │  │
│  │  EMEA Regional Approval                               │  │
│  │  Status: ● Pending                                    │  │
│  │  [Approve]  [Reject]                                  │  │
│  │                                                       │  │
│  │  ─────────────────────────────────────────────────    │  │
│  │                                                       │  │
│  │  APAC Regional Approval                               │  │
│  │  Status: ○ Voided                                     │  │
│  │  Voided by: Admin on 2025-10-17                       │  │
│  │  Reason: "No APAC deployments for these models"       │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  Progress: 1/2 required approvals obtained                  │
│  [████████████░░░░░░░░░░░░] 50%                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4. Trend View (for a specific metric)

```
┌─────────────────────────────────────────────────────────────┐
│ PSI Trend - Credit Risk Scorecard                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  0.30 ┤                               ╭──── Red Zone        │
│       │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│                     │
│  0.25 ┼─────────────────────────────────────────────────    │
│       │▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒│  Yellow Zone       │
│  0.10 ┼─────────────────────────────────────────────────    │
│       │                           ●   │                     │
│  0.08 ┤                       ●       │                     │
│       │                   ●           │                     │
│  0.05 ┤               ●               │  Green Zone         │
│       │           ●                   │                     │
│  0.00 └───────────────────────────────┴─────────────────    │
│        Q4'24  Q1'25  Q2'25  Q3'25                           │
│                                                             │
│  Summary: PSI has remained stable in Green zone.            │
│  Latest: 0.08 (Q3 2025)  Trend: Stable                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Database & Core API (Backend) ✅ COMPLETE
1. ✅ Create migration for monitoring_cycles, monitoring_cycle_approvals, and monitoring_results tables
2. ✅ Add MonitoringCycle, MonitoringCycleApproval, and MonitoringResult SQLAlchemy models
3. ✅ Add Pydantic schemas for cycles, approvals, and results
4. ✅ Implement CRUD endpoints for cycles
5. ✅ Implement result entry endpoints with outcome calculation
6. ✅ Add permission checks (data provider, team member, admin)
7. ✅ Write pytest tests (63 tests in test_monitoring.py)

**Files Created/Modified:**
- `api/alembic/versions/*_add_monitoring_cycles_tables.py` - Migration
- `api/app/models/monitoring.py` - Added MonitoringCycle, MonitoringCycleApproval, MonitoringResult models
- `api/app/models/__init__.py` - Exported new models
- `api/app/schemas/monitoring.py` - Added cycle, approval, and result schemas
- `api/app/api/monitoring.py` - Added all CRUD and workflow endpoints (~2300 lines)
- `api/tests/test_monitoring.py` - Added test classes for cycles, workflow, results, approvals

### Phase 2: Workflow & Validation (Backend) ✅ COMPLETE (merged with Phase 1)
1. ✅ Implement cycle status transitions (PENDING → DATA_COLLECTION → UNDER_REVIEW → PENDING_APPROVAL → APPROVED)
2. ✅ Add validation for result entry (only allowed in DATA_COLLECTION or later, not PENDING)
3. ✅ Implement submit/request-approval workflow actions
4. ✅ Implement auto-creation of approval requirements (Global + Regional based on model regions)
5. ✅ Write tests for workflow scenarios (included in Phase 1 tests)

### Phase 3: Approval Workflow (Backend) ✅ COMPLETE (merged with Phase 1)
1. ✅ Implement approval endpoints (approve, reject, void)
2. ✅ Add logic to auto-generate approvals based on model regions (queries model_regions for each model in plan scope)
3. ✅ Add auto-transition to APPROVED when all approvals complete
4. ✅ Add permission checks for approvers (Global: Admin or team member; Regional: User with region assignment)
5. ✅ Write tests for approval scenarios (included in Phase 1 tests)

### Phase 4: Basic Frontend (Cycles Tab) 📋 PENDING
1. Add Cycles tab to MonitoringPlanDetailPage
2. Display current cycle with progress and approval status
3. List previous cycles with status badges
4. Create New Cycle modal
5. Add status badges for approval states

### Phase 5: Results Entry UI 📋 PENDING
1. Create ResultsEntryPage or modal
2. Quantitative input with threshold visualization
3. Qualitative dropdown with required narrative
4. Real-time outcome calculation display
5. Save/Submit functionality

### Phase 6: Approval UI 📋 PENDING
1. Create Approval Status section in cycle detail view
2. Approve/Reject modals with comments
3. Void approval UI (Admin only)
4. Progress indicator for approval completion

### Phase 7: Reporting & Trends 📋 PENDING
1. Implement trend API endpoint
2. Add performance summary endpoint
3. Create trend visualization component
4. Add CSV export functionality
5. Add History tab with charts

## Taxonomy Setup

Add a new "Monitoring Outcome" taxonomy for qualitative selections:

```python
MONITORING_OUTCOME_TAXONOMY = {
    "taxonomy_name": "Monitoring Outcome",
    "code": "MONITORING_OUTCOME",
    "is_system": True,
    "values": [
        {"code": "GREEN", "label": "Green - Within Tolerance", "sort_order": 1},
        {"code": "YELLOW", "label": "Yellow - Warning", "sort_order": 2},
        {"code": "RED", "label": "Red - Breach/Critical", "sort_order": 3},
        {"code": "NA", "label": "N/A - Not Applicable", "sort_order": 4},
    ]
}
```

## Testing Requirements

### Backend Tests
- Cycle CRUD operations
- Result entry for each evaluation type
- Outcome calculation accuracy
- Permission checks (data provider vs team member vs admin)
- Workflow state transitions
- Validation of required fields
- Approval workflow:
  - Auto-creation of approval requirements based on model regions
  - Global vs Regional approval permissions
  - Approval/Reject/Void actions
  - Auto-transition to APPROVED when all approvals complete
  - Rejection sends back to UNDER_REVIEW

### Frontend Tests
- Cycles tab rendering
- Result entry form validation
- Outcome display updates
- Submit workflow
- Approval status display
- Approve/Reject modal interactions

## Summary

This design enables:
1. **Periodic result capture** with proper cycle management
2. **Automatic outcome calculation** for quantitative metrics
3. **Judgment-based outcomes** for qualitative metrics with required rationale
4. **Historical tracking** and trend analysis over time
5. **Flexible permissions** allowing data providers, team members, or admins to enter results
6. **Audit trail** for all changes
7. **Reporting capabilities** for compliance and trend analysis
8. **Approval workflow** with Global and Regional approvers (similar to validation workflow)
