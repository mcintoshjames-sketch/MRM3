"""API endpoints for version deployment tasks."""
from datetime import date, datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.version_deployment_task import VersionDeploymentTask
from app.models.model_version import ModelVersion
from app.models.model import Model
from app.models.model_delegate import ModelDelegate
from app.models.validation import ValidationRequest
from app.models.model_region import ModelRegion
from app.models.taxonomy import TaxonomyValue
from app.schemas.version_deployment_task import (
    VersionDeploymentTaskResponse,
    VersionDeploymentTaskSummary,
    VersionDeploymentTaskConfirm,
    VersionDeploymentTaskAdjust,
    VersionDeploymentTaskCancel,
    ModelInfo,
    VersionInfo,
    RegionInfo,
    UserInfo,
    ValidationRequestInfo
)

router = APIRouter()


def can_manage_task(task: VersionDeploymentTask, user: User, db: Session) -> bool:
    """
    Check if user can manage this deployment task.

    Returns True if:
    - User is the assigned model owner, OR
    - User is an active delegate for the model
    """
    # Check if assigned to this user
    if task.assigned_to_id == user.user_id:
        return True

    # Check if user is an active delegate
    delegate = db.query(ModelDelegate).filter(
        ModelDelegate.model_id == task.model_id,
        ModelDelegate.user_id == user.user_id,
        ModelDelegate.revoked_at == None
    ).first()

    return delegate is not None


def ensure_task_model_alignment(task: VersionDeploymentTask):
    """Ensure task.model_id matches the version's model_id to prevent silent drift."""
    if task.version and task.model_id != task.version.model_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Deployment task model_id does not match the associated version's model."
        )


@router.get("/my-tasks", response_model=List[VersionDeploymentTaskSummary])
def get_my_deployment_tasks(
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get deployment tasks for current user.

    For Admin users: Shows all deployment tasks (system-wide oversight)
    For non-Admin users: Shows tasks where user is:
    - Assigned model owner, OR
    - Active delegate for the model
    """
    # Base query with eager loading
    query = db.query(VersionDeploymentTask).options(
        joinedload(VersionDeploymentTask.model),
        joinedload(VersionDeploymentTask.version),
        joinedload(VersionDeploymentTask.region),
        joinedload(VersionDeploymentTask.assigned_to)
    )

    # Admin users see all tasks; non-admin users see only their assigned tasks
    if current_user.role != 'Admin':
        # Filter to tasks user can access
        # Get all models where user is delegate
        delegate_model_ids = db.query(ModelDelegate.model_id).filter(
            ModelDelegate.user_id == current_user.user_id,
            ModelDelegate.revoked_at == None
        ).subquery()

        query = query.filter(
            or_(
                VersionDeploymentTask.assigned_to_id == current_user.user_id,
                VersionDeploymentTask.model_id.in_(delegate_model_ids)
            )
        )

    # Optional status filter
    if status:
        query = query.filter(VersionDeploymentTask.status == status)

    # Order by due date
    query = query.order_by(VersionDeploymentTask.planned_production_date)

    tasks = query.all()

    # Build response with summary info
    result = []
    today = date.today()

    for task in tasks:
        ensure_task_model_alignment(task)
        # Calculate days until due
        days_until_due = (task.planned_production_date - today).days

        # Get validation status if exists
        validation_status = None
        if task.version.validation_request_id:
            val_request = db.query(ValidationRequest).get(task.version.validation_request_id)
            if val_request:
                status_value = db.query(TaxonomyValue).get(val_request.current_status_id)
                validation_status = status_value.label if status_value else None

        result.append(VersionDeploymentTaskSummary(
            task_id=task.task_id,
            model_name=task.model.model_name,
            version_number=task.version.version_number,
            region_code=task.region.code if task.region else None,
            region_name=task.region.name if task.region else None,
            planned_production_date=task.planned_production_date,
            actual_production_date=task.actual_production_date,
            days_until_due=days_until_due,
            status=task.status,
            assigned_to_name=task.assigned_to.full_name,
            deployed_before_validation_approved=task.deployed_before_validation_approved,
            validation_status=validation_status
        ))

    return result


@router.get("/{task_id}", response_model=VersionDeploymentTaskResponse)
def get_deployment_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed deployment task information."""
    task = db.query(VersionDeploymentTask).options(
        joinedload(VersionDeploymentTask.model),
        joinedload(VersionDeploymentTask.version),
        joinedload(VersionDeploymentTask.region),
        joinedload(VersionDeploymentTask.assigned_to),
        joinedload(VersionDeploymentTask.confirmed_by)
    ).filter(VersionDeploymentTask.task_id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment task not found"
        )

    # Check access
    if not can_manage_task(task, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this deployment task"
        )

    ensure_task_model_alignment(task)

    # Get validation info if exists
    validation_request = None
    if task.version.validation_request_id:
        val_request = db.query(ValidationRequest).get(task.version.validation_request_id)
        if val_request:
            status_value = db.query(TaxonomyValue).get(val_request.current_status_id)
            validation_request = ValidationRequestInfo(
                request_id=val_request.request_id,
                current_status=status_value.label if status_value else "Unknown",
                target_completion_date=val_request.target_completion_date
            )

    # Build response
    return VersionDeploymentTaskResponse(
        task_id=task.task_id,
        version_id=task.version_id,
        model_id=task.model_id,
        region_id=task.region_id,
        planned_production_date=task.planned_production_date,
        actual_production_date=task.actual_production_date,
        assigned_to_id=task.assigned_to_id,
        status=task.status,
        confirmation_notes=task.confirmation_notes,
        confirmed_at=task.confirmed_at,
        confirmed_by_id=task.confirmed_by_id,
        deployed_before_validation_approved=task.deployed_before_validation_approved,
        validation_override_reason=task.validation_override_reason,
        created_at=task.created_at,
        model=ModelInfo(
            model_id=task.model.model_id,
            model_name=task.model.model_name
        ),
        version=VersionInfo(
            version_id=task.version.version_id,
            version_number=task.version.version_number,
            change_description=task.version.change_description
        ),
        region=RegionInfo(
            region_id=task.region.region_id,
            code=task.region.code,
            name=task.region.name
        ) if task.region else None,
        assigned_to=UserInfo(
            user_id=task.assigned_to.user_id,
            full_name=task.assigned_to.full_name,
            email=task.assigned_to.email
        ),
        confirmed_by=UserInfo(
            user_id=task.confirmed_by.user_id,
            full_name=task.confirmed_by.full_name,
            email=task.confirmed_by.email
        ) if task.confirmed_by else None,
        validation_request=validation_request
    )


@router.patch("/{task_id}/confirm", response_model=VersionDeploymentTaskResponse)
def confirm_deployment(
    task_id: int,
    confirmation_data: VersionDeploymentTaskConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Confirm deployment of a version.

    Validates that:
    - Task is in PENDING status
    - User has permission to confirm
    - If validation exists and not approved, requires override reason

    Updates model_regions table with deployment info.
    """
    task = db.query(VersionDeploymentTask).filter(
        VersionDeploymentTask.task_id == task_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment task not found"
        )

    # Check access
    if not can_manage_task(task, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to confirm this deployment"
        )

    # Check status
    if task.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot confirm task with status '{task.status}'"
        )

    # Check validation status
    deployed_before_validation = False
    validation_override_reason = None

    version = db.query(ModelVersion).get(task.version_id)
    if version and version.validation_request_id:
        val_request = db.query(ValidationRequest).get(version.validation_request_id)
        if val_request:
            status_value = db.query(TaxonomyValue).get(val_request.current_status_id)

            # Check if validation is approved
            if status_value and status_value.code != "APPROVED":
                # Validation not approved - require override justification
                if not confirmation_data.validation_override_reason:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "error": "validation_not_approved",
                            "message": f"Validation status is '{status_value.label}', not 'Approved'",
                            "validation_request_id": val_request.request_id,
                            "current_status": status_value.label,
                            "requires_override": True
                        }
                    )

                deployed_before_validation = True
                validation_override_reason = confirmation_data.validation_override_reason

    # Update task
    task.status = "CONFIRMED"
    task.actual_production_date = confirmation_data.actual_production_date
    task.confirmation_notes = confirmation_data.confirmation_notes
    task.deployed_before_validation_approved = deployed_before_validation
    task.validation_override_reason = validation_override_reason
    task.confirmed_at = datetime.utcnow()
    task.confirmed_by_id = current_user.user_id

    # Update version's actual_production_date
    if version:
        version.actual_production_date = confirmation_data.actual_production_date

    # Update model_regions table
    if task.region_id:
        # Regional deployment
        model_region = db.query(ModelRegion).filter(
            ModelRegion.model_id == task.model_id,
            ModelRegion.region_id == task.region_id
        ).first()

        if model_region:
            model_region.version_id = task.version_id
            model_region.deployed_at = datetime.utcnow()
            if confirmation_data.confirmation_notes:
                model_region.deployment_notes = confirmation_data.confirmation_notes
    else:
        # Global deployment - update all regions
        model_regions = db.query(ModelRegion).filter(
            ModelRegion.model_id == task.model_id
        ).all()

        for mr in model_regions:
            mr.version_id = task.version_id
            mr.deployed_at = datetime.utcnow()

    db.commit()
    db.refresh(task)

    # Return updated task
    return get_deployment_task(task_id, db, current_user)


@router.patch("/{task_id}/adjust", response_model=VersionDeploymentTaskResponse)
def adjust_deployment_date(
    task_id: int,
    adjustment_data: VersionDeploymentTaskAdjust,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Adjust the planned production date for a deployment.

    Only allowed for PENDING tasks.
    """
    task = db.query(VersionDeploymentTask).filter(
        VersionDeploymentTask.task_id == task_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment task not found"
        )

    # Check access
    if not can_manage_task(task, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to adjust this deployment"
        )

    # Check status
    if task.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot adjust task with status '{task.status}'"
        )

    # Update date
    task.planned_production_date = adjustment_data.planned_production_date
    task.confirmation_notes = adjustment_data.adjustment_reason
    task.status = "ADJUSTED"

    db.commit()
    db.refresh(task)

    return get_deployment_task(task_id, db, current_user)


@router.patch("/{task_id}/cancel", response_model=VersionDeploymentTaskResponse)
def cancel_deployment(
    task_id: int,
    cancellation_data: VersionDeploymentTaskCancel,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a deployment task.

    Only allowed for PENDING or ADJUSTED tasks.
    """
    task = db.query(VersionDeploymentTask).filter(
        VersionDeploymentTask.task_id == task_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment task not found"
        )

    # Check access
    if not can_manage_task(task, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this deployment"
        )

    # Check status
    if task.status not in ["PENDING", "ADJUSTED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel task with status '{task.status}'"
        )

    # Update status
    task.status = "CANCELLED"
    task.confirmation_notes = cancellation_data.cancellation_reason

    db.commit()
    db.refresh(task)

    return get_deployment_task(task_id, db, current_user)
