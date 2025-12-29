"""Validation workflow schemas."""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, date
from typing import Optional, List, Dict
from app.schemas.user import UserResponse
from app.schemas.taxonomy import TaxonomyValueResponse
from app.schemas.region import Region


# ==================== VALIDATION POLICY SCHEMAS ====================

class ValidationPolicyBase(BaseModel):
    """Base schema for validation policy."""
    risk_tier_id: int
    frequency_months: int = 12
    grace_period_months: int = 3
    model_change_lead_time_days: int = 90
    description: Optional[str] = None
    monitoring_plan_review_required: bool = False
    monitoring_plan_review_description: Optional[str] = None


class ValidationPolicyCreate(ValidationPolicyBase):
    """Schema for creating a validation policy."""
    pass


class ValidationPolicyUpdate(BaseModel):
    """Schema for updating a validation policy."""
    frequency_months: Optional[int] = None
    grace_period_months: Optional[int] = None
    model_change_lead_time_days: Optional[int] = None
    description: Optional[str] = None
    monitoring_plan_review_required: Optional[bool] = None
    monitoring_plan_review_description: Optional[str] = None


class ValidationPolicyResponse(ValidationPolicyBase):
    """Response schema for validation policy."""
    policy_id: int
    risk_tier: TaxonomyValueResponse
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== HELPER SCHEMAS ====================

class ModelSummary(BaseModel):
    """Minimal model info for validation response."""
    model_id: int
    model_name: str
    status: str

    class Config:
        from_attributes = True


class UserSummary(BaseModel):
    """Minimal user info for validation responses."""
    user_id: int
    full_name: str
    email: str
    role: str

    class Config:
        from_attributes = True


# ==================== VALIDATION REQUEST SCHEMAS ====================

class ValidationRequestBase(BaseModel):
    """Base schema for validation request."""
    model_ids: List[int]  # Support multiple models
    validation_type_id: int
    priority_id: int
    target_completion_date: date
    trigger_reason: Optional[str] = None
    region_ids: List[int] = []  # Support multiple regions
    prior_validation_request_id: Optional[int] = None  # Link to previous validation for revalidations


class ValidationRequestCreate(ValidationRequestBase):
    """Schema for creating a validation request."""
    model_versions: Optional[Dict[int, Optional[int]]] = None  # {model_id: version_id or None}
    check_warnings: bool = False  # If True, return warnings without creating request
    force_create: bool = False  # If True, proceed despite warnings (but not errors)


class ValidationWarning(BaseModel):
    """Individual warning about target completion date."""
    warning_type: str  # 'LEAD_TIME', 'IMPLEMENTATION_DATE', 'REVALIDATION_OVERDUE'
    severity: str  # 'ERROR', 'WARNING', 'INFO'
    model_id: int
    model_name: str
    version_number: Optional[str] = None
    message: str
    details: Optional[Dict] = None  # Additional contextual information


class ValidationRequestWarningsResponse(BaseModel):
    """Response with warnings about target completion date issues."""
    has_warnings: bool
    can_proceed: bool  # False if there are blocking errors
    warnings: List[ValidationWarning]
    request_data: ValidationRequestBase  # Echo back the request data


# ==================== CHANGE VALIDATION BLOCKER SCHEMAS ====================

class VersionAvailable(BaseModel):
    """Summary of an available draft version for selection."""
    version_id: int
    version_number: str
    change_description: Optional[str] = None


class VersionBlocker(BaseModel):
    """
    Blocking issue for CHANGE validation creation.

    When validation_type is CHANGE, each model must be linked to a specific
    model version. These blockers indicate what's preventing creation.
    """
    type: str = Field(
        ...,
        description="Blocker type: 'NO_DRAFT_VERSION' (no version to select) or 'MISSING_VERSION_LINK' (version not specified)"
    )
    severity: str = Field(
        default="ERROR",
        description="Always ERROR for blockers - cannot be overridden"
    )
    model_id: int = Field(
        ...,
        description="ID of the model with the blocking issue"
    )
    model_name: str = Field(
        ...,
        description="Name of the model with the blocking issue"
    )
    message: str = Field(
        ...,
        description="Human-readable explanation of the blocking issue"
    )
    available_versions: Optional[List[VersionAvailable]] = Field(
        None,
        description="DRAFT versions available for selection (only for MISSING_VERSION_LINK)"
    )


class ValidationCreationBlockedResponse(BaseModel):
    """
    Response when CHANGE validation creation is blocked.

    Returned with HTTP 400 when attempting to create a CHANGE validation
    without properly linking models to versions.
    """
    message: str = Field(
        ...,
        description="Overall explanation of why creation was blocked"
    )
    blockers: List[VersionBlocker] = Field(
        ...,
        description="List of blocking issues per model"
    )


class ValidationRequestUpdate(BaseModel):
    """Schema for updating a validation request."""
    validation_type_id: Optional[int] = None
    priority_id: Optional[int] = None
    target_completion_date: Optional[date] = None
    trigger_reason: Optional[str] = None
    region_ids: Optional[List[int]] = None


class ModelVersionEntry(BaseModel):
    """Entry for adding a model with optional version."""
    model_id: int
    version_id: Optional[int] = None  # Required for CHANGE type validations


class ValidationRequestModelUpdate(BaseModel):
    """Schema for adding/removing models from a validation request."""
    add_models: Optional[List[ModelVersionEntry]] = None
    remove_model_ids: Optional[List[int]] = None
    allow_unassign_conflicts: bool = False


class ValidationRequestModelUpdateResponse(BaseModel):
    """Response with impacts of the model change."""
    success: bool
    models_added: List[int]
    models_removed: List[int]
    lead_time_changed: bool
    old_lead_time_days: Optional[int] = None
    new_lead_time_days: Optional[int] = None
    warnings: List[ValidationWarning] = Field(default_factory=list)
    plan_deviations_flagged: int
    approvals_added: int
    approvals_voided: int
    conditional_approvals_added: int
    conditional_approvals_voided: int
    validators_unassigned: List[str] = Field(default_factory=list)


class ValidationRequestStatusUpdate(BaseModel):
    """Schema for updating validation request status."""
    new_status_id: int
    change_reason: Optional[str] = None
    skip_assessment_warning: bool = False  # Skip warning about outdated risk assessments


class ValidationRequestHold(BaseModel):
    """Schema for putting a validation request on hold - reason required."""
    hold_reason: str = Field(
        ...,
        min_length=10,
        description="Required explanation for putting request on hold (min 10 characters)"
    )


class ValidationRequestCancel(BaseModel):
    """Schema for cancelling a validation request - reason required."""
    cancel_reason: str = Field(
        ...,
        min_length=10,
        description="Required explanation for cancellation (min 10 characters)"
    )


class ValidationRequestResume(BaseModel):
    """Schema for resuming a validation request from hold."""
    resume_notes: Optional[str] = Field(
        None,
        description="Optional explanation for resuming"
    )
    target_status_code: Optional[str] = Field(
        None,
        description="Override status to resume to (defaults to previous status before hold)"
    )


class ValidationRequestDecline(BaseModel):
    """Schema for admin declining a validation request."""
    decline_reason: str


class ValidationRequestMarkSubmission(BaseModel):
    """Schema for marking submission received."""
    submission_received_date: date
    notes: Optional[str] = None
    # Optional fields to capture submission metadata
    confirmed_model_version_id: Optional[int] = None  # Allow confirming/correcting the model version
    model_documentation_version: Optional[str] = None  # Version of model documentation
    model_submission_version: Optional[str] = None  # Version of model code/artifacts
    model_documentation_id: Optional[str] = None  # External document ID (e.g., DMS reference)


class ValidationApprovalUnlink(BaseModel):
    """Schema for admin unlinking a regional approval."""
    unlink_reason: str


# ==================== VALIDATION ASSIGNMENT SCHEMAS ====================

class ValidationAssignmentBase(BaseModel):
    """Base schema for validation assignment."""
    validator_id: int
    is_primary: bool = False
    is_reviewer: bool = False
    estimated_hours: Optional[float] = None


class ValidationAssignmentCreate(ValidationAssignmentBase):
    """Schema for creating a validation assignment."""
    independence_attestation: bool = False  # Must be True to assign validator


class ValidationAssignmentUpdate(BaseModel):
    """Schema for updating a validation assignment."""
    is_primary: Optional[bool] = None
    is_reviewer: Optional[bool] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    independence_attestation: Optional[bool] = None


class ReviewerSignOffRequest(BaseModel):
    """Schema for reviewer sign-off on validation work."""
    comments: Optional[str] = None


class ValidationAssignmentResponse(BaseModel):
    """Response schema for validation assignment."""
    assignment_id: int
    request_id: int
    validator: UserSummary
    is_primary: bool
    is_reviewer: bool
    assignment_date: date
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    independence_attestation: bool
    reviewer_signed_off: bool = False
    reviewer_signed_off_at: Optional[datetime] = None
    reviewer_sign_off_comments: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== VALIDATION WORK COMPONENT SCHEMAS ====================

class ValidationWorkComponentBase(BaseModel):
    """Base schema for validation work component."""
    component_type_id: int
    status_id: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None


class ValidationWorkComponentCreate(ValidationWorkComponentBase):
    """Schema for creating a validation work component."""
    pass


class ValidationWorkComponentUpdate(BaseModel):
    """Schema for updating a validation work component."""
    status_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None


class ValidationWorkComponentResponse(BaseModel):
    """Response schema for validation work component."""
    component_id: int
    request_id: int
    component_type: TaxonomyValueResponse
    status: TaxonomyValueResponse
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== VALIDATION OUTCOME SCHEMAS ====================

class ValidationOutcomeBase(BaseModel):
    """Base schema for validation outcome."""
    overall_rating_id: int
    executive_summary: str
    effective_date: date
    expiration_date: Optional[date] = None


class ValidationOutcomeCreate(ValidationOutcomeBase):
    """Schema for creating a validation outcome."""
    pass


class ValidationOutcomeUpdate(BaseModel):
    """Schema for updating a validation outcome."""
    overall_rating_id: Optional[int] = None
    executive_summary: Optional[str] = None
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None


class ValidationOutcomeResponse(BaseModel):
    """Response schema for validation outcome."""
    outcome_id: int
    request_id: int
    overall_rating: TaxonomyValueResponse
    executive_summary: str
    effective_date: date
    expiration_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== VALIDATION REVIEW OUTCOME SCHEMAS ====================

class ValidationReviewOutcomeBase(BaseModel):
    """Base schema for validation review outcome."""
    decision: str  # 'AGREE' or 'SEND_BACK'
    comments: Optional[str] = None
    agrees_with_rating: Optional[bool] = None


class ValidationReviewOutcomeCreate(ValidationReviewOutcomeBase):
    """Schema for creating a validation review outcome."""
    pass


class ValidationReviewOutcomeUpdate(BaseModel):
    """Schema for updating a validation review outcome."""
    decision: Optional[str] = None
    comments: Optional[str] = None
    agrees_with_rating: Optional[bool] = None


class ValidationReviewOutcomeResponse(BaseModel):
    """Response schema for validation review outcome."""
    review_outcome_id: int
    request_id: int
    reviewer: UserSummary
    decision: str
    comments: Optional[str] = None
    agrees_with_rating: Optional[bool] = None
    review_date: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== VALIDATION APPROVAL SCHEMAS ====================

class ValidationApprovalBase(BaseModel):
    """Base schema for validation approval."""
    approver_id: int
    approver_role: str  # Validator, Validation Head, Model Owner, Risk Officer
    is_required: bool = True
    approval_type: str = "Global"  # Global or Regional
    region_id: Optional[int] = None
    represented_region_id: Optional[int] = None

    @field_validator("approval_type")
    @classmethod
    def validate_approval_type(cls, v):
        allowed = ["Global", "Regional"]
        if v not in allowed:
            raise ValueError(f"approval_type must be one of {allowed}")
        return v


class ValidationApprovalCreate(ValidationApprovalBase):
    """Schema for creating a validation approval."""
    pass


class ValidationApprovalUpdate(BaseModel):
    """Schema for updating a validation approval (submitting approval)."""
    approval_status: str  # Pending, Approved, Sent Back (Rejected removed - use workflow cancellation instead)
    comments: Optional[str] = None

    @field_validator('approval_status')
    @classmethod
    def validate_status(cls, v):
        allowed = ['Pending', 'Approved', 'Sent Back']
        if v not in allowed:
            raise ValueError(f'approval_status must be one of {allowed}. To reject a validation, cancel the workflow instead.')
        return v


class ValidationApprovalResponse(BaseModel):
    """Response schema for validation approval."""
    approval_id: int
    request_id: int
    approver: Optional[UserSummary] = None  # None for conditional approvals until submitted
    approver_role: str
    approval_type: str  # Global, Regional, or Conditional
    is_required: bool
    approval_status: str
    comments: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    # Region this approval is for (used for regional approvals)
    region_id: Optional[int] = None
    # Historical context field (deprecated, use region_id instead)
    represented_region_id: Optional[int] = None
    # Voided status (approvals may be voided due to model risk tier changes)
    voided_at: Optional[datetime] = None
    void_reason: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== VALIDATION STATUS HISTORY SCHEMAS ====================

class ValidationStatusHistoryResponse(BaseModel):
    """Response schema for validation status history."""
    history_id: int
    request_id: int
    old_status: Optional[TaxonomyValueResponse] = None
    new_status: TaxonomyValueResponse
    changed_by: UserSummary
    change_reason: Optional[str] = None
    changed_at: datetime

    class Config:
        from_attributes = True


# ==================== FULL VALIDATION REQUEST RESPONSES ====================

class ValidationRequestResponse(BaseModel):
    """Response schema for validation request with basic relationships."""
    request_id: int
    models: List[ModelSummary]  # Support multiple models
    request_date: date
    requestor: UserSummary
    validation_type: TaxonomyValueResponse
    priority: TaxonomyValueResponse
    target_completion_date: date
    trigger_reason: Optional[str] = None
    current_status: TaxonomyValueResponse
    regions: List[Region] = []  # Support multiple regions
    approvals: List[ValidationApprovalResponse] = []  # Added for Phase 5: Smart Approver Assignment
    created_at: datetime
    updated_at: datetime
    completion_date: Optional[datetime] = Field(None, description="Date when validation was completed (latest approval date)")

    # Risk tier snapshot at validation approval
    validated_risk_tier_id: Optional[int] = Field(None, description="Snapshot of model's risk tier at approval time")
    validated_risk_tier: Optional[TaxonomyValueResponse] = Field(None, description="Risk tier at time of validation approval")

    # Scorecard and Residual Risk
    scorecard_overall_rating: Optional[str] = Field(None, description="Overall scorecard rating (e.g., Green, Yellow, Red)")
    residual_risk: Optional[str] = Field(None, description="Computed residual risk based on risk tier and scorecard outcome")

    # Revalidation Lifecycle Fields
    prior_validation_request_id: Optional[int] = None
    prior_full_validation_request_id: Optional[int] = None
    submission_received_date: Optional[date] = None

    # Submission metadata fields (captured when marking submission received)
    confirmed_model_version_id: Optional[int] = None
    model_documentation_version: Optional[str] = None
    model_submission_version: Optional[str] = None
    model_documentation_id: Optional[str] = None

    # Computed revalidation lifecycle properties
    is_periodic_revalidation: bool = False
    submission_due_date: Optional[date] = None
    submission_grace_period_end: Optional[date] = None
    model_validation_due_date: Optional[date] = None
    validation_team_sla_due_date: Optional[date] = None
    submission_status: str = "N/A"
    model_compliance_status: str = "N/A"
    validation_team_sla_status: str = "N/A"
    days_until_submission_due: Optional[int] = None
    days_until_model_validation_due: Optional[int] = None
    days_until_team_sla_due: Optional[int] = None

    # Risk-tier-based SLA (replaces fixed complete_work_days)
    applicable_lead_time_days: int = Field(
        90,
        description="Risk-tier-specific completion lead time in days from ValidationPolicy"
    )

    # Hold time tracking
    total_hold_days: int = Field(
        0,
        description="Total days this request has spent in ON_HOLD status"
    )
    previous_status_before_hold: Optional[str] = Field(
        None,
        description="Status code before most recent ON_HOLD (for Resume functionality)"
    )
    adjusted_validation_team_sla_due_date: Optional[date] = Field(
        None,
        description="Team SLA due date adjusted for hold time (extends by hold days)"
    )

    class Config:
        from_attributes = True


class ValidationRequestDetailResponse(ValidationRequestResponse):
    """Detailed response schema for validation request with all relationships."""
    assignments: List[ValidationAssignmentResponse] = []
    work_components: List[ValidationWorkComponentResponse] = []
    status_history: List[ValidationStatusHistoryResponse] = []
    approvals: List[ValidationApprovalResponse] = []
    outcome: Optional[ValidationOutcomeResponse] = None
    review_outcome: Optional[ValidationReviewOutcomeResponse] = None

    class Config:
        from_attributes = True


class ValidationRequestListResponse(BaseModel):
    """Lightweight response schema for validation request list."""
    request_id: int
    model_ids: List[int]  # Support multiple models
    model_names: List[str]  # Support multiple model names
    request_date: date
    requestor_name: str
    validation_type: str
    priority: str
    target_completion_date: date
    current_status: str
    days_in_status: int
    primary_validator: Optional[str] = None
    regions: List[Region] = []  # Support multiple regions
    created_at: datetime
    updated_at: datetime
    completion_date: Optional[datetime] = Field(None, description="Date when validation was completed (latest approval date)")

    # Risk-tier-based SLA (replaces fixed complete_work_days)
    applicable_lead_time_days: int = Field(
        90,
        description="Risk-tier-specific completion lead time in days from ValidationPolicy"
    )

    class Config:
        from_attributes = True


# ==================== LEGACY VALIDATION SCHEMAS (for backwards compatibility) ====================

class ValidationBase(BaseModel):
    """DEPRECATED: Base schema for legacy validation."""
    model_id: int
    validation_date: date
    validator_id: int
    validation_type_id: int
    outcome_id: int
    scope_id: Optional[int] = None
    region_id: Optional[int] = None
    findings_summary: Optional[str] = None
    report_reference: Optional[str] = None


class ValidationCreate(ValidationBase):
    """DEPRECATED: Schema for creating a legacy validation."""
    pass


class ValidationUpdate(BaseModel):
    """DEPRECATED: Schema for updating a legacy validation."""
    validation_date: Optional[date] = None
    validator_id: Optional[int] = None
    validation_type_id: Optional[int] = None
    outcome_id: Optional[int] = None
    scope_id: Optional[int] = None
    region_id: Optional[int] = None
    findings_summary: Optional[str] = None
    report_reference: Optional[str] = None


class ValidationResponse(ValidationBase):
    """DEPRECATED: Response schema for legacy validation."""
    validation_id: int
    model: ModelSummary
    validator: UserResponse
    validation_type: TaxonomyValueResponse
    outcome: TaxonomyValueResponse
    scope: Optional[TaxonomyValueResponse] = None
    region: Optional[Region] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ValidationListResponse(BaseModel):
    """DEPRECATED: Response schema for legacy validation list."""
    validation_id: int
    model_id: int
    model_name: str
    validation_date: date
    validator_name: str
    validation_type: str
    outcome: str
    scope: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== VALIDATION PLAN SCHEMAS ====================

class ValidationComponentDefinitionResponse(BaseModel):
    """Response schema for validation component definition."""
    component_id: int
    section_number: str
    section_title: str
    component_code: str
    component_title: str
    is_test_or_analysis: bool
    expectation_high: str
    expectation_medium: str
    expectation_low: str
    expectation_very_low: str
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True


class ValidationPlanComponentBase(BaseModel):
    """Base schema for validation plan component."""
    component_id: int
    planned_treatment: str  # Planned, NotPlanned, NotApplicable
    rationale: Optional[str] = None
    additional_notes: Optional[str] = None
    # Component 9b specific fields (for Performance Monitoring Plan Review)
    monitoring_plan_version_id: Optional[int] = None  # Reference to MonitoringPlanVersion
    monitoring_review_notes: Optional[str] = None


class ValidationPlanComponentCreate(ValidationPlanComponentBase):
    """Schema for creating a validation plan component."""
    pass


class ValidationPlanComponentUpdate(BaseModel):
    """Schema for updating a validation plan component."""
    component_id: int  # Required to identify which component to update
    planned_treatment: Optional[str] = None
    rationale: Optional[str] = None
    additional_notes: Optional[str] = None
    # Component 9b specific fields
    monitoring_plan_version_id: Optional[int] = None
    monitoring_review_notes: Optional[str] = None


class ValidationPlanComponentResponse(ValidationPlanComponentBase):
    """Response schema for validation plan component."""
    plan_component_id: int
    default_expectation: str
    is_deviation: bool
    component_definition: ValidationComponentDefinitionResponse
    created_at: datetime
    updated_at: datetime
    # Component 9b specific fields
    monitoring_plan_version_id: Optional[int] = None
    monitoring_review_notes: Optional[str] = None

    class Config:
        from_attributes = True


class ValidationPlanBase(BaseModel):
    """Base schema for validation plan."""
    overall_scope_summary: Optional[str] = None
    material_deviation_from_standard: bool = False
    overall_deviation_rationale: Optional[str] = None


class ValidationPlanCreate(ValidationPlanBase):
    """Schema for creating a validation plan."""
    components: List[ValidationPlanComponentCreate] = []
    template_plan_id: Optional[int] = None  # Copy from this plan if provided


class ValidationPlanUpdate(BaseModel):
    """Schema for updating a validation plan."""
    overall_scope_summary: Optional[str] = None
    material_deviation_from_standard: Optional[bool] = None
    overall_deviation_rationale: Optional[str] = None
    components: Optional[List[ValidationPlanComponentUpdate]] = None


class ValidationPlanResponse(ValidationPlanBase):
    """Response schema for validation plan."""
    plan_id: int
    request_id: int
    components: List[ValidationPlanComponentResponse]
    created_at: datetime
    updated_at: datetime

    # Versioning and locking fields
    config_id: Optional[int] = None
    locked_at: Optional[datetime] = None
    locked_by_user_id: Optional[int] = None

    # Derived fields for UI convenience
    model_id: Optional[int] = None
    model_name: Optional[str] = None
    risk_tier: Optional[str] = None
    validation_approach: Optional[str] = None

    # Scope-only plan indicator (for TARGETED, INTERIM validation types)
    is_scope_only: bool = False
    validation_type_code: Optional[str] = None

    class Config:
        from_attributes = True


class PlanTemplateSuggestion(BaseModel):
    """Suggestion for a previous plan to use as a template."""
    source_request_id: int
    source_plan_id: int
    validation_type: str
    model_names: List[str]
    completion_date: Optional[str] = None
    validator_name: Optional[str] = None
    component_count: int
    deviations_count: int
    config_id: Optional[int] = None
    config_name: Optional[str] = None
    is_different_config: bool  # True if template uses different requirements version


class PlanTemplateSuggestionsResponse(BaseModel):
    """Response with template plan suggestions."""
    has_suggestions: bool
    suggestions: List[PlanTemplateSuggestion]


# ==================== COMPONENT DEFINITION MANAGEMENT SCHEMAS ====================

class ValidationComponentDefinitionUpdate(BaseModel):
    """Schema for updating a component definition."""
    expectation_high: Optional[str] = None
    expectation_medium: Optional[str] = None
    expectation_low: Optional[str] = None
    expectation_very_low: Optional[str] = None
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    component_code: Optional[str] = None
    component_title: Optional[str] = None
    is_test_or_analysis: Optional[bool] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ConfigurationItemResponse(BaseModel):
    """Response schema for a configuration item (component snapshot)."""
    config_item_id: int
    component_id: int
    expectation_high: str
    expectation_medium: str
    expectation_low: str
    expectation_very_low: str
    section_number: str
    section_title: str
    component_code: str
    component_title: str
    is_test_or_analysis: bool
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True


class ConfigurationResponse(BaseModel):
    """Response schema for a configuration version."""
    config_id: int
    config_name: str
    description: Optional[str]
    effective_date: date
    created_by_user_id: Optional[int]
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class ConfigurationDetailResponse(ConfigurationResponse):
    """Detailed configuration response with component items."""
    config_items: List[ConfigurationItemResponse]


class ConfigurationPublishRequest(BaseModel):
    """Request schema for publishing a new configuration version."""
    config_name: str
    description: Optional[str] = None
    effective_date: Optional[date] = None  # Defaults to today if not provided


# ==================== RISK TIER CHANGE IMPACT SCHEMAS ====================

class OpenValidationSummary(BaseModel):
    """Summary of an open validation request that would be affected by risk tier change."""
    request_id: int
    current_status: str
    validation_type: str
    has_plan: bool
    pending_approvals_count: int
    primary_validator: Optional[str] = None


class OpenValidationsCheckResponse(BaseModel):
    """Response for checking open validations that would be affected by risk tier change."""
    model_id: int
    model_name: str
    current_risk_tier: Optional[str] = None
    proposed_risk_tier: Optional[str] = None
    has_open_validations: bool
    open_validation_count: int
    open_validations: List[OpenValidationSummary] = []
    warning_message: Optional[str] = None
    requires_confirmation: bool = False


class ForceResetRequest(BaseModel):
    """Request to force reset validation plans after risk tier change."""
    model_id: int
    new_risk_tier_id: int
    confirm_reset: bool = False  # Must be True to proceed


class ForceResetResponse(BaseModel):
    """Response after force resetting validation plans."""
    success: bool
    reset_count: int
    request_ids: List[int]
    components_regenerated: int
    approvals_voided: int
    message: str


# ==================== RISK MISMATCH REPORT SCHEMAS ====================

class RiskMismatchItem(BaseModel):
    """A model where current risk tier doesn't match validated risk tier."""
    model_id: int
    model_name: str
    current_risk_tier_id: Optional[int] = None
    current_risk_tier_code: Optional[str] = None
    current_risk_tier_label: Optional[str] = None
    validated_risk_tier_id: Optional[int] = None
    validated_risk_tier_code: Optional[str] = None
    validated_risk_tier_label: Optional[str] = None
    last_validation_request_id: Optional[int] = None
    last_validation_date: Optional[date] = None
    tier_change_direction: str  # "INCREASED", "DECREASED", or "CHANGED"
    requires_revalidation: bool


class RiskMismatchReportResponse(BaseModel):
    """Response for risk mismatch audit report."""
    total_models_checked: int
    models_with_mismatch: int
    items: List[RiskMismatchItem]
    generated_at: datetime


# ==================== PRE-TRANSITION WARNING SCHEMAS ====================

class PreTransitionWarning(BaseModel):
    """
    Individual pre-transition warning.

    Returned when checking if a validation request can safely transition
    to a new status (e.g., PENDING_APPROVAL). Warnings alert users to
    incomplete work that should be addressed before proceeding.
    """
    warning_type: str = Field(
        ...,
        description="Type of warning: 'OPEN_FINDINGS', 'PENDING_RECOMMENDATIONS', 'UNADDRESSED_ATTESTATIONS'"
    )
    severity: str = Field(
        ...,
        description="Severity level: 'ERROR' (blocking), 'WARNING' (proceed with caution), 'INFO'"
    )
    message: str = Field(
        ...,
        description="Human-readable warning message"
    )
    model_id: int = Field(
        ...,
        description="ID of the model this warning relates to"
    )
    model_name: str = Field(
        ...,
        description="Name of the model this warning relates to"
    )
    details: Dict = Field(
        default_factory=dict,
        description="Additional contextual details (e.g., finding_ids, recommendation_ids, counts)"
    )


class PreTransitionWarningsResponse(BaseModel):
    """
    Response for pre-transition warnings check.

    Called before transitioning a validation request to a new status
    to identify any blocking issues or warnings that users should be aware of.
    """
    request_id: int = Field(
        ...,
        description="ID of the validation request being checked"
    )
    target_status: str = Field(
        ...,
        description="The status the request would transition to (e.g., 'PENDING_APPROVAL')"
    )
    warnings: List[PreTransitionWarning] = Field(
        default_factory=list,
        description="List of warnings/errors found"
    )
    can_proceed: bool = Field(
        ...,
        description="False if there are ERROR-severity warnings (blocking), True otherwise"
    )
