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

    class Config:
        from_attributes = True
