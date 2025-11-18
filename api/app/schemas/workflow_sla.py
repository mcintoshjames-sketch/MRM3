"""Workflow SLA configuration schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class WorkflowSLAUpdate(BaseModel):
    """Schema for updating workflow SLA configuration."""
    assignment_days: int = Field(..., ge=1, le=365, description="Days to assign/claim a validation request")
    begin_work_days: int = Field(..., ge=1, le=365, description="Days to begin work after assignment")
    complete_work_days: int = Field(..., ge=1, le=365, description="Days to complete work after assignment")
    approval_days: int = Field(..., ge=1, le=365, description="Days to approve after requesting approval")


class WorkflowSLAResponse(BaseModel):
    """Response schema for workflow SLA configuration."""
    sla_id: int
    workflow_type: str
    assignment_days: int
    begin_work_days: int
    complete_work_days: int
    approval_days: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
