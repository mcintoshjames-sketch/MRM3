# Model Exceptions Reporting & Metrics - Implementation Plan

## Status: AWAITING CLARIFICATION

## Overview

Implement a comprehensive model exceptions tracking system to detect, track, and report on three categories of exceptions:
1. **Unmitigated Performance Problem** - Model has performance issues that haven't been addressed
2. **Model Used Outside Intended Purpose** - Validated model used beyond its approved scope
3. **Model In Use Prior to Full Validation** - Model deployed without full validation (interim or unapproved)

## Current System Analysis

### What Already Exists

#### Approval Status Tracking
- **File**: `api/app/core/model_approval_status.py`
- Model approval_status computed as: NEVER_VALIDATED, APPROVED, INTERIM_APPROVED, VALIDATION_IN_PROGRESS, EXPIRED
- `use_approval_date` tracks when all conditional approvals complete
- `ModelApprovalStatusHistory` provides audit trail of status changes

#### Performance Monitoring
- **File**: `api/app/api/monitoring.py`, `api/app/models/monitoring.py`
- MonitoringCycle with RED/YELLOW/GREEN outcomes
- "Breach protocol": RED results require narrative justification before approval
- MonitoringResult stores: calculated_outcome, narrative, supporting_data
- NO proactive alerting - enforcement only at approval time

#### Validation Workflow
- **File**: `api/app/api/validation_workflow.py`, `api/app/models/validation.py`
- ValidationRequest with 8 states (INTAKE → APPROVED)
- ValidationOutcome with overall_rating (Fit for Purpose / Not Fit for Purpose)
- Conditional approvals with regional coverage

#### Reporting Infrastructure
- **File**: `api/app/api/kpi_report.py`, `api/app/api/overdue_revalidation_report.py`
- 21 KPI metrics with drill-down support
- Overdue report with severity buckets
- Well-established patterns for aggregation

### Gaps to Address

1. **No unified Exception entity** - Exceptions are implicit, not tracked as first-class entities
2. **No "intended purpose" definition** - Models don't have formal scope boundaries
3. **No exception lifecycle** - No workflow for acknowledging/remediating/closing exceptions
4. **No real-time alerting** - Discovery is manual or at approval gates
5. **No aggregated exception metrics** - Cannot trend exceptions over time

---

## Clarifying Questions

### 1. Unmitigated Performance Problem

The system tracks RED monitoring outcomes with required justification. How should "unmitigated" be defined?

- **A**: RED result documented but no remediation action within X days
- **B**: RED result persists across multiple monitoring cycles
- **C**: RED result without a linked recommendation/action item
- **D**: Other definition?

### 2. Model Used Outside Intended Purpose

Models lack formal "intended purpose" fields. How should scope be captured?

- **A**: Add structured fields (approved_use_cases, approved_regions, approved_products)
- **B**: Link models to "Use Case" entities defining approved scope
- **C**: Self-attestation - owners attest quarterly that usage is within scope
- **D**: Manual exception creation when out-of-scope use is identified

### 3. Model In Use Prior to Full Validation

System has INTERIM_APPROVED and NEVER_VALIDATED statuses. How to track "in use"?

- **A**: Add `is_in_production_use` boolean flag
- **B**: Track via model versions (deployed version = in use)
- **C**: Infer from deployment regions (if deployed = in use)
- **D**: Self-attestation by model owner

### 4. Exception Lifecycle

What workflow states should exceptions have?
- Example: `OPEN → ACKNOWLEDGED → REMEDIATION_IN_PROGRESS → CLOSED`
- Should exceptions require approval to close?
- Should they have SLAs based on severity?

### 5. Integration Points

Where should exceptions surface for best UX?
- Model detail pages?
- User dashboards/task lists?
- Validation workflow?
- Monitoring cycle pages?
- All of the above?

---

## Preliminary Architecture (Pending Answers)

### Proposed Core Entity: ModelException

```python
class ModelException(Base):
    __tablename__ = "model_exceptions"

    exception_id: int  # PK
    model_id: int  # FK to models
    exception_type_id: int  # FK to taxonomy (3 types)
    exception_status_id: int  # FK to taxonomy (OPEN, ACKNOWLEDGED, IN_REMEDIATION, CLOSED)
    severity_id: int  # FK to taxonomy (CRITICAL, HIGH, MEDIUM, LOW)

    # Source tracking
    source_entity_type: str  # "MonitoringResult", "ValidationRequest", "ManualEntry"
    source_entity_id: int

    # Dates
    detected_at: datetime
    acknowledged_at: datetime | None
    remediation_started_at: datetime | None
    closed_at: datetime | None
    sla_due_date: datetime | None

    # Details
    description: str
    remediation_plan: str | None
    closure_reason: str | None
    closed_by_id: int | None  # FK to users

    # Relationships
    model: Model
    exception_type: TaxonomyValue
    status: TaxonomyValue
    severity: TaxonomyValue
```

### Proposed Detection Mechanisms

1. **Performance Exceptions**: Triggered when RED monitoring result is approved but no linked recommendation created within X days
2. **Scope Exceptions**: TBD based on how scope is captured
3. **Pre-Validation Exceptions**: Auto-detected when model with status=ACTIVE has approval_status in (NEVER_VALIDATED, INTERIM_APPROVED, EXPIRED)

### Proposed UI Integration Points

1. **Model Detail Page**: "Exceptions" tab showing open/historical exceptions
2. **Dashboard**: Exception count badges and exception task list
3. **Reports**: "Model Exceptions Report" with aggregation and drill-down
4. **Validation Workflow**: Pre-validation exceptions surfaced during submission

---

## Next Steps

1. Receive answers to clarifying questions
2. Finalize exception type definitions and detection logic
3. Design complete database schema
4. Design API endpoints
5. Design UI components and integration
6. Create implementation phases
