"""Pydantic schemas for version deployment tasks."""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class VersionDeploymentTaskBase(BaseModel):
    """Base schema for version deployment tasks."""
    planned_production_date: date
    confirmation_notes: Optional[str] = None


class VersionDeploymentTaskConfirm(BaseModel):
    """Schema for confirming a deployment task."""
    actual_production_date: date
    confirmation_notes: Optional[str] = None
    validation_override_reason: Optional[str] = Field(
        None,
        description="Required if deploying before validation is approved"
    )


class VersionDeploymentTaskAdjust(BaseModel):
    """Schema for adjusting a planned production date."""
    planned_production_date: date
    adjustment_reason: str


class VersionDeploymentTaskCancel(BaseModel):
    """Schema for cancelling a deployment task."""
    cancellation_reason: str


class ModelInfo(BaseModel):
    """Minimal model info for task display."""
    model_id: int
    model_name: str


class VersionInfo(BaseModel):
    """Minimal version info for task display."""
    version_id: int
    version_number: str
    change_description: str


class RegionInfo(BaseModel):
    """Minimal region info for task display."""
    region_id: int
    code: str
    name: str


class UserInfo(BaseModel):
    """Minimal user info for task display."""
    user_id: int
    full_name: str
    email: str


class ValidationRequestInfo(BaseModel):
    """Minimal validation request info."""
    request_id: int
    current_status: str
    target_completion_date: date


class VersionDeploymentTaskResponse(BaseModel):
    """Full schema for version deployment task response."""
    task_id: int
    version_id: int
    model_id: int
    region_id: Optional[int]

    # Task details
    planned_production_date: date
    actual_production_date: Optional[date]

    # Assignment
    assigned_to_id: int

    # Status
    status: str
    confirmation_notes: Optional[str]
    confirmed_at: Optional[datetime]
    confirmed_by_id: Optional[int]

    # Validation override tracking
    deployed_before_validation_approved: bool
    validation_override_reason: Optional[str]

    # Timestamps
    created_at: datetime

    # Relationships
    model: ModelInfo
    version: VersionInfo
    region: Optional[RegionInfo]
    assigned_to: UserInfo
    confirmed_by: Optional[UserInfo]

    # Optional validation info
    validation_request: Optional[ValidationRequestInfo] = None

    class Config:
        from_attributes = True


class VersionDeploymentTaskSummary(BaseModel):
    """Summary schema for task list display."""
    task_id: int
    model_name: str
    version_number: str
    region_code: Optional[str]
    region_name: Optional[str]
    planned_production_date: date
    actual_production_date: Optional[date]
    days_until_due: int
    status: str
    assigned_to_name: str
    deployed_before_validation_approved: bool
    validation_status: Optional[str] = None

    class Config:
        from_attributes = True
