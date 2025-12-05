"""Workflow SLA configuration schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class WorkflowSLAUpdate(BaseModel):
    """Schema for updating workflow SLA configuration.

    Note: complete_work_days was removed - work completion lead time is now
    calculated per-request based on the model's risk tier policy
    (model_change_lead_time_days in ValidationPolicy).
    """
    assignment_days: int = Field(..., ge=1, le=365, description="Days to assign/claim a validation request")
    begin_work_days: int = Field(..., ge=1, le=365, description="Days to begin work after assignment")
    approval_days: int = Field(..., ge=1, le=365, description="Days to approve after requesting approval")


class WorkflowSLAResponse(BaseModel):
    """Response schema for workflow SLA configuration.

    Note: complete_work_days was removed - work completion lead time is now
    calculated per-request based on the model's risk tier policy
    (model_change_lead_time_days in ValidationPolicy). See applicable_lead_time_days
    on ValidationRequest responses for the computed value.
    """
    sla_id: int
    workflow_type: str
    assignment_days: int
    begin_work_days: int
    approval_days: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
