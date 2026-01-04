"""
FRY 14 Reporting Schemas.

Pydantic models for FRY 14 reporting API requests and responses.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Line Item Schemas
# ============================================================================

class FryLineItemBase(BaseModel):
    """Base schema for FRY line item."""
    line_item_text: str
    sort_order: int = 0


class FryLineItemCreate(FryLineItemBase):
    """Schema for creating a FRY line item."""
    pass


class FryLineItemUpdate(BaseModel):
    """Schema for updating a FRY line item."""
    line_item_text: Optional[str] = None
    sort_order: Optional[int] = None


class FryLineItemResponse(FryLineItemBase):
    """Response schema for FRY line item."""
    line_item_id: int
    metric_group_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# ============================================================================
# Metric Group Schemas
# ============================================================================

class FryMetricGroupBase(BaseModel):
    """Base schema for FRY metric group."""
    metric_group_name: str
    model_driven: bool = False
    rationale: Optional[str] = None
    is_active: bool = True


    model_config = ConfigDict(protected_namespaces=())
class FryMetricGroupCreate(FryMetricGroupBase):
    """Schema for creating a FRY metric group."""
    pass


class FryMetricGroupUpdate(BaseModel):
    """Schema for updating a FRY metric group."""
    metric_group_name: Optional[str] = None
    model_driven: Optional[bool] = None
    rationale: Optional[str] = None
    is_active: Optional[bool] = None


    model_config = ConfigDict(protected_namespaces=())
class FryMetricGroupResponse(FryMetricGroupBase):
    """Response schema for FRY metric group."""
    metric_group_id: int
    schedule_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class FryMetricGroupWithLineItems(FryMetricGroupResponse):
    """Response schema for FRY metric group with line items."""
    line_items: List[FryLineItemResponse] = []

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# ============================================================================
# Schedule Schemas
# ============================================================================

class FryScheduleBase(BaseModel):
    """Base schema for FRY schedule."""
    schedule_code: str
    description: Optional[str] = None
    is_active: bool = True


class FryScheduleCreate(FryScheduleBase):
    """Schema for creating a FRY schedule."""
    pass


class FryScheduleUpdate(BaseModel):
    """Schema for updating a FRY schedule."""
    schedule_code: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class FryScheduleResponse(FryScheduleBase):
    """Response schema for FRY schedule."""
    schedule_id: int
    report_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class FryScheduleWithMetricGroups(FryScheduleResponse):
    """Response schema for FRY schedule with metric groups."""
    metric_groups: List[FryMetricGroupWithLineItems] = []

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# ============================================================================
# Report Schemas
# ============================================================================

class FryReportBase(BaseModel):
    """Base schema for FRY report."""
    report_code: str
    description: Optional[str] = None
    is_active: bool = True


class FryReportCreate(FryReportBase):
    """Schema for creating a FRY report."""
    pass


class FryReportUpdate(BaseModel):
    """Schema for updating a FRY report."""
    report_code: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class FryReportResponse(FryReportBase):
    """Response schema for FRY report."""
    report_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class FryReportWithSchedules(FryReportResponse):
    """Response schema for FRY report with schedules."""
    schedules: List[FryScheduleWithMetricGroups] = []

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# ============================================================================
# Summary Schemas
# ============================================================================

class FryMetricGroupSummary(BaseModel):
    """Summary schema for FRY metric group (without line items)."""
    metric_group_id: int
    metric_group_name: str
    model_driven: bool
    is_active: bool
    line_item_count: int

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class FryScheduleSummary(BaseModel):
    """Summary schema for FRY schedule (with metric group counts)."""
    schedule_id: int
    schedule_code: str
    is_active: bool
    metric_group_count: int

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class FryReportSummary(BaseModel):
    """Summary schema for FRY report (with schedule counts)."""
    report_id: int
    report_code: str
    is_active: bool
    schedule_count: int

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
