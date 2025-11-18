"""Workflow SLA configuration routes."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.validation import ValidationWorkflowSLA
from app.schemas.workflow_sla import WorkflowSLAResponse, WorkflowSLAUpdate

router = APIRouter()


@router.get("/validation", response_model=WorkflowSLAResponse)
def get_validation_sla(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get validation workflow SLA configuration."""
    sla = db.query(ValidationWorkflowSLA).filter(
        ValidationWorkflowSLA.workflow_type == "Validation"
    ).first()

    if not sla:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation workflow SLA configuration not found"
        )

    return sla


@router.patch("/validation", response_model=WorkflowSLAResponse)
def update_validation_sla(
    sla_data: WorkflowSLAUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update validation workflow SLA configuration (Admin only)."""
    # Check if user is admin
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update workflow SLA configuration"
        )

    sla = db.query(ValidationWorkflowSLA).filter(
        ValidationWorkflowSLA.workflow_type == "Validation"
    ).first()

    if not sla:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation workflow SLA configuration not found"
        )

    # Update fields
    sla.assignment_days = sla_data.assignment_days
    sla.begin_work_days = sla_data.begin_work_days
    sla.complete_work_days = sla_data.complete_work_days
    sla.approval_days = sla_data.approval_days
    sla.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(sla)

    return sla
