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
    model_change_lead_time_days: int = 90
    description: Optional[str] = None


class ValidationPolicyCreate(ValidationPolicyBase):
    """Schema for creating a validation policy."""
    pass


class ValidationPolicyUpdate(BaseModel):
    """Schema for updating a validation policy."""
    frequency_months: Optional[int] = None
    model_change_lead_time_days: Optional[int] = None
    description: Optional[str] = None


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


class ValidationRequestUpdate(BaseModel):
    """Schema for updating a validation request."""
    validation_type_id: Optional[int] = None
    priority_id: Optional[int] = None
    target_completion_date: Optional[date] = None
    trigger_reason: Optional[str] = None
    region_ids: Optional[List[int]] = None


class ValidationRequestStatusUpdate(BaseModel):
    """Schema for updating validation request status."""
    new_status_id: int
    change_reason: Optional[str] = None


class ValidationRequestDecline(BaseModel):
    """Schema for admin declining a validation request."""
    decline_reason: str


class ValidationRequestMarkSubmission(BaseModel):
    """Schema for marking submission received."""
    submission_received_date: date
    notes: Optional[str] = None


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
    recommended_review_frequency: int  # in months
    effective_date: date
    expiration_date: Optional[date] = None


class ValidationOutcomeCreate(ValidationOutcomeBase):
    """Schema for creating a validation outcome."""
    pass


class ValidationOutcomeUpdate(BaseModel):
    """Schema for updating a validation outcome."""
    overall_rating_id: Optional[int] = None
    executive_summary: Optional[str] = None
    recommended_review_frequency: Optional[int] = None
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None


class ValidationOutcomeResponse(BaseModel):
    """Response schema for validation outcome."""
    outcome_id: int
    request_id: int
    overall_rating: TaxonomyValueResponse
    executive_summary: str
    recommended_review_frequency: int
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
    approval_status: str  # Pending, Approved, Rejected
    comments: Optional[str] = None

    @field_validator('approval_status')
    @classmethod
    def validate_status(cls, v):
        allowed = ['Pending', 'Approved', 'Rejected']
        if v not in allowed:
            raise ValueError(f'approval_status must be one of {allowed}')
        return v


class ValidationApprovalResponse(BaseModel):
    """Response schema for validation approval."""
    approval_id: int
    request_id: int
    approver: UserSummary
    approver_role: str
    is_required: bool
    approval_status: str
    comments: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    # Historical context field
    represented_region_id: Optional[int] = None

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

    # Revalidation Lifecycle Fields
    prior_validation_request_id: Optional[int] = None
    submission_received_date: Optional[date] = None

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


class ValidationPlanComponentCreate(ValidationPlanComponentBase):
    """Schema for creating a validation plan component."""
    pass


class ValidationPlanComponentUpdate(BaseModel):
    """Schema for updating a validation plan component."""
    component_id: int  # Required to identify which component to update
    planned_treatment: Optional[str] = None
    rationale: Optional[str] = None
    additional_notes: Optional[str] = None


class ValidationPlanComponentResponse(ValidationPlanComponentBase):
    """Response schema for validation plan component."""
    plan_component_id: int
    default_expectation: str
    is_deviation: bool
    component_definition: ValidationComponentDefinitionResponse
    created_at: datetime
    updated_at: datetime

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
