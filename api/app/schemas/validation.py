"""Validation workflow schemas."""
from pydantic import BaseModel, field_validator
from datetime import datetime, date
from typing import Optional, List
from app.schemas.user import UserResponse
from app.schemas.taxonomy import TaxonomyValueResponse
from app.schemas.region import Region


# ==================== VALIDATION POLICY SCHEMAS ====================

class ValidationPolicyBase(BaseModel):
    """Base schema for validation policy."""
    risk_tier_id: int
    frequency_months: int = 12
    description: Optional[str] = None


class ValidationPolicyCreate(ValidationPolicyBase):
    """Schema for creating a validation policy."""
    pass


class ValidationPolicyUpdate(BaseModel):
    """Schema for updating a validation policy."""
    frequency_months: Optional[int] = None
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
    region_id: Optional[int] = None


class ValidationRequestCreate(ValidationRequestBase):
    """Schema for creating a validation request."""
    pass


class ValidationRequestUpdate(BaseModel):
    """Schema for updating a validation request."""
    validation_type_id: Optional[int] = None
    priority_id: Optional[int] = None
    target_completion_date: Optional[date] = None
    trigger_reason: Optional[str] = None
    region_id: Optional[int] = None


class ValidationRequestStatusUpdate(BaseModel):
    """Schema for updating validation request status."""
    new_status_id: int
    change_reason: Optional[str] = None


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
    region: Optional[Region] = None
    created_at: datetime
    updated_at: datetime

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
    created_at: datetime
    updated_at: datetime

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
