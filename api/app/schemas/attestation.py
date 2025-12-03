"""Attestation schemas for Model Risk Attestations."""
import re
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class AttestationCycleStatusEnum(str, Enum):
    """Attestation cycle status workflow states."""
    PENDING = "PENDING"
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    CLOSED = "CLOSED"


class AttestationFrequencyEnum(str, Enum):
    """Attestation frequency options."""
    ANNUAL = "ANNUAL"
    QUARTERLY = "QUARTERLY"


class AttestationDecisionEnum(str, Enum):
    """Attestation decision types."""
    I_ATTEST = "I_ATTEST"
    I_ATTEST_WITH_UPDATES = "I_ATTEST_WITH_UPDATES"
    OTHER = "OTHER"


class AttestationRecordStatusEnum(str, Enum):
    """Attestation record status."""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    ADMIN_REVIEW = "ADMIN_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class AttestationSchedulingRuleTypeEnum(str, Enum):
    """Types of scheduling rules."""
    GLOBAL_DEFAULT = "GLOBAL_DEFAULT"
    OWNER_THRESHOLD = "OWNER_THRESHOLD"
    MODEL_OVERRIDE = "MODEL_OVERRIDE"
    REGIONAL_OVERRIDE = "REGIONAL_OVERRIDE"


class AttestationChangeTypeEnum(str, Enum):
    """Types of inventory changes proposed during attestation."""
    UPDATE_EXISTING = "UPDATE_EXISTING"
    NEW_MODEL = "NEW_MODEL"
    DECOMMISSION = "DECOMMISSION"


class AttestationChangeStatusEnum(str, Enum):
    """Status of change proposals."""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class AttestationEvidenceTypeEnum(str, Enum):
    """Types of evidence URLs."""
    MONITORING_REPORT = "MONITORING_REPORT"
    VALIDATION_REPORT = "VALIDATION_REPORT"
    POLICY_DOC = "POLICY_DOC"
    EXCEPTION_DOC = "EXCEPTION_DOC"
    OTHER = "OTHER"


class AttestationQuestionFrequencyEnum(str, Enum):
    """Frequency scope for attestation questions."""
    ANNUAL = "ANNUAL"
    QUARTERLY = "QUARTERLY"
    BOTH = "BOTH"


# ============================================================================
# REFERENCE SCHEMAS
# ============================================================================

class UserRef(BaseModel):
    """Minimal user reference."""
    user_id: int
    email: str
    full_name: str

    class Config:
        from_attributes = True


class ModelRef(BaseModel):
    """Minimal model reference."""
    model_id: int
    model_name: str
    risk_tier_code: Optional[str] = None
    risk_tier_label: Optional[str] = None
    owner_name: Optional[str] = None

    class Config:
        from_attributes = True


class RegionRef(BaseModel):
    """Minimal region reference."""
    region_id: int
    region_name: str
    region_code: str

    class Config:
        from_attributes = True


class TaxonomyValueRef(BaseModel):
    """Minimal taxonomy value reference."""
    value_id: int
    code: str
    label: str

    class Config:
        from_attributes = True


# ============================================================================
# ATTESTATION QUESTION SCHEMAS
# ============================================================================

class AttestationQuestionConfigBase(BaseModel):
    """Base schema for attestation question config."""
    frequency_scope: AttestationQuestionFrequencyEnum = AttestationQuestionFrequencyEnum.BOTH
    requires_comment_if_no: bool = False


class AttestationQuestionConfigCreate(AttestationQuestionConfigBase):
    """Create schema for attestation question config."""
    question_value_id: int


class AttestationQuestionConfigUpdate(BaseModel):
    """Update schema for attestation question config."""
    frequency_scope: Optional[AttestationQuestionFrequencyEnum] = None
    requires_comment_if_no: Optional[bool] = None


class AttestationQuestionUpdate(BaseModel):
    """Update schema for attestation question (combines taxonomy value + config)."""
    # Taxonomy value fields
    label: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    # Config fields
    frequency_scope: Optional[AttestationQuestionFrequencyEnum] = None
    requires_comment_if_no: Optional[bool] = None


class AttestationQuestionResponse(BaseModel):
    """Response schema for attestation question (combines taxonomy value + config)."""
    value_id: int
    code: str
    label: str
    description: Optional[str] = None
    sort_order: int
    is_active: bool
    frequency_scope: AttestationQuestionFrequencyEnum
    requires_comment_if_no: bool

    class Config:
        from_attributes = True


# ============================================================================
# ATTESTATION CYCLE SCHEMAS
# ============================================================================

class AttestationCycleBase(BaseModel):
    """Base schema for attestation cycle."""
    cycle_name: str
    period_start_date: date
    period_end_date: date
    submission_due_date: date
    notes: Optional[str] = None


class AttestationCycleCreate(AttestationCycleBase):
    """Create schema for attestation cycle."""
    pass


class AttestationCycleUpdate(BaseModel):
    """Update schema for attestation cycle."""
    cycle_name: Optional[str] = None
    period_start_date: Optional[date] = None
    period_end_date: Optional[date] = None
    submission_due_date: Optional[date] = None
    notes: Optional[str] = None


class AttestationCycleResponse(AttestationCycleBase):
    """Response schema for attestation cycle."""
    cycle_id: int
    status: AttestationCycleStatusEnum
    opened_at: Optional[datetime] = None
    opened_by: Optional[UserRef] = None
    closed_at: Optional[datetime] = None
    closed_by: Optional[UserRef] = None
    created_at: datetime
    updated_at: datetime
    # Computed fields
    total_records: int = 0
    pending_count: int = 0
    submitted_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0

    class Config:
        from_attributes = True


class AttestationCycleListResponse(BaseModel):
    """List response for attestation cycles (summary view)."""
    cycle_id: int
    cycle_name: str
    period_start_date: date
    period_end_date: date
    submission_due_date: date
    status: AttestationCycleStatusEnum
    total_records: int = 0
    pending_count: int = 0
    submitted_count: int = 0
    accepted_count: int = 0
    # Coverage info
    coverage_pct: float = 0.0

    class Config:
        from_attributes = True


# ============================================================================
# ATTESTATION RESPONSE SCHEMAS (answers to questions)
# ============================================================================

class AttestationResponseBase(BaseModel):
    """Base schema for attestation question response."""
    question_id: int
    answer: bool
    comment: Optional[str] = None


class AttestationResponseCreate(AttestationResponseBase):
    """Create schema for attestation question response."""
    pass


class AttestationResponseResponse(AttestationResponseBase):
    """Response schema for attestation question response."""
    response_id: int
    attestation_id: int
    question: Optional[AttestationQuestionResponse] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# ATTESTATION EVIDENCE SCHEMAS
# ============================================================================

class AttestationEvidenceBase(BaseModel):
    """Base schema for attestation evidence."""
    evidence_type: AttestationEvidenceTypeEnum = AttestationEvidenceTypeEnum.OTHER
    url: str = Field(..., max_length=2000)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator('url')
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        """Validate URL starts with http:// or https://."""
        if not v:
            raise ValueError('URL is required')
        if not re.match(r'^https?://', v, re.IGNORECASE):
            raise ValueError('URL must start with http:// or https://')
        return v


class AttestationEvidenceCreate(AttestationEvidenceBase):
    """Create schema for attestation evidence."""
    pass


class AttestationEvidenceResponse(AttestationEvidenceBase):
    """Response schema for attestation evidence."""
    evidence_id: int
    attestation_id: int
    added_by: UserRef
    added_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# ATTESTATION RECORD SCHEMAS
# ============================================================================

class AttestationRecordBase(BaseModel):
    """Base schema for attestation record."""
    pass


class AttestationSubmitRequest(BaseModel):
    """Request schema for submitting an attestation."""
    decision: AttestationDecisionEnum
    decision_comment: Optional[str] = None
    responses: List[AttestationResponseCreate]
    evidence: List[AttestationEvidenceCreate] = []


class AttestationReviewRequest(BaseModel):
    """Request schema for admin reviewing an attestation."""
    review_comment: Optional[str] = None


class AttestationRecordResponse(BaseModel):
    """Response schema for attestation record."""
    attestation_id: int
    cycle_id: int
    model: ModelRef
    attesting_user: UserRef
    due_date: date
    status: AttestationRecordStatusEnum
    attested_at: Optional[datetime] = None
    decision: Optional[AttestationDecisionEnum] = None
    decision_comment: Optional[str] = None
    reviewed_by: Optional[UserRef] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    responses: List[AttestationResponseResponse] = []
    evidence: List[AttestationEvidenceResponse] = []
    change_proposals: List["AttestationChangeProposalResponse"] = []
    created_at: datetime
    updated_at: datetime
    # Computed
    days_overdue: int = 0
    is_overdue: bool = False

    class Config:
        from_attributes = True


class AttestationRecordListResponse(BaseModel):
    """List response for attestation records (summary view)."""
    attestation_id: int
    cycle_id: int
    cycle_name: str
    model_id: int
    model_name: str
    risk_tier_code: Optional[str] = None
    owner_name: str
    attesting_user_name: str
    due_date: date
    status: AttestationRecordStatusEnum
    decision: Optional[AttestationDecisionEnum] = None
    attested_at: Optional[datetime] = None
    is_overdue: bool = False
    days_overdue: int = 0

    class Config:
        from_attributes = True


class MyAttestationResponse(BaseModel):
    """Response for user's upcoming/pending attestations."""
    attestation_id: int
    cycle_id: int
    cycle_name: str
    model_id: int
    model_name: str
    risk_tier_code: Optional[str] = None
    due_date: date
    status: AttestationRecordStatusEnum
    days_until_due: int  # Negative if overdue
    is_overdue: bool
    can_submit: bool  # Whether current user can submit

    class Config:
        from_attributes = True


# ============================================================================
# ATTESTATION SCHEDULING RULE SCHEMAS
# ============================================================================

class AttestationSchedulingRuleBase(BaseModel):
    """Base schema for attestation scheduling rule."""
    rule_name: str
    rule_type: AttestationSchedulingRuleTypeEnum
    frequency: AttestationFrequencyEnum
    priority: int = 10
    is_active: bool = True
    owner_model_count_min: Optional[int] = None
    owner_high_fluctuation_flag: Optional[bool] = None
    model_id: Optional[int] = None
    region_id: Optional[int] = None
    effective_date: date
    end_date: Optional[date] = None


class AttestationSchedulingRuleCreate(AttestationSchedulingRuleBase):
    """Create schema for attestation scheduling rule."""
    pass


class AttestationSchedulingRuleUpdate(BaseModel):
    """Update schema for attestation scheduling rule."""
    rule_name: Optional[str] = None
    frequency: Optional[AttestationFrequencyEnum] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    owner_model_count_min: Optional[int] = None
    owner_high_fluctuation_flag: Optional[bool] = None
    end_date: Optional[date] = None


class AttestationSchedulingRuleResponse(AttestationSchedulingRuleBase):
    """Response schema for attestation scheduling rule."""
    rule_id: int
    model: Optional[ModelRef] = None
    region: Optional[RegionRef] = None
    created_by: UserRef
    updated_by: Optional[UserRef] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# ATTESTATION CHANGE PROPOSAL SCHEMAS
# ============================================================================

class AttestationChangeProposalBase(BaseModel):
    """Base schema for attestation change proposal."""
    change_type: AttestationChangeTypeEnum
    model_id: Optional[int] = None
    proposed_data: Optional[dict] = None


class AttestationChangeProposalCreate(AttestationChangeProposalBase):
    """Create schema for attestation change proposal."""
    pass


class AttestationChangeProposalDecision(BaseModel):
    """Request schema for admin decision on change proposal."""
    admin_comment: Optional[str] = None


class AttestationChangeProposalResponse(AttestationChangeProposalBase):
    """Response schema for attestation change proposal."""
    proposal_id: int
    attestation_id: int
    pending_edit_id: Optional[int] = None
    status: AttestationChangeStatusEnum
    admin_comment: Optional[str] = None
    decided_by: Optional[UserRef] = None
    decided_at: Optional[datetime] = None
    created_at: datetime
    # Model info if UPDATE_EXISTING or DECOMMISSION
    model: Optional[ModelRef] = None

    class Config:
        from_attributes = True


# ============================================================================
# COVERAGE TARGET SCHEMAS
# ============================================================================

class CoverageTargetBase(BaseModel):
    """Base schema for coverage target."""
    risk_tier_id: int
    target_percentage: Decimal = Field(..., ge=0, le=100)
    is_blocking: bool = True
    effective_date: date
    end_date: Optional[date] = None


class CoverageTargetCreate(CoverageTargetBase):
    """Create schema for coverage target."""
    pass


class CoverageTargetUpdate(BaseModel):
    """Update schema for coverage target."""
    target_percentage: Optional[Decimal] = None
    is_blocking: Optional[bool] = None
    end_date: Optional[date] = None


class CoverageTargetResponse(CoverageTargetBase):
    """Response schema for coverage target."""
    target_id: int
    risk_tier: TaxonomyValueRef
    created_by: UserRef
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# COVERAGE REPORT SCHEMAS
# ============================================================================

class CoverageByTierResponse(BaseModel):
    """Coverage breakdown by risk tier."""
    risk_tier_code: str
    risk_tier_label: str
    total_models: int
    attested_count: int
    coverage_pct: float
    target_pct: float
    is_blocking: bool
    meets_target: bool
    gap: int  # Number of missing attestations


class CoverageReportResponse(BaseModel):
    """Full coverage report for a cycle."""
    cycle: AttestationCycleListResponse
    coverage_by_tier: List[CoverageByTierResponse]
    overall_coverage: dict  # total_models, attested_count, coverage_pct
    can_close_cycle: bool
    blocking_gaps: List[str]  # Messages for blocking targets not met
    models_not_attested: List[ModelRef]


# ============================================================================
# TIMELINESS REPORT SCHEMAS
# ============================================================================

class TimelinessItemResponse(BaseModel):
    """Individual past-due item in timeliness report."""
    attestation_id: int
    model_id: int
    model_name: str
    owner_name: str
    due_date: date
    days_overdue: int
    risk_tier: str


class TimelinessReportResponse(BaseModel):
    """Timeliness report for a cycle."""
    cycle: AttestationCycleListResponse
    timeliness_summary: dict  # total_due, submitted_on_time, submitted_late, still_pending, on_time_rate_pct, avg_days_to_submit
    past_due_items: List[TimelinessItemResponse]


# ============================================================================
# ADMIN DASHBOARD SCHEMAS
# ============================================================================

class AttestationDashboardStats(BaseModel):
    """Stats for attestation admin dashboard."""
    pending_count: int
    submitted_count: int
    overdue_count: int
    pending_changes: int
    active_cycles: int


class CycleReminderResponse(BaseModel):
    """Response for cycle reminder check."""
    should_show_reminder: bool
    suggested_cycle_name: Optional[str] = None
    last_cycle_end_date: Optional[date] = None
    message: Optional[str] = None


# ============================================================================
# OWNER DASHBOARD SCHEMAS
# ============================================================================

class OwnerAttestationWidgetResponse(BaseModel):
    """Response for owner attestation deadline widget."""
    upcoming_attestations: List[MyAttestationResponse]  # Next 14 days
    past_due_attestations: List[MyAttestationResponse]  # Past due
    total_upcoming: int
    total_past_due: int


# ============================================================================
# FORWARD REFERENCE RESOLUTION
# ============================================================================

# Rebuild models that use forward references to resolve them
AttestationRecordResponse.model_rebuild()
