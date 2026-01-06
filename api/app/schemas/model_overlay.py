"""Model Overlays schemas."""
from datetime import datetime, date
from typing import Optional, List, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class UserSummary(BaseModel):
    """Minimal user info for overlay responses."""
    user_id: int
    full_name: str
    email: str

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ModelSummary(BaseModel):
    """Minimal model info for overlay responses."""
    model_id: int
    model_name: str
    status: str

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class RegionSummary(BaseModel):
    """Minimal region info for overlay responses."""
    region_id: int
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class MonitoringResultSummary(BaseModel):
    """Minimal monitoring result info for overlay responses."""
    result_id: int
    cycle_id: int
    model_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class MonitoringCycleSummary(BaseModel):
    """Minimal monitoring cycle info for overlay responses."""
    cycle_id: int
    period_start_date: date
    period_end_date: date
    status: str

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class RecommendationSummary(BaseModel):
    """Minimal recommendation info for overlay responses."""
    recommendation_id: int
    recommendation_code: str
    title: str

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class LimitationSummary(BaseModel):
    """Minimal limitation info for overlay responses."""
    limitation_id: int
    description: str

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ModelOverlayBase(BaseModel):
    """Base schema for overlays."""
    overlay_kind: Literal["OVERLAY", "MANAGEMENT_JUDGEMENT"]
    is_underperformance_related: bool
    description: str = Field(..., min_length=1)
    rationale: str = Field(..., min_length=1)
    effective_from: date
    effective_to: Optional[date] = None
    region_id: Optional[int] = None
    trigger_monitoring_result_id: Optional[int] = None
    trigger_monitoring_cycle_id: Optional[int] = None
    related_recommendation_id: Optional[int] = None
    related_limitation_id: Optional[int] = None
    evidence_description: Optional[str] = None

    @model_validator(mode='after')
    def validate_effective_window(self):
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot be earlier than effective_from")
        return self

    model_config = ConfigDict(protected_namespaces=())


class ModelOverlayCreate(ModelOverlayBase):
    """Schema for creating overlays."""
    pass


class ModelOverlayUpdate(BaseModel):
    """Schema for updating overlay evidence and link fields."""
    evidence_description: Optional[str] = None
    trigger_monitoring_result_id: Optional[int] = None
    trigger_monitoring_cycle_id: Optional[int] = None
    related_recommendation_id: Optional[int] = None
    related_limitation_id: Optional[int] = None

    model_config = ConfigDict(protected_namespaces=())


class ModelOverlayRetire(BaseModel):
    """Schema for retiring overlays."""
    retirement_reason: str = Field(..., min_length=1)


class ModelOverlayResponse(BaseModel):
    """Detailed overlay response."""
    overlay_id: int
    model_id: int
    model: ModelSummary
    overlay_kind: str
    is_underperformance_related: bool
    description: str
    rationale: str
    effective_from: date
    effective_to: Optional[date] = None
    region_id: Optional[int] = None
    region: Optional[RegionSummary] = None
    trigger_monitoring_result_id: Optional[int] = None
    trigger_monitoring_result: Optional[MonitoringResultSummary] = None
    trigger_monitoring_cycle_id: Optional[int] = None
    trigger_monitoring_cycle: Optional[MonitoringCycleSummary] = None
    related_recommendation_id: Optional[int] = None
    related_recommendation: Optional[RecommendationSummary] = None
    related_limitation_id: Optional[int] = None
    related_limitation: Optional[LimitationSummary] = None
    evidence_description: Optional[str] = None
    is_retired: bool
    retirement_date: Optional[datetime] = None
    retirement_reason: Optional[str] = None
    retired_by: Optional[UserSummary] = None
    created_by: UserSummary
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ModelOverlayListResponse(BaseModel):
    """List response schema for overlays."""
    overlay_id: int
    model_id: int
    overlay_kind: str
    is_underperformance_related: bool
    description: str
    rationale: str
    effective_from: date
    effective_to: Optional[date] = None
    region_id: Optional[int] = None
    region: Optional[RegionSummary] = None
    trigger_monitoring_result_id: Optional[int] = None
    trigger_monitoring_cycle_id: Optional[int] = None
    related_recommendation_id: Optional[int] = None
    related_limitation_id: Optional[int] = None
    evidence_description: Optional[str] = None
    is_retired: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ModelOverlayReportItem(BaseModel):
    """Item in the model overlays report."""
    overlay_id: int
    model_id: int
    model_name: str
    model_status: str
    risk_tier: Optional[str] = None
    risk_tier_code: Optional[str] = None
    team_name: Optional[str] = None
    overlay_kind: str
    is_underperformance_related: bool
    description: str
    rationale: str
    effective_from: date
    effective_to: Optional[date] = None
    region_name: Optional[str] = None
    region_code: Optional[str] = None
    evidence_description: Optional[str] = None
    trigger_monitoring_result_id: Optional[int] = None
    trigger_monitoring_cycle_id: Optional[int] = None
    related_recommendation_id: Optional[int] = None
    related_limitation_id: Optional[int] = None
    has_monitoring_traceability: bool
    created_at: datetime

    model_config = ConfigDict(protected_namespaces=())


class ModelOverlaysReportResponse(BaseModel):
    """Response for model overlays report."""
    filters_applied: dict
    total_count: int
    items: List[ModelOverlayReportItem]
