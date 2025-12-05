"""Workflow SLA configuration routes."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.time import utc_now
from app.core.deps import get_current_user
from app.models.user import User
from app.models.validation import ValidationWorkflowSLA
from app.models.audit_log import AuditLog
from app.schemas.workflow_sla import WorkflowSLAResponse, WorkflowSLAUpdate

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry for workflow SLA configuration changes."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


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

    # Track changes for audit log
    changes = {}

    if sla_data.assignment_days != sla.assignment_days:
        # CRITICAL: Assignment SLA changes affect when violations are triggered
        changes["assignment_days"] = {
            "old": sla.assignment_days,
            "new": sla_data.assignment_days
        }
        sla.assignment_days = sla_data.assignment_days

    if sla_data.begin_work_days != sla.begin_work_days:
        # CRITICAL: Begin work SLA changes affect when violations are triggered
        changes["begin_work_days"] = {
            "old": sla.begin_work_days,
            "new": sla_data.begin_work_days
        }
        sla.begin_work_days = sla_data.begin_work_days

    # NOTE: complete_work_days was removed - work completion lead time is now
    # calculated per-request based on the model's risk tier policy

    if sla_data.approval_days != sla.approval_days:
        # CRITICAL: Approval SLA changes affect when violations are triggered
        changes["approval_days"] = {
            "old": sla.approval_days,
            "new": sla_data.approval_days
        }
        sla.approval_days = sla_data.approval_days

    sla.updated_at = utc_now()

    # Create audit log if changes were made
    if changes:
        create_audit_log(
            db=db,
            entity_type="ValidationWorkflowSLA",
            entity_id=sla.sla_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(sla)

    return sla
