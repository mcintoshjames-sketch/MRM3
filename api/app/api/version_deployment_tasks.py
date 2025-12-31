"""API endpoints for version deployment tasks."""
from datetime import date, datetime
from typing import List, Set
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from app.core.database import get_db
from app.core.time import utc_now
from app.core.deps import get_current_user
from app.core.roles import is_admin
from app.core.exception_detection import detect_type3_for_deployment_task
from app.models.user import User
from app.core.roles import is_admin
from app.models.version_deployment_task import VersionDeploymentTask
from app.models.model_version import ModelVersion
from app.models.model import Model
from app.models.model_delegate import ModelDelegate
from app.models.validation import ValidationRequest, ValidationApproval
from app.models.model_region import ModelRegion
from app.models.region import Region
from app.models.taxonomy import TaxonomyValue
from app.models.audit_log import AuditLog
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
    ValidationRequestInfo,
    ReadyToDeployItem,
    ReadyToDeployResponse,
    VersionSourceEnum
)
from app.schemas.deploy_modal import (
    DeployModalDataResponse,
    RegionDeploymentStatus,
    DeploymentCreateRequest,
    DeploymentCreateResponse,
    BulkConfirmRequest,
    BulkAdjustRequest,
    BulkCancelRequest,
    BulkOperationResult
)

router = APIRouter()


def can_manage_task(task: VersionDeploymentTask, user: User, db: Session) -> bool:
    """
    Check if user can manage this deployment task.

    Returns True if:
    - User is an Admin, OR
    - User is the assigned model owner, OR
    - User is an active delegate for the model
    """
    # Admins can manage any task
    if is_admin(user):
        return True

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
    if not is_admin(current_user):
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

        # Get validation status and scope regions if exists
        validation_status = None
        validation_region_ids: Set[int] = set()
        if task.version.validation_request_id:
            val_request = db.query(ValidationRequest).options(
                joinedload(ValidationRequest.regions)
            ).get(task.version.validation_request_id)
            if val_request:
                status_value = db.query(TaxonomyValue).get(val_request.current_status_id)
                validation_status = status_value.label if status_value else None
                # Get validation scope region IDs
                validation_region_ids = {r.region_id for r in val_request.regions}

        # Compute requires_regional_approval (lock icon logic):
        # True when region has the flag AND region is NOT in validation scope
        requires_regional_approval = False
        if task.region and task.region.requires_regional_approval:
            requires_regional_approval = task.region_id not in validation_region_ids

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
            validation_status=validation_status,
            requires_regional_approval=requires_regional_approval
        ))

    return result


@router.get("/ready-to-deploy", response_model=list[ReadyToDeployItem])
def get_ready_to_deploy(
    model_id: int = None,
    my_models_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get versions ready to deploy with per-region granularity.

    Returns one row per (version, region) combination where:
    - Version has an APPROVED validation
    - Region does not have a CONFIRMED deployment task for this version

    Each row includes:
    - Version and model info
    - Region details (region_id, code, name)
    - version_source: "explicit" (user linked) or "inferred" (system auto-suggested)
    - Validation info and approval date
    - Pending deployment task info for this specific region

    Filters:
    - model_id: Filter to specific model
    - my_models_only: Filter to models owned by or delegated to current user

    Access Control:
    - Admin: Sees all ready-to-deploy items
    - Non-admin: Only sees items for models they own or are delegated for
    """
    # Get the APPROVED status taxonomy value
    approved_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.code == "APPROVED"
    ).first()

    if not approved_status:
        # No approved status configured - return empty list
        return []

    # Build base query for versions with APPROVED validation
    query = db.query(ModelVersion).options(
        joinedload(ModelVersion.model),
        joinedload(ModelVersion.validation_request)
    ).join(
        ValidationRequest,
        ModelVersion.validation_request_id == ValidationRequest.request_id
    ).filter(
        ValidationRequest.current_status_id == approved_status.value_id
    )

    # Get models user can access for filtering
    accessible_model_ids = None
    if not is_admin(current_user) or my_models_only:
        # Non-admin: Only owned + delegated models
        # my_models_only: Same filter for admins who want to see only their models
        owned_model_ids = db.query(Model.model_id).filter(
            Model.owner_id == current_user.user_id
        ).subquery()

        delegate_model_ids = db.query(ModelDelegate.model_id).filter(
            ModelDelegate.user_id == current_user.user_id,
            ModelDelegate.revoked_at == None
        ).subquery()

        accessible_model_ids = db.query(Model.model_id).filter(
            or_(
                Model.model_id.in_(owned_model_ids),
                Model.model_id.in_(delegate_model_ids)
            )
        ).subquery()

        query = query.filter(ModelVersion.model_id.in_(accessible_model_ids))

    # Filter by specific model_id if provided
    if model_id:
        query = query.filter(ModelVersion.model_id == model_id)

    # Execute query to get versions
    versions = query.all()

    # For each version, get model regions and check deployment status
    items = []
    unique_versions = set()
    unique_models = set()
    pending_tasks_count = 0
    today = date.today()

    for version in versions:
        model = version.model
        val_request = version.validation_request

        # Get model regions
        model_regions = db.query(ModelRegion).options(
            joinedload(ModelRegion.region)
        ).filter(
            ModelRegion.model_id == model.model_id
        ).all()

        # Get CONFIRMED deployment tasks for this version (to exclude those regions)
        confirmed_region_ids = set(
            db.query(VersionDeploymentTask.region_id).filter(
                VersionDeploymentTask.version_id == version.version_id,
                VersionDeploymentTask.status == "CONFIRMED"
            ).all()
        )
        confirmed_region_ids = {r[0] for r in confirmed_region_ids if r[0] is not None}

        # Get PENDING/ADJUSTED deployment tasks for this version (to show pending info)
        pending_tasks = db.query(VersionDeploymentTask).filter(
            VersionDeploymentTask.version_id == version.version_id,
            VersionDeploymentTask.status.in_(["PENDING", "ADJUSTED"])
        ).all()
        pending_tasks_by_region = {t.region_id: t for t in pending_tasks}

        # Get version source from validation request (default to "explicit")
        version_source = val_request.version_source if val_request.version_source else "explicit"

        # Get owner info
        owner = db.query(User).get(model.owner_id)
        owner_name = owner.full_name if owner else "Unknown"

        # Calculate days since approval
        days_since_approval = 0
        validation_approved_date = None
        if val_request.completion_date:
            validation_approved_date = val_request.completion_date
            days_since_approval = (today - val_request.completion_date).days

        # Get validation status label
        status_value = db.query(TaxonomyValue).get(val_request.current_status_id)
        validation_status = status_value.label if status_value else "Unknown"

        # Create a row for each region that is NOT fully deployed
        for mr in model_regions:
            region = mr.region
            if region.region_id in confirmed_region_ids:
                # This region already has a CONFIRMED deployment - skip
                continue

            # Check for pending task in this region
            pending_task = pending_tasks_by_region.get(region.region_id)
            has_pending_task = pending_task is not None
            pending_task_id = pending_task.task_id if pending_task else None

            if has_pending_task:
                pending_tasks_count += 1

            unique_versions.add(version.version_id)
            unique_models.add(model.model_id)

            items.append(ReadyToDeployItem(
                version_id=version.version_id,
                version_number=version.version_number,
                model_id=model.model_id,
                model_name=model.model_name,
                region_id=region.region_id,
                region_code=region.code,
                region_name=region.name,
                version_source=version_source,
                validation_request_id=val_request.request_id,
                validation_status=validation_status,
                validation_approved_date=validation_approved_date,
                days_since_approval=days_since_approval,
                owner_id=model.owner_id,
                owner_name=owner_name,
                has_pending_task=has_pending_task,
                pending_task_id=pending_task_id
            ))

    # Sort by days_since_approval descending (oldest first)
    items.sort(key=lambda x: x.days_since_approval, reverse=True)

    return items


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
    task.confirmed_at = utc_now()
    task.confirmed_by_id = current_user.user_id

    # Update model_regions table
    if task.region_id:
        # Regional deployment
        model_region = db.query(ModelRegion).filter(
            ModelRegion.model_id == task.model_id,
            ModelRegion.region_id == task.region_id
        ).first()

        if model_region:
            model_region.version_id = task.version_id
            # Issue 1 fix: Use user-provided date, not server timestamp
            model_region.deployed_at = datetime.combine(
                confirmation_data.actual_production_date, datetime.min.time()
            )
            if confirmation_data.confirmation_notes:
                model_region.deployment_notes = confirmation_data.confirmation_notes
    else:
        # Global deployment - update all regions
        model_regions = db.query(ModelRegion).filter(
            ModelRegion.model_id == task.model_id
        ).all()

        for mr in model_regions:
            mr.version_id = task.version_id
            # Issue 1 fix: Use user-provided date, not server timestamp
            mr.deployed_at = datetime.combine(
                confirmation_data.actual_production_date, datetime.min.time()
            )

    # Issue 2 fix: Only update version.actual_production_date when ALL regions deployed
    if version:
        check_and_update_version_production_date(db, version)

    # Auto-create regional approval if required (lock icon region)
    if version and version.validation_request_id and task.region_id:
        create_regional_approval_if_required(db, task, version.validation_request_id)

    # Issue 3 fix: Add audit logging
    db.add(AuditLog(
        entity_type="VersionDeploymentTask",
        entity_id=task.task_id,
        action="DEPLOYMENT_CONFIRMED",
        user_id=current_user.user_id,
        changes={
            "status": task.status,
            "actual_production_date": str(task.actual_production_date),
            "region_id": task.region_id,
            "version_id": task.version_id,
            "model_id": task.model_id,
            "deployed_before_validation_approved": task.deployed_before_validation_approved
        }
    ))

    db.commit()
    db.refresh(task)

    # Detect Type 3 exception if deployed before validation was approved
    if task.deployed_before_validation_approved:
        detect_type3_for_deployment_task(db, task)
        db.commit()  # Persist Type 3 exception

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


def compute_requires_regional_approval(
    region: Region,
    validation_region_ids: Set[int]
) -> bool:
    """
    Compute if regional approval is required for a deployment.

    Lock icon 🔒 shows when:
    - Region has requires_regional_approval = True, AND
    - Region is NOT in the validation request's scope
    """
    if not region.requires_regional_approval:
        return False
    return region.region_id not in validation_region_ids


def create_regional_approval_if_required(
    db: Session,
    task: VersionDeploymentTask,
    validation_request_id: int
) -> bool:
    """
    Create a regional approval record if the deployment region requires approval.

    This is called when a deployment task is confirmed. If the region requires
    regional approval (lock icon 🔒 logic), a pending ValidationApproval is created.

    Returns True if an approval was created, False otherwise.
    """
    if not task.region_id:
        return False  # Global deployment doesn't create regional approvals

    # Get the region
    region = db.query(Region).get(task.region_id)
    if not region:
        return False

    # Get validation request to check scope
    val_request = db.query(ValidationRequest).get(validation_request_id)
    if not val_request:
        return False

    # Get validation scope region IDs
    validation_region_ids: Set[int] = set()
    if val_request.regions:
        validation_region_ids = {r.region_id for r in val_request.regions}

    # Check if regional approval is required
    if not compute_requires_regional_approval(region, validation_region_ids):
        return False

    # Check if approval already exists for this region/request
    existing_approval = db.query(ValidationApproval).filter(
        ValidationApproval.request_id == validation_request_id,
        ValidationApproval.approval_type == "Regional",
        ValidationApproval.region_id == task.region_id
    ).first()

    if existing_approval:
        return False  # Don't create duplicate

    # Create regional approval
    regional_approval = ValidationApproval(
        request_id=validation_request_id,
        approver_role=f"Regional Approver - {region.code}",
        approval_type="Regional",
        region_id=task.region_id,
        is_required=True,
        approval_status="Pending"
    )
    db.add(regional_approval)
    return True


def check_and_update_version_production_date(db: Session, version: ModelVersion):
    """
    Only update version.actual_production_date when ALL model regions are deployed.

    This ensures the version production date reflects the final deployment across all regions,
    not just the first region to be deployed.
    """
    # Get all regions the model is deployed to
    model_regions = db.query(ModelRegion).filter(
        ModelRegion.model_id == version.model_id
    ).all()

    if not model_regions:
        return

    # Check if all have deployed_at set
    if all(mr.deployed_at is not None for mr in model_regions):
        # Use max deployed_at date
        version.actual_production_date = max(mr.deployed_at for mr in model_regions).date()


def can_deploy_version(version: ModelVersion, model: Model, user: User, db: Session) -> bool:
    """
    Check if user can deploy this version.

    Returns True if:
    - User is model owner, OR
    - User is an active delegate for the model, OR
    - User is Admin
    """
    if is_admin(user):
        return True

    if model.owner_id == user.user_id:
        return True

    # Check if user is an active delegate
    delegate = db.query(ModelDelegate).filter(
        ModelDelegate.model_id == model.model_id,
        ModelDelegate.user_id == user.user_id,
        ModelDelegate.revoked_at == None
    ).first()

    return delegate is not None


@router.get("/version/{version_id}/deploy-modal", response_model=DeployModalDataResponse)
def get_deploy_modal_data(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get data for the deploy modal.

    Returns version info, model info, validation status, and regional deployment status
    with lock icon computation (requires_regional_approval).

    Lock icon 🔒 appears when:
    - region.requires_regional_approval = True, AND
    - region.region_id NOT IN validation_request.regions
    """
    # Get version with model
    version = db.query(ModelVersion).options(
        joinedload(ModelVersion.model)
    ).filter(ModelVersion.version_id == version_id).first()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    model = version.model

    # Check permission
    if not can_deploy_version(version, model, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to deploy this version"
        )

    # Get validation status and regions in scope
    validation_region_ids: Set[int] = set()
    validation_status = None
    validation_approved = False
    validation_request_id = None

    if version.validation_request_id:
        val_request = db.query(ValidationRequest).options(
            joinedload(ValidationRequest.regions)
        ).filter(ValidationRequest.request_id == version.validation_request_id).first()

        if val_request:
            validation_request_id = val_request.request_id
            status_value = db.query(TaxonomyValue).get(val_request.current_status_id)
            if status_value:
                validation_status = status_value.label
                validation_approved = status_value.code == "APPROVED"

            # Get regions in validation scope
            validation_region_ids = {r.region_id for r in val_request.regions}

    # Get all model regions (where model is deployed)
    model_regions = db.query(ModelRegion).options(
        joinedload(ModelRegion.region),
        joinedload(ModelRegion.version)
    ).filter(ModelRegion.model_id == model.model_id).all()

    # Get pending/adjusted deployment tasks for this version
    pending_tasks = db.query(VersionDeploymentTask).filter(
        VersionDeploymentTask.version_id == version_id,
        VersionDeploymentTask.status.in_(["PENDING", "ADJUSTED"])
    ).all()

    pending_tasks_by_region = {t.region_id: t for t in pending_tasks}

    # Build region deployment status
    regions: List[RegionDeploymentStatus] = []

    for mr in model_regions:
        region = mr.region
        pending_task = pending_tasks_by_region.get(region.region_id)

        # Compute lock icon logic
        requires_approval = compute_requires_regional_approval(region, validation_region_ids)

        regions.append(RegionDeploymentStatus(
            region_id=region.region_id,
            region_code=region.code,
            region_name=region.name,
            current_version_id=mr.version_id,
            current_version_number=mr.version.version_number if mr.version else None,
            deployed_at=mr.deployed_at,
            requires_regional_approval=requires_approval,
            in_validation_scope=region.region_id in validation_region_ids,
            has_pending_task=pending_task is not None,
            pending_task_id=pending_task.task_id if pending_task else None,
            pending_task_planned_date=pending_task.planned_production_date if pending_task else None
        ))

    # Sort regions by code for consistent display
    regions.sort(key=lambda r: r.region_code)

    return DeployModalDataResponse(
        version_id=version.version_id,
        version_number=version.version_number,
        change_description=version.change_description,
        model_id=model.model_id,
        model_name=model.model_name,
        validation_request_id=validation_request_id,
        validation_status=validation_status,
        validation_approved=validation_approved,
        regions=regions,
        can_deploy=True
    )


@router.post("/version/{version_id}/deploy", response_model=DeploymentCreateResponse)
def deploy_version(
    version_id: int,
    deploy_request: DeploymentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create deployment task(s) for a version.

    If deploy_now=True: Creates CONFIRMED tasks and updates ModelRegion immediately.
    If deploy_now=False: Creates PENDING tasks for later confirmation.

    Validates:
    - User has permission to deploy
    - If validation not approved and deploy_now=True, requires validation_override_reason
    - Regions are valid for the model
    """
    # Get version with model
    version = db.query(ModelVersion).options(
        joinedload(ModelVersion.model)
    ).filter(ModelVersion.version_id == version_id).first()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    model = version.model

    # Check permission
    if not can_deploy_version(version, model, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to deploy this version"
        )

    # Check validation status
    validation_approved = False
    validation_region_ids: Set[int] = set()

    if version.validation_request_id:
        val_request = db.query(ValidationRequest).options(
            joinedload(ValidationRequest.regions)
        ).filter(ValidationRequest.request_id == version.validation_request_id).first()

        if val_request:
            status_value = db.query(TaxonomyValue).get(val_request.current_status_id)
            validation_approved = status_value and status_value.code == "APPROVED"
            validation_region_ids = {r.region_id for r in val_request.regions}

    # If deploy now and validation exists but not approved, require override reason
    # Note: MINOR changes don't create validation requests, so they can deploy without override
    deployed_before_validation = False
    if deploy_request.deploy_now and version.validation_request_id and not validation_approved:
        if not deploy_request.validation_override_reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "validation_not_approved",
                    "message": "Validation is not approved. Provide validation_override_reason to deploy anyway.",
                    "requires_override": True
                }
            )
        deployed_before_validation = True

    # Validate regions exist for this model
    model_region_ids = {mr.region_id for mr in db.query(ModelRegion).filter(
        ModelRegion.model_id == model.model_id
    ).all()}

    requested_region_ids = {d.region_id for d in deploy_request.deployments}
    invalid_regions = requested_region_ids - model_region_ids

    if invalid_regions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid region IDs for this model: {invalid_regions}"
        )

    # Get regions requiring approval
    regions_requiring_approval = []
    for deployment in deploy_request.deployments:
        region = db.query(Region).get(deployment.region_id)
        if region and compute_requires_regional_approval(region, validation_region_ids):
            regions_requiring_approval.append(region.code)

    # Create deployment tasks
    created_task_ids = []
    now = utc_now()

    for deployment in deploy_request.deployments:
        # Combine notes
        notes = deployment.notes or deploy_request.shared_notes

        # Determine status based on deploy_now
        task_status = "CONFIRMED" if deploy_request.deploy_now else "PENDING"

        task = VersionDeploymentTask(
            version_id=version_id,
            model_id=model.model_id,
            region_id=deployment.region_id,
            planned_production_date=deployment.production_date,
            actual_production_date=deployment.production_date if deploy_request.deploy_now else None,
            assigned_to_id=model.owner_id,
            status=task_status,
            confirmation_notes=notes,
            deployed_before_validation_approved=deployed_before_validation if deploy_request.deploy_now else False,
            validation_override_reason=deploy_request.validation_override_reason if deploy_request.deploy_now else None,
            confirmed_at=now if deploy_request.deploy_now else None,
            confirmed_by_id=current_user.user_id if deploy_request.deploy_now else None,
            created_at=now
        )

        db.add(task)
        db.flush()  # Get task_id
        created_task_ids.append(task.task_id)

        # Issue 3 fix: Add audit logging for task creation
        db.add(AuditLog(
            entity_type="VersionDeploymentTask",
            entity_id=task.task_id,
            action="DEPLOYMENT_CREATED",
            user_id=current_user.user_id,
            changes={
                "status": task.status,
                "planned_production_date": str(task.planned_production_date),
                "region_id": task.region_id,
                "version_id": task.version_id,
                "model_id": task.model_id,
                "deploy_now": deploy_request.deploy_now
            }
        ))

        # If deploy_now, also update ModelRegion
        if deploy_request.deploy_now:
            model_region = db.query(ModelRegion).filter(
                ModelRegion.model_id == model.model_id,
                ModelRegion.region_id == deployment.region_id
            ).first()

            if model_region:
                model_region.version_id = version_id
                # Issue 1 fix: Use user-provided date, not server timestamp
                model_region.deployed_at = datetime.combine(
                    deployment.production_date, datetime.min.time()
                )
                if notes:
                    model_region.deployment_notes = notes

            # Issue 2 fix: Only update version.actual_production_date when ALL regions deployed
            check_and_update_version_production_date(db, version)

            # Detect Type 3 exception if deployed before validation was approved
            if deployed_before_validation:
                detect_type3_for_deployment_task(db, task)

            # Auto-create regional approval if required (lock icon region)
            if version.validation_request_id and deployment.region_id:
                create_regional_approval_if_required(db, task, version.validation_request_id)

            # Issue 3 fix: Add audit logging for immediate confirmation
            db.add(AuditLog(
                entity_type="VersionDeploymentTask",
                entity_id=task.task_id,
                action="DEPLOYMENT_CONFIRMED",
                user_id=current_user.user_id,
                changes={
                    "status": task.status,
                    "actual_production_date": str(task.actual_production_date),
                    "region_id": task.region_id,
                    "version_id": task.version_id,
                    "model_id": task.model_id,
                    "deployed_before_validation_approved": task.deployed_before_validation_approved
                }
            ))

    db.commit()

    # Build response message
    if deploy_request.deploy_now:
        message = f"Deployed version {version.version_number} to {len(created_task_ids)} region(s)"
    else:
        message = f"Scheduled deployment of version {version.version_number} to {len(created_task_ids)} region(s)"

    if regions_requiring_approval:
        message += f". Regional approval will be required for: {', '.join(regions_requiring_approval)}"

    return DeploymentCreateResponse(
        created_tasks=created_task_ids,
        regions_requiring_approval=regions_requiring_approval,
        message=message
    )


@router.post("/bulk/confirm", response_model=BulkOperationResult)
def bulk_confirm_deployments(
    request: BulkConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Confirm multiple deployment tasks at once.

    Validates each task and confirms those where user has permission.
    Returns list of succeeded and failed task IDs.
    """
    succeeded = []
    failed = []

    for task_id in request.task_ids:
        try:
            task = db.query(VersionDeploymentTask).filter(
                VersionDeploymentTask.task_id == task_id
            ).first()

            if not task:
                failed.append({"task_id": task_id, "error": "Task not found"})
                continue

            if not can_manage_task(task, current_user, db):
                failed.append({"task_id": task_id, "error": "Not authorized"})
                continue

            if task.status not in ["PENDING", "ADJUSTED"]:
                failed.append({"task_id": task_id, "error": f"Invalid status: {task.status}"})
                continue

            # Check validation status
            deployed_before_validation = False
            version = db.query(ModelVersion).get(task.version_id)

            if version and version.validation_request_id:
                val_request = db.query(ValidationRequest).get(version.validation_request_id)
                if val_request:
                    status_value = db.query(TaxonomyValue).get(val_request.current_status_id)
                    if status_value and status_value.code != "APPROVED":
                        if not request.validation_override_reason:
                            failed.append({
                                "task_id": task_id,
                                "error": "Validation not approved, override reason required"
                            })
                            continue
                        deployed_before_validation = True

            # Confirm the task
            task.status = "CONFIRMED"
            task.actual_production_date = request.actual_production_date
            task.confirmation_notes = request.confirmation_notes
            task.deployed_before_validation_approved = deployed_before_validation
            task.validation_override_reason = request.validation_override_reason if deployed_before_validation else None
            task.confirmed_at = utc_now()
            task.confirmed_by_id = current_user.user_id

            # Update ModelRegion
            if task.region_id:
                model_region = db.query(ModelRegion).filter(
                    ModelRegion.model_id == task.model_id,
                    ModelRegion.region_id == task.region_id
                ).first()

                if model_region:
                    model_region.version_id = task.version_id
                    # Issue 1 fix: Use user-provided date, not server timestamp
                    model_region.deployed_at = datetime.combine(
                        request.actual_production_date, datetime.min.time()
                    )
                    if request.confirmation_notes:
                        model_region.deployment_notes = request.confirmation_notes

            # Issue 2 fix: Only update version.actual_production_date when ALL regions deployed
            if version:
                check_and_update_version_production_date(db, version)

            # Auto-create regional approval if required (lock icon region)
            if version and version.validation_request_id and task.region_id:
                create_regional_approval_if_required(db, task, version.validation_request_id)

            # Detect Type 3 exception
            if deployed_before_validation:
                detect_type3_for_deployment_task(db, task)

            # Issue 3 fix: Add audit logging for bulk confirmation
            db.add(AuditLog(
                entity_type="VersionDeploymentTask",
                entity_id=task.task_id,
                action="DEPLOYMENT_CONFIRMED",
                user_id=current_user.user_id,
                changes={
                    "status": task.status,
                    "actual_production_date": str(task.actual_production_date),
                    "region_id": task.region_id,
                    "version_id": task.version_id,
                    "model_id": task.model_id,
                    "deployed_before_validation_approved": task.deployed_before_validation_approved
                }
            ))

            succeeded.append(task_id)

        except Exception as e:
            failed.append({"task_id": task_id, "error": str(e)})

    db.commit()

    return BulkOperationResult(
        succeeded=succeeded,
        failed=failed,
        message=f"Confirmed {len(succeeded)} task(s), {len(failed)} failed"
    )


@router.post("/bulk/adjust", response_model=BulkOperationResult)
def bulk_adjust_deployments(
    request: BulkAdjustRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Adjust planned dates for multiple deployment tasks at once.

    Only works for PENDING or ADJUSTED tasks.
    """
    succeeded = []
    failed = []

    for task_id in request.task_ids:
        try:
            task = db.query(VersionDeploymentTask).filter(
                VersionDeploymentTask.task_id == task_id
            ).first()

            if not task:
                failed.append({"task_id": task_id, "error": "Task not found"})
                continue

            if not can_manage_task(task, current_user, db):
                failed.append({"task_id": task_id, "error": "Not authorized"})
                continue

            if task.status not in ["PENDING", "ADJUSTED"]:
                failed.append({"task_id": task_id, "error": f"Invalid status: {task.status}"})
                continue

            # Adjust the task
            old_date = task.planned_production_date
            task.planned_production_date = request.new_planned_date
            if request.adjustment_reason:
                task.confirmation_notes = request.adjustment_reason
            task.status = "ADJUSTED"

            # Issue 3 fix: Add audit logging for date adjustment
            db.add(AuditLog(
                entity_type="VersionDeploymentTask",
                entity_id=task.task_id,
                action="DEPLOYMENT_DATE_ADJUSTED",
                user_id=current_user.user_id,
                changes={
                    "status": task.status,
                    "old_planned_date": str(old_date) if old_date else None,
                    "new_planned_date": str(request.new_planned_date),
                    "adjustment_reason": request.adjustment_reason,
                    "region_id": task.region_id,
                    "version_id": task.version_id,
                    "model_id": task.model_id
                }
            ))

            succeeded.append(task_id)

        except Exception as e:
            failed.append({"task_id": task_id, "error": str(e)})

    db.commit()

    return BulkOperationResult(
        succeeded=succeeded,
        failed=failed,
        message=f"Adjusted {len(succeeded)} task(s), {len(failed)} failed"
    )


@router.post("/bulk/cancel", response_model=BulkOperationResult)
def bulk_cancel_deployments(
    request: BulkCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel multiple deployment tasks at once.

    Only works for PENDING or ADJUSTED tasks.
    """
    succeeded = []
    failed = []

    for task_id in request.task_ids:
        try:
            task = db.query(VersionDeploymentTask).filter(
                VersionDeploymentTask.task_id == task_id
            ).first()

            if not task:
                failed.append({"task_id": task_id, "error": "Task not found"})
                continue

            if not can_manage_task(task, current_user, db):
                failed.append({"task_id": task_id, "error": "Not authorized"})
                continue

            if task.status not in ["PENDING", "ADJUSTED"]:
                failed.append({"task_id": task_id, "error": f"Invalid status: {task.status}"})
                continue

            # Cancel the task
            task.status = "CANCELLED"
            if request.cancellation_reason:
                task.confirmation_notes = request.cancellation_reason

            # Issue 3 fix: Add audit logging for cancellation
            db.add(AuditLog(
                entity_type="VersionDeploymentTask",
                entity_id=task.task_id,
                action="DEPLOYMENT_CANCELLED",
                user_id=current_user.user_id,
                changes={
                    "status": task.status,
                    "cancellation_reason": request.cancellation_reason,
                    "region_id": task.region_id,
                    "version_id": task.version_id,
                    "model_id": task.model_id
                }
            ))

            succeeded.append(task_id)

        except Exception as e:
            failed.append({"task_id": task_id, "error": str(e)})

    db.commit()

    return BulkOperationResult(
        succeeded=succeeded,
        failed=failed,
        message=f"Cancelled {len(succeeded)} task(s), {len(failed)} failed"
    )
