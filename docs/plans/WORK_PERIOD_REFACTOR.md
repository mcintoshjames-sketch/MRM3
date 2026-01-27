Refactoring Analysis: Removing complete_work_days from Validation Workflow SLA
Current Architecture
Two separate sources of timing configuration:
Configuration	Location	Value	Purpose
complete_work_days	ValidationWorkflowSLA	80 days (fixed)	Time to complete validation work after assignment
model_change_lead_time_days	ValidationPolicy (per risk tier)	Tier 1: 120, Tier 2: 90, Tier 3: 60, Tier 4: 45	Lead time before model change implementation
Files affected by complete_work_days:
File	Usage
api/app/models/validation.py:98	Model column definition
api/app/api/model_versions.py:294	Total SLA calculation for INTERIM detection
api/app/schemas/workflow_sla.py:10,20	Input/output schemas
api/app/seed.py:1817	Default value seeding
api/tests/test_model_version_warnings.py:41	Test fixtures
web/src/pages/WorkflowConfigurationPage.tsx:11,28,45,168-191	Form field
web/src/pages/ValidatorDashboardPage.tsx:28,336,339	SLA calculation per status
web/src/pages/ValidationRequestDetailPage.tsx:146,901	Stage SLA lookup
Proposed Refactoring Strategy
Core Change: Replace fixed complete_work_days with model's risk-tier-specific model_change_lead_time_days from ValidationPolicy. Key Decisions:
For multi-model validation requests: Use the maximum lead time from all associated models' policies (most conservative approach for compliance).
Add computed property to ValidationRequest model:
@property
def applicable_lead_time_days(self) -> int:
    """Get the maximum lead time from all models' policies (conservative)."""
Include in API response via new schema field:
applicable_lead_time_days: int = Field(..., description="Risk-tier based completion lead time")
Safe Refactoring Steps
Phase 1: Backend - Add Computed Property (Non-Breaking)
Add applicable_lead_time_days property to ValidationRequest model
Add field to response schemas (ValidationRequestResponse, ValidationRequestListResponse)
Ensure backward compatibility: complete_work_days still exists
Phase 2: Frontend - Dual Support (Non-Breaking)
Update frontend to prefer applicable_lead_time_days when available
Fall back to complete_work_days if not present (backward compat)
Phase 3: Backend - Remove Deprecated Field (Breaking Change)
Create migration to remove complete_work_days column
Remove from model, schemas, seed
Update model_versions.py to use policy-based calculation
Phase 4: Frontend - Clean Up
Remove complete_work_days from interfaces
Remove "Complete Work Period" field from WorkflowConfigurationPage
Update all SLA calculations to use new field
Phase 5: Tests
Update test fixtures
Add tests for multi-model lead time calculation