"""Monitoring Plans and Teams schemas."""
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel
from enum import Enum


class MonitoringFrequency(str, Enum):
    """Monitoring plan frequency."""
    MONTHLY = "Monthly"
    QUARTERLY = "Quarterly"
    SEMI_ANNUAL = "Semi-Annual"
    ANNUAL = "Annual"


# ============================================================================
# USER REFERENCE (for team members and data providers)
# ============================================================================

class UserRef(BaseModel):
    """Minimal user reference."""
    user_id: int
    email: str
    full_name: str

    class Config:
        from_attributes = True


# ============================================================================
# MODEL REFERENCE (for plan scope)
# ============================================================================

class ModelRef(BaseModel):
    """Minimal model reference."""
    model_id: int
    model_name: str

    class Config:
        from_attributes = True


# ============================================================================
# KPM REFERENCE (for plan metrics)
# ============================================================================

class KpmRef(BaseModel):
    """Minimal KPM reference."""
    kpm_id: int
    name: str
    category_id: int
    evaluation_type: Optional[str] = "Quantitative"

    class Config:
        from_attributes = True


# ============================================================================
# MONITORING TEAM SCHEMAS
# ============================================================================

class MonitoringTeamBase(BaseModel):
    """Base schema for monitoring team."""
    name: str
    description: Optional[str] = None
    is_active: bool = True


class MonitoringTeamCreate(MonitoringTeamBase):
    """Create schema for monitoring team."""
    member_ids: List[int] = []


class MonitoringTeamUpdate(BaseModel):
    """Update schema for monitoring team (all fields optional)."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    member_ids: Optional[List[int]] = None


class MonitoringTeamResponse(MonitoringTeamBase):
    """Response schema for monitoring team."""
    team_id: int
    members: List[UserRef] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MonitoringTeamListResponse(BaseModel):
    """List response for monitoring team (without members for performance)."""
    team_id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    member_count: int = 0
    plan_count: int = 0

    class Config:
        from_attributes = True


# ============================================================================
# MONITORING PLAN METRIC SCHEMAS
# ============================================================================

class MonitoringPlanMetricBase(BaseModel):
    """Base schema for monitoring plan metric."""
    kpm_id: int
    yellow_min: Optional[float] = None
    yellow_max: Optional[float] = None
    red_min: Optional[float] = None
    red_max: Optional[float] = None
    qualitative_guidance: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True


class MonitoringPlanMetricCreate(MonitoringPlanMetricBase):
    """Create schema for monitoring plan metric."""
    pass


class MonitoringPlanMetricUpdate(BaseModel):
    """Update schema for monitoring plan metric (all fields optional)."""
    kpm_id: Optional[int] = None
    yellow_min: Optional[float] = None
    yellow_max: Optional[float] = None
    red_min: Optional[float] = None
    red_max: Optional[float] = None
    qualitative_guidance: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class MonitoringPlanMetricResponse(MonitoringPlanMetricBase):
    """Response schema for monitoring plan metric."""
    metric_id: int
    plan_id: int
    kpm: KpmRef

    class Config:
        from_attributes = True


# ============================================================================
# MONITORING PLAN SCHEMAS
# ============================================================================

class MonitoringPlanBase(BaseModel):
    """Base schema for monitoring plan."""
    name: str
    description: Optional[str] = None
    frequency: MonitoringFrequency = MonitoringFrequency.QUARTERLY
    monitoring_team_id: Optional[int] = None
    data_provider_user_id: Optional[int] = None
    reporting_lead_days: int = 30
    is_active: bool = True


class MonitoringPlanCreate(MonitoringPlanBase):
    """Create schema for monitoring plan."""
    model_ids: List[int] = []
    metrics: List[MonitoringPlanMetricCreate] = []
    # Optional: set initial submission due date (defaults to calculated from frequency)
    next_submission_due_date: Optional[date] = None


class MonitoringPlanUpdate(BaseModel):
    """Update schema for monitoring plan (all fields optional)."""
    name: Optional[str] = None
    description: Optional[str] = None
    frequency: Optional[MonitoringFrequency] = None
    monitoring_team_id: Optional[int] = None
    data_provider_user_id: Optional[int] = None
    reporting_lead_days: Optional[int] = None
    next_submission_due_date: Optional[date] = None
    is_active: Optional[bool] = None
    model_ids: Optional[List[int]] = None


class MonitoringPlanResponse(MonitoringPlanBase):
    """Response schema for monitoring plan."""
    plan_id: int
    next_submission_due_date: Optional[date] = None
    next_report_due_date: Optional[date] = None
    team: Optional[MonitoringTeamListResponse] = None
    data_provider: Optional[UserRef] = None
    models: List[ModelRef] = []
    metrics: List[MonitoringPlanMetricResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MonitoringPlanListResponse(BaseModel):
    """List response for monitoring plan (summary view)."""
    plan_id: int
    name: str
    description: Optional[str] = None
    frequency: MonitoringFrequency
    is_active: bool
    next_submission_due_date: Optional[date] = None
    next_report_due_date: Optional[date] = None
    team_name: Optional[str] = None
    data_provider_name: Optional[str] = None
    model_count: int = 0
    metric_count: int = 0
    version_count: int = 0
    active_version_number: Optional[int] = None

    class Config:
        from_attributes = True


# ============================================================================
# MONITORING PLAN VERSION SCHEMAS
# ============================================================================

class PublishVersionRequest(BaseModel):
    """Request to publish a new plan version."""
    version_name: Optional[str] = None
    description: Optional[str] = None
    effective_date: Optional[date] = None  # Defaults to today


class MetricSnapshotResponse(BaseModel):
    """Response for a metric snapshot within a version."""
    snapshot_id: int
    kpm_id: int
    kpm_name: str
    kpm_category_name: Optional[str] = None
    evaluation_type: str
    yellow_min: Optional[float] = None
    yellow_max: Optional[float] = None
    red_min: Optional[float] = None
    red_max: Optional[float] = None
    qualitative_guidance: Optional[str] = None
    sort_order: int

    class Config:
        from_attributes = True


class MonitoringPlanVersionResponse(BaseModel):
    """Summary response for a plan version."""
    version_id: int
    plan_id: int
    version_number: int
    version_name: Optional[str] = None
    description: Optional[str] = None
    effective_date: date
    published_by: Optional[UserRef] = None
    published_at: datetime
    is_active: bool
    metrics_count: int = 0
    cycles_count: int = 0

    class Config:
        from_attributes = True


class MonitoringPlanVersionDetailResponse(MonitoringPlanVersionResponse):
    """Detailed response including metric snapshots."""
    metric_snapshots: List[MetricSnapshotResponse] = []


class MonitoringPlanVersionListResponse(BaseModel):
    """List response for monitoring plan versions."""
    version_id: int
    version_number: int
    version_name: Optional[str] = None
    effective_date: date
    published_by_name: Optional[str] = None
    published_at: datetime
    is_active: bool
    metrics_count: int = 0
    cycles_count: int = 0

    class Config:
        from_attributes = True


class ModelMonitoringPlanResponse(BaseModel):
    """Monitoring plan info for model lookup (component 9b)."""
    plan_id: int
    plan_name: str
    frequency: MonitoringFrequency
    active_version: Optional[MonitoringPlanVersionResponse] = None
    all_versions: List[MonitoringPlanVersionResponse] = []
    latest_cycle_status: Optional[str] = None
    latest_cycle_outcome_summary: Optional[str] = None


# ============================================================================
# ACTIVE CYCLES WARNING SCHEMA
# ============================================================================

class ActiveCyclesWarning(BaseModel):
    """Warning info when editing metrics with active cycles."""
    warning: bool = False
    message: str = ""
    active_cycle_count: int = 0


# ============================================================================
# MONITORING CYCLE STATUS ENUM
# ============================================================================

class MonitoringCycleStatusEnum(str, Enum):
    """Monitoring cycle status workflow states."""
    PENDING = "PENDING"
    DATA_COLLECTION = "DATA_COLLECTION"
    UNDER_REVIEW = "UNDER_REVIEW"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    CANCELLED = "CANCELLED"


# ============================================================================
# MONITORING CYCLE SCHEMAS
# ============================================================================

class MonitoringCycleBase(BaseModel):
    """Base schema for monitoring cycle."""
    period_start_date: date
    period_end_date: date
    submission_due_date: date
    report_due_date: date
    assigned_to_user_id: Optional[int] = None
    notes: Optional[str] = None


class MonitoringCycleCreate(BaseModel):
    """Create schema for monitoring cycle."""
    period_start_date: Optional[date] = None  # Auto-calculated if not provided
    period_end_date: Optional[date] = None    # Auto-calculated if not provided
    assigned_to_user_id: Optional[int] = None
    notes: Optional[str] = None


class MonitoringCycleUpdate(BaseModel):
    """Update schema for monitoring cycle."""
    assigned_to_user_id: Optional[int] = None
    notes: Optional[str] = None


class MonitoringCycleVersionRef(BaseModel):
    """Version reference for cycle."""
    version_id: int
    version_number: int
    version_name: Optional[str] = None

    class Config:
        from_attributes = True


class MonitoringCycleResponse(BaseModel):
    """Response schema for monitoring cycle."""
    cycle_id: int
    plan_id: int
    period_start_date: date
    period_end_date: date
    submission_due_date: date
    report_due_date: date
    status: MonitoringCycleStatusEnum
    assigned_to: Optional[UserRef] = None
    submitted_at: Optional[datetime] = None
    submitted_by: Optional[UserRef] = None
    completed_at: Optional[datetime] = None
    completed_by: Optional[UserRef] = None
    notes: Optional[str] = None
    # Version tracking
    plan_version_id: Optional[int] = None
    plan_version: Optional[MonitoringCycleVersionRef] = None
    version_locked_at: Optional[datetime] = None
    version_locked_by: Optional[UserRef] = None
    created_at: datetime
    updated_at: datetime
    # Computed fields
    result_count: int = 0
    approval_count: int = 0
    pending_approval_count: int = 0

    class Config:
        from_attributes = True


class MonitoringCycleListResponse(BaseModel):
    """List response for monitoring cycle (summary view)."""
    cycle_id: int
    plan_id: int
    period_start_date: date
    period_end_date: date
    status: MonitoringCycleStatusEnum
    submission_due_date: date
    report_due_date: date
    assigned_to_name: Optional[str] = None
    # Version info
    plan_version_id: Optional[int] = None
    version_number: Optional[int] = None
    version_name: Optional[str] = None
    result_count: int = 0
    green_count: int = 0
    yellow_count: int = 0
    red_count: int = 0

    class Config:
        from_attributes = True


# ============================================================================
# MONITORING CYCLE APPROVAL SCHEMAS
# ============================================================================

class RegionRef(BaseModel):
    """Minimal region reference."""
    region_id: int
    region_name: str
    region_code: str

    class Config:
        from_attributes = True


class MonitoringCycleApprovalBase(BaseModel):
    """Base schema for monitoring cycle approval."""
    approval_type: str = "Global"  # 'Global' or 'Regional'
    region_id: Optional[int] = None
    is_required: bool = True


class MonitoringCycleApprovalCreate(MonitoringCycleApprovalBase):
    """Create schema for monitoring cycle approval."""
    pass


class MonitoringCycleApprovalResponse(BaseModel):
    """Response schema for monitoring cycle approval."""
    approval_id: int
    cycle_id: int
    approval_type: str
    region: Optional[RegionRef] = None
    approver: Optional[UserRef] = None
    represented_region: Optional[RegionRef] = None
    is_required: bool
    approval_status: str
    comments: Optional[str] = None
    approved_at: Optional[datetime] = None
    voided_by: Optional[UserRef] = None
    void_reason: Optional[str] = None
    voided_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApproveRequest(BaseModel):
    """Request schema for approving a cycle."""
    comments: Optional[str] = None


class RejectRequest(BaseModel):
    """Request schema for rejecting a cycle."""
    comments: str


class VoidApprovalRequest(BaseModel):
    """Request schema for voiding an approval requirement."""
    void_reason: str


# ============================================================================
# MONITORING RESULT SCHEMAS
# ============================================================================

class MonitoringResultBase(BaseModel):
    """Base schema for monitoring result."""
    plan_metric_id: int
    model_id: Optional[int] = None
    numeric_value: Optional[float] = None
    outcome_value_id: Optional[int] = None
    narrative: Optional[str] = None
    supporting_data: Optional[dict] = None


class MonitoringResultCreate(MonitoringResultBase):
    """Create schema for monitoring result."""
    pass


class MonitoringResultUpdate(BaseModel):
    """Update schema for monitoring result."""
    numeric_value: Optional[float] = None
    outcome_value_id: Optional[int] = None
    narrative: Optional[str] = None
    supporting_data: Optional[dict] = None


class OutcomeValueRef(BaseModel):
    """Minimal outcome value reference."""
    value_id: int
    code: str
    label: str

    class Config:
        from_attributes = True


class MonitoringResultResponse(BaseModel):
    """Response schema for monitoring result."""
    result_id: int
    cycle_id: int
    plan_metric_id: int
    model: Optional[ModelRef] = None
    numeric_value: Optional[float] = None
    outcome_value: Optional[OutcomeValueRef] = None
    calculated_outcome: Optional[str] = None
    narrative: Optional[str] = None
    supporting_data: Optional[dict] = None
    entered_by: UserRef
    entered_at: datetime
    updated_at: datetime
    # Include metric info for context
    metric: Optional[MonitoringPlanMetricResponse] = None

    class Config:
        from_attributes = True


class MonitoringResultListResponse(BaseModel):
    """List response for monitoring results."""
    result_id: int
    cycle_id: int
    plan_metric_id: int
    model_id: Optional[int] = None
    model_name: Optional[str] = None
    metric_name: str
    numeric_value: Optional[float] = None
    calculated_outcome: Optional[str] = None
    entered_by_name: str
    entered_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# WORKFLOW ACTION SCHEMAS
# ============================================================================

class CycleStartRequest(BaseModel):
    """Request schema for starting a cycle."""
    pass


class CycleSubmitRequest(BaseModel):
    """Request schema for submitting cycle results."""
    pass


class CycleRequestApprovalRequest(BaseModel):
    """Request schema for requesting approval."""
    pass


class CycleCancelRequest(BaseModel):
    """Request schema for cancelling a cycle."""
    cancel_reason: str


# ============================================================================
# REPORTING SCHEMAS
# ============================================================================

class MetricTrendPoint(BaseModel):
    """Single data point in a metric trend."""
    cycle_id: int
    period_end_date: date
    numeric_value: Optional[float] = None
    calculated_outcome: Optional[str] = None
    model_id: Optional[int] = None
    model_name: Optional[str] = None


class MetricTrendResponse(BaseModel):
    """Response schema for metric trend data."""
    plan_metric_id: int
    metric_name: str
    kpm_name: str
    evaluation_type: str
    data_points: List[MetricTrendPoint] = []


class PerformanceSummary(BaseModel):
    """Summary of performance outcomes."""
    total_results: int
    green_count: int
    yellow_count: int
    red_count: int
    na_count: int
    by_metric: List[dict] = []
