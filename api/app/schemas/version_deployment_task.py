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
    requires_regional_approval: bool = False  # Lock icon indicator

    class Config:
        from_attributes = True


# =============================================================================
# Ready-to-Deploy Schemas (Per-Region Granularity)
# =============================================================================

class VersionSourceEnum(str):
    """How the version was linked to the validation request."""
    EXPLICIT = "explicit"  # User explicitly linked this version
    INFERRED = "inferred"  # System auto-suggested the version


class ReadyToDeployItem(BaseModel):
    """
    Schema for a single (version, region) combination ready for deployment.

    Key design: Returns ONE ROW per (version, region) pair, not aggregated.
    This allows the frontend to show granular deployment status per region.
    """
    # Version identification
    version_id: int
    version_number: str
    model_id: int
    model_name: str

    # Region details (per-region granularity)
    region_id: int
    region_code: str
    region_name: str

    # Version source tracking (explicit vs inferred)
    version_source: str = Field(
        ...,
        description="'explicit' if user linked version to validation, 'inferred' if system auto-suggested"
    )

    # Validation info
    validation_request_id: Optional[int] = None
    validation_status: str
    validation_approved_date: Optional[date] = None

    # Timing
    days_since_approval: int = Field(
        0,
        description="Days since validation was approved (0 if not approved)"
    )

    # Owner info
    owner_id: int
    owner_name: str

    # Deployment task tracking (for this specific region)
    has_pending_task: bool = Field(
        False,
        description="True if a deployment task already exists for this region"
    )
    pending_task_id: Optional[int] = Field(
        None,
        description="ID of pending deployment task for this region, if exists"
    )

    class Config:
        from_attributes = True


class ReadyToDeployResponse(BaseModel):
    """Response schema for ready-to-deploy endpoint with summary stats."""
    items: list[ReadyToDeployItem]

    # Summary statistics
    total_items: int = Field(
        ...,
        description="Total count of (version, region) combinations"
    )
    unique_versions_count: int = Field(
        ...,
        description="Count of unique versions ready to deploy"
    )
    unique_models_count: int = Field(
        ...,
        description="Count of unique models with versions ready to deploy"
    )
    with_pending_tasks_count: int = Field(
        ...,
        description="Count of items that already have deployment tasks scheduled"
    )
