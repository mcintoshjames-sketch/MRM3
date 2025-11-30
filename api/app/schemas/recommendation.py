"""Model Recommendations schemas."""
from pydantic import BaseModel, Field, model_validator
from datetime import datetime, date
from typing import Optional, List, Any
from app.schemas.taxonomy import TaxonomyValueResponse
from app.schemas.region import Region


# ==================== HELPER SCHEMAS ====================

class UserSummary(BaseModel):
    """Minimal user info for recommendation responses."""
    user_id: int
    full_name: str
    email: str
    role: str

    class Config:
        from_attributes = True


class ModelSummary(BaseModel):
    """Minimal model info for recommendation responses."""
    model_id: int
    model_name: str
    status: str

    class Config:
        from_attributes = True


class ValidationRequestSummary(BaseModel):
    """Minimal validation request info for recommendation responses."""
    request_id: int
    validation_type: Optional[str] = None

    class Config:
        from_attributes = True

    @model_validator(mode='before')
    @classmethod
    def extract_validation_type_label(cls, data: Any) -> Any:
        """Extract validation_type label from ORM relationship object."""
        if isinstance(data, dict):
            return data
        # Handle ORM object - extract label from validation_type relationship
        if hasattr(data, 'request_id'):
            validation_type_label = None
            if hasattr(data, 'validation_type') and data.validation_type is not None:
                validation_type_label = getattr(data.validation_type, 'label', None)
            return {
                'request_id': data.request_id,
                'validation_type': validation_type_label
            }
        return data


class MonitoringCycleSummary(BaseModel):
    """Minimal monitoring cycle info for recommendation responses."""
    cycle_id: int
    period_start: date
    period_end: date
    plan_name: Optional[str] = None

    class Config:
        from_attributes = True

    @model_validator(mode='before')
    @classmethod
    def extract_plan_name(cls, data: Any) -> Any:
        """Extract plan_name from ORM relationship object."""
        if isinstance(data, dict):
            return data
        # Handle ORM object - extract plan_name from plan relationship
        if hasattr(data, 'cycle_id'):
            plan_name = None
            if hasattr(data, 'plan') and data.plan is not None:
                plan_name = getattr(data.plan, 'plan_name', None)
            return {
                'cycle_id': data.cycle_id,
                'period_start': data.period_start,
                'period_end': data.period_end,
                'plan_name': plan_name
            }
        return data


# ==================== ACTION PLAN TASK SCHEMAS ====================

class ActionPlanTaskBase(BaseModel):
    """Base schema for action plan task."""
    description: str
    owner_id: int
    target_date: date
    completion_notes: Optional[str] = None


class ActionPlanTaskCreate(ActionPlanTaskBase):
    """Schema for creating an action plan task."""
    pass


class ActionPlanTaskUpdate(BaseModel):
    """Schema for updating an action plan task."""
    description: Optional[str] = None
    owner_id: Optional[int] = None
    target_date: Optional[date] = None
    completion_status_id: Optional[int] = None
    completion_notes: Optional[str] = None


class ActionPlanTaskResponse(BaseModel):
    """Response schema for action plan task."""
    task_id: int
    recommendation_id: int
    task_order: int
    description: str
    owner: UserSummary
    target_date: date
    completed_date: Optional[date] = None
    completion_status: TaxonomyValueResponse
    completion_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== REBUTTAL SCHEMAS ====================

class RebuttalCreate(BaseModel):
    """Schema for creating a rebuttal."""
    rationale: str
    supporting_evidence: Optional[str] = None


class RebuttalReviewRequest(BaseModel):
    """Schema for reviewing a rebuttal."""
    decision: str = Field(..., description="ACCEPT or OVERRIDE")
    comments: Optional[str] = None


class RebuttalResponse(BaseModel):
    """Response schema for rebuttal."""
    rebuttal_id: int
    recommendation_id: int
    submitted_by: UserSummary
    rationale: str
    supporting_evidence: Optional[str] = None
    submitted_at: datetime
    reviewed_by: Optional[UserSummary] = None
    reviewed_at: Optional[datetime] = None
    review_decision: Optional[str] = None
    review_comments: Optional[str] = None
    is_current: bool

    class Config:
        from_attributes = True


class RebuttalReviewResponse(BaseModel):
    """Response schema after reviewing a rebuttal."""
    rebuttal_id: int
    review_decision: str
    reviewed_by: UserSummary
    reviewed_at: datetime
    recommendation: "RecommendationResponse"

    class Config:
        from_attributes = True


# ==================== CLOSURE EVIDENCE SCHEMAS ====================

class ClosureEvidenceCreate(BaseModel):
    """Schema for uploading closure evidence."""
    file_name: str
    file_path: str
    file_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    description: Optional[str] = None


class ClosureEvidenceResponse(BaseModel):
    """Response schema for closure evidence."""
    evidence_id: int
    recommendation_id: int
    file_name: str
    file_path: str
    file_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    description: Optional[str] = None
    uploaded_by: UserSummary
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ==================== STATUS HISTORY SCHEMAS ====================

class StatusHistoryResponse(BaseModel):
    """Response schema for status history."""
    history_id: int
    recommendation_id: int
    old_status: Optional[TaxonomyValueResponse] = None
    new_status: TaxonomyValueResponse
    changed_by: UserSummary
    changed_at: datetime
    change_reason: Optional[str] = None
    additional_context: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== APPROVAL SCHEMAS ====================

class ApprovalResponse(BaseModel):
    """Response schema for recommendation approval."""
    approval_id: int
    recommendation_id: int
    approval_type: str
    region: Optional[Region] = None
    represented_region: Optional[Region] = None
    approver: Optional[UserSummary] = None
    approved_at: Optional[datetime] = None
    is_required: bool
    approval_status: str
    comments: Optional[str] = None
    approval_evidence: Optional[str] = None
    voided_by: Optional[UserSummary] = None
    void_reason: Optional[str] = None
    voided_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalRequest(BaseModel):
    """Schema for approving a recommendation."""
    comments: Optional[str] = None
    approval_evidence: Optional[str] = None


class ApprovalRejectRequest(BaseModel):
    """Schema for rejecting or voiding a recommendation approval."""
    rejection_reason: str


# ==================== PRIORITY CONFIG SCHEMAS ====================

class PriorityConfigCreate(BaseModel):
    """Schema for creating priority configuration."""
    priority_id: int
    requires_final_approval: bool = True
    description: Optional[str] = None


class PriorityConfigUpdate(BaseModel):
    """Schema for updating priority configuration."""
    requires_final_approval: Optional[bool] = None
    description: Optional[str] = None


class PriorityConfigResponse(BaseModel):
    """Response schema for priority configuration."""
    config_id: int
    priority: TaxonomyValueResponse
    requires_final_approval: bool
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== RECOMMENDATION SCHEMAS ====================

class RecommendationBase(BaseModel):
    """Base schema for recommendation."""
    model_id: int
    validation_request_id: Optional[int] = None
    monitoring_cycle_id: Optional[int] = None
    title: str
    description: str
    root_cause_analysis: Optional[str] = None
    priority_id: int
    category_id: Optional[int] = None
    assigned_to_id: int
    original_target_date: date


class RecommendationCreate(RecommendationBase):
    """Schema for creating a recommendation."""
    pass


class RecommendationUpdate(BaseModel):
    """Schema for updating a recommendation."""
    title: Optional[str] = None
    description: Optional[str] = None
    root_cause_analysis: Optional[str] = None
    category_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    current_target_date: Optional[date] = None


class RecommendationResponse(BaseModel):
    """Full response schema for recommendation."""
    recommendation_id: int
    recommendation_code: str
    model: ModelSummary
    # Source linkage (optional - at least one should be set)
    validation_request_id: Optional[int] = None
    validation_request: Optional[ValidationRequestSummary] = None
    monitoring_cycle_id: Optional[int] = None
    monitoring_cycle: Optional[MonitoringCycleSummary] = None
    title: str
    description: str
    root_cause_analysis: Optional[str] = None
    priority: TaxonomyValueResponse
    category: Optional[TaxonomyValueResponse] = None
    current_status: TaxonomyValueResponse
    created_by: UserSummary
    assigned_to: UserSummary
    original_target_date: date
    current_target_date: date
    finalized_at: Optional[datetime] = None
    finalized_by: Optional[UserSummary] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[UserSummary] = None
    closed_at: Optional[datetime] = None
    closed_by: Optional[UserSummary] = None
    closure_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # Nested relationships
    action_plan_tasks: List[ActionPlanTaskResponse] = []
    rebuttals: List[RebuttalResponse] = []
    closure_evidence: List[ClosureEvidenceResponse] = []
    status_history: List[StatusHistoryResponse] = []
    approvals: List[ApprovalResponse] = []

    class Config:
        from_attributes = True


class RecommendationListResponse(BaseModel):
    """Minimal response schema for recommendation list."""
    recommendation_id: int
    recommendation_code: str
    model: ModelSummary
    title: str
    # Source linkage info
    validation_request_id: Optional[int] = None
    monitoring_cycle_id: Optional[int] = None
    source_type: Optional[str] = None  # "validation" or "monitoring" or None
    priority: TaxonomyValueResponse
    category: Optional[TaxonomyValueResponse] = None
    current_status: TaxonomyValueResponse
    assigned_to: UserSummary
    original_target_date: date
    current_target_date: date
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== ACTION PLAN SUBMISSION SCHEMAS ====================

class ActionPlanSubmission(BaseModel):
    """Schema for submitting an action plan with tasks."""
    tasks: List[ActionPlanTaskCreate]


class ActionPlanRevisionRequest(BaseModel):
    """Schema for requesting revisions to an action plan."""
    reason: str


# ==================== CLOSURE WORKFLOW SCHEMAS ====================

class ClosureReviewRequest(BaseModel):
    """Schema for validator reviewing closure submission."""
    decision: str = Field(..., description="APPROVE or RETURN")
    comments: Optional[str] = None
    closure_summary: Optional[str] = None


class DeclineAcknowledgementRequest(BaseModel):
    """Schema for developer declining acknowledgement."""
    reason: str


# ==================== REBUTTAL SUBMISSION RESPONSE ====================

class RebuttalSubmissionResponse(BaseModel):
    """Response after submitting a rebuttal."""
    rebuttal_id: int
    recommendation: RecommendationResponse

    class Config:
        from_attributes = True


# ==================== DASHBOARD & REPORTS SCHEMAS ====================

class MyTaskItem(BaseModel):
    """Individual task item for my-tasks endpoint."""
    task_type: str  # "ACTION_REQUIRED", "REVIEW_PENDING", "APPROVAL_PENDING"
    recommendation_id: int
    recommendation_code: str
    title: str
    model: ModelSummary
    priority: TaxonomyValueResponse
    current_status: TaxonomyValueResponse
    current_target_date: date
    action_description: str
    days_until_due: Optional[int] = None
    is_overdue: bool = False

    class Config:
        from_attributes = True


class MyTasksResponse(BaseModel):
    """Response for my-tasks endpoint."""
    total_tasks: int
    overdue_count: int
    tasks: List[MyTaskItem]


class StatusSummary(BaseModel):
    """Count of recommendations by status."""
    status_code: str
    status_label: str
    count: int


class PrioritySummary(BaseModel):
    """Count of recommendations by priority."""
    priority_code: str
    priority_label: str
    count: int


class OpenRecommendationsSummary(BaseModel):
    """Summary of open (non-terminal) recommendations."""
    total_open: int
    by_status: List[StatusSummary]
    by_priority: List[PrioritySummary]


class OverdueRecommendation(BaseModel):
    """Overdue recommendation item."""
    recommendation_id: int
    recommendation_code: str
    title: str
    model: ModelSummary
    priority: TaxonomyValueResponse
    current_status: TaxonomyValueResponse
    assigned_to: UserSummary
    current_target_date: date
    days_overdue: int

    class Config:
        from_attributes = True


class OverdueRecommendationsReport(BaseModel):
    """Report of overdue recommendations."""
    total_overdue: int
    by_priority: List[PrioritySummary]
    recommendations: List[OverdueRecommendation]


# Update forward references
RebuttalReviewResponse.model_rebuild()
