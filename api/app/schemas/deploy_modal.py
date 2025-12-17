"""Schemas for deploy modal and version deployment operations."""
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class RegionDeploymentStatus(BaseModel):
    """Status of a version's deployment to a specific region."""
    region_id: int
    region_code: str
    region_name: str
    current_version_id: Optional[int] = None
    current_version_number: Optional[str] = None
    deployed_at: Optional[datetime] = None
    # Computed: region.requires_regional_approval AND region NOT in validation scope
    requires_regional_approval: bool
    in_validation_scope: bool
    has_pending_task: bool = False
    pending_task_id: Optional[int] = None
    pending_task_planned_date: Optional[date] = None


class DeployModalDataResponse(BaseModel):
    """Response data for deploy modal initialization."""
    version_id: int
    version_number: str
    change_description: Optional[str] = None
    model_id: int
    model_name: str
    validation_request_id: Optional[int] = None
    validation_status: Optional[str] = None
    validation_approved: bool = False
    regions: List[RegionDeploymentStatus]
    can_deploy: bool = True

    model_config = {"from_attributes": True}


class RegionDeploymentSpec(BaseModel):
    """Specification for deploying to a single region."""
    region_id: int
    production_date: date
    notes: Optional[str] = None


class DeploymentCreateRequest(BaseModel):
    """Request to create deployment task(s) for a version."""
    deployments: List[RegionDeploymentSpec] = Field(
        ..., min_length=1, description="At least one region deployment required"
    )
    deploy_now: bool = Field(
        default=False,
        description="If true, creates CONFIRMED tasks; if false, creates PENDING tasks"
    )
    validation_override_reason: Optional[str] = Field(
        default=None,
        description="Required if validation not approved and deploying anyway"
    )
    shared_notes: Optional[str] = Field(
        default=None,
        description="Notes applied to all deployments"
    )


class DeploymentCreateResponse(BaseModel):
    """Response after creating deployment tasks."""
    created_tasks: List[int] = Field(
        description="List of created task IDs"
    )
    regions_requiring_approval: List[str] = Field(
        default_factory=list,
        description="Region codes that will require regional approval"
    )
    message: str


class BulkTaskIds(BaseModel):
    """Request body containing multiple task IDs for bulk operations."""
    task_ids: List[int] = Field(
        ..., min_length=1, description="At least one task ID required"
    )


class BulkConfirmRequest(BaseModel):
    """Request to confirm multiple deployment tasks."""
    task_ids: List[int] = Field(
        ..., min_length=1, description="Task IDs to confirm"
    )
    actual_production_date: date
    confirmation_notes: Optional[str] = None
    validation_override_reason: Optional[str] = Field(
        default=None,
        description="Required if any task's validation is not approved"
    )


class BulkAdjustRequest(BaseModel):
    """Request to adjust dates for multiple deployment tasks."""
    task_ids: List[int] = Field(
        ..., min_length=1, description="Task IDs to adjust"
    )
    new_planned_date: date
    adjustment_reason: Optional[str] = None


class BulkCancelRequest(BaseModel):
    """Request to cancel multiple deployment tasks."""
    task_ids: List[int] = Field(
        ..., min_length=1, description="Task IDs to cancel"
    )
    cancellation_reason: Optional[str] = None


class BulkOperationResult(BaseModel):
    """Result of a bulk operation."""
    succeeded: List[int] = Field(
        description="Task IDs that were successfully processed"
    )
    failed: List[dict] = Field(
        default_factory=list,
        description="List of {task_id, error} for failed operations"
    )
    message: str
