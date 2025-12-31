"""Model versions routes."""
import csv
import io
from typing import List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.roles import is_admin, is_validator
from app.core.validation_conflicts import (
    find_active_validation_conflicts,
    build_validation_conflict_message
)
from app.models.user import User
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.model_delegate import ModelDelegate
from app.models.audit_log import AuditLog
from app.models.model_change_taxonomy import ModelChangeType, ModelChangeCategory
from app.models.validation import ValidationRequest, ValidationWorkflowSLA, ValidationRequestModelVersion
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.model_region import ModelRegion
from app.models.region import Region
from app.models.version_deployment_task import VersionDeploymentTask
from app.schemas.model_version import (
    ModelVersionCreate,
    ModelVersionUpdate,
    ModelVersionResponse,
    VersionStatus,
    ReadyToDeployVersion,
    ReadyToDeploySummary,
)
from fpdf import FPDF

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


def generate_next_version_number(db: Session, model_id: int, change_type: str) -> str:
    """Auto-generate the next version number based on the latest version and change type."""
    # Get the latest version (highest version_id = most recent)
    latest_version = db.query(ModelVersion).filter(
        ModelVersion.model_id == model_id
    ).order_by(desc(ModelVersion.created_at)).first()

    if not latest_version:
        # First version
        return "1.0"

    # Try to parse the latest version number as "major.minor"
    try:
        parts = latest_version.version_number.split('.')
        if len(parts) >= 2:
            major = int(parts[0])
            minor = int(parts[1])

            if change_type == "MAJOR":
                # Increment major, reset minor to 0
                return f"{major + 1}.0"
            else:
                # Increment minor
                return f"{major}.{minor + 1}"
        else:
            # Can't parse, try to increment as integer
            try:
                num = int(latest_version.version_number)
                return str(num + 1)
            except ValueError:
                # Not a number, default to incrementing from 1.0
                if change_type == "MAJOR":
                    return "2.0"
                else:
                    return "1.1"
    except (ValueError, IndexError):
        # Version number is not numeric (e.g., "v2.0", "2024.Q1")
        # Default to standard versioning
        if change_type == "MAJOR":
            return "2.0"
        else:
            return "1.1"


def check_version_permission(db: Session, model: Model, user: User) -> bool:
    """Check if user has permission to create/manage versions."""
    # Owner, developer, or admin can create versions
    if is_admin(user):
        return True
    if model.owner_id == user.user_id:
        return True
    if model.developer_id == user.user_id:
        return True

    # Check if user is an active delegate with can_submit_changes permission
    delegate = db.query(ModelDelegate).filter(
        ModelDelegate.model_id == model.model_id,
        ModelDelegate.user_id == user.user_id,
        ModelDelegate.can_submit_changes == True,
        ModelDelegate.revoked_at.is_(None)
    ).first()

    if delegate:
        return True

    return False


def check_version_creation_blockers(db: Session, model_id: int) -> dict | None:
    """Check for blockers that prevent creating a new version.

    Returns:
        None if no blockers, otherwise a dict with blocking information.

    Blocking conditions:
    B1: Undeployed version exists (DRAFT or APPROVED without actual_production_date)
        that is NOT in an active validation
    B2: Version is in active validation (status NOT in: APPROVED, CANCELLED, ON_HOLD)
    """
    # Get all versions for this model
    versions = db.query(ModelVersion).filter(
        ModelVersion.model_id == model_id
    ).all()

    # Find non-terminal status codes (active validation statuses)
    # Active = NOT in: APPROVED, CANCELLED, ON_HOLD
    terminal_status_codes = {"APPROVED", "CANCELLED", "ON_HOLD"}

    # Get the Validation Request Status taxonomy to find status IDs
    status_taxonomy = db.query(Taxonomy).filter(
        Taxonomy.name == "Validation Request Status"
    ).first()

    terminal_status_ids = set()
    if status_taxonomy:
        terminal_statuses = db.query(TaxonomyValue).filter(
            TaxonomyValue.taxonomy_id == status_taxonomy.taxonomy_id,
            TaxonomyValue.code.in_(terminal_status_codes)
        ).all()
        terminal_status_ids = {s.value_id for s in terminal_statuses}

    for version in versions:
        # B2: Check if version is in active validation
        # Look for ValidationRequest linked to this version via ValidationRequestModelVersion
        active_validation = db.query(ValidationRequest).join(
            ValidationRequestModelVersion,
            ValidationRequest.request_id == ValidationRequestModelVersion.request_id
        ).filter(
            ValidationRequestModelVersion.version_id == version.version_id,
            ~ValidationRequest.current_status_id.in_(terminal_status_ids) if terminal_status_ids else True
        ).first()

        if active_validation:
            return {
                "error": "version_creation_blocked",
                "reason": "version_in_active_validation",
                "blocking_version_number": version.version_number,
                "blocking_validation_id": active_validation.request_id,
                "message": f"Cannot create new version: version {version.version_number} is in active validation (request #{active_validation.request_id})"
            }

        # B1: Check for undeployed versions not in active validation
        # Undeployed = DRAFT or APPROVED status without actual_production_date
        is_undeployed = (
            version.status in ("DRAFT", "IN_VALIDATION", "APPROVED") and
            version.actual_production_date is None
        )

        if is_undeployed:
            # Skip if this version is linked to a cancelled validation (resolved case)
            cancelled_validation_link = db.query(ValidationRequest).join(
                ValidationRequestModelVersion,
                ValidationRequest.request_id == ValidationRequestModelVersion.request_id
            ).join(
                TaxonomyValue,
                ValidationRequest.current_status_id == TaxonomyValue.value_id
            ).filter(
                ValidationRequestModelVersion.version_id == version.version_id,
                TaxonomyValue.code == "CANCELLED"
            ).first()

            if cancelled_validation_link:
                # This version's validation was cancelled, skip it
                continue

            return {
                "error": "version_creation_blocked",
                "reason": "undeployed_version_exists",
                "blocking_version_number": version.version_number,
                "message": f"Cannot create new version: version {version.version_number} ({version.status}) has not been deployed yet"
            }

    return None


def check_version_deletion_blockers(db: Session, version: ModelVersion) -> dict | None:
    """Check for blockers that prevent deleting a version.

    Returns:
        None if no blockers, otherwise a dict with blocking information.

    Blocking conditions:
    B3: Version is linked to any validation request
    """
    # Check if version is linked to any validation via ValidationRequestModelVersion
    validation_link = db.query(ValidationRequest).join(
        ValidationRequestModelVersion,
        ValidationRequest.request_id == ValidationRequestModelVersion.request_id
    ).filter(
        ValidationRequestModelVersion.version_id == version.version_id
    ).first()

    if validation_link:
        # Get the validation number for the error message
        validation_number = f"VAL-{validation_link.request_id:03d}"
        return {
            "error": "version_deletion_blocked",
            "reason": "linked_to_validation",
            "validation_number": validation_number,
            "validation_id": validation_link.request_id,
            "message": f"Cannot delete version: it is linked to validation request {validation_number}"
        }

    return None


@router.get("/models/{model_id}/versions/next-version")
def get_next_version_preview(
    model_id: int,
    change_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Preview what the next auto-generated version number would be."""
    from app.core.rls import can_access_model

    # Check RLS access
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    next_version = generate_next_version_number(db, model_id, change_type)
    return {"next_version": next_version, "change_type": change_type}


@router.post("/models/{model_id}/versions", response_model=ModelVersionResponse, status_code=status.HTTP_201_CREATED)
def create_model_version(
    model_id: int,
    version_data: ModelVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new model version (submit model change)."""
    from app.core.rls import can_access_model

    # Check RLS access first
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Get model
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Check permissions
    if not check_version_permission(db, model, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only model owner, developer, or delegates can submit changes"
        )

    # Check for blockers (undeployed versions or versions in active validation)
    blocker = check_version_creation_blockers(db, model_id)
    if blocker:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=blocker
        )

    # Auto-generate version number if not provided
    version_number = version_data.version_number
    if not version_number:
        version_number = generate_next_version_number(
            db, model_id, version_data.change_type)

    # Check if version number already exists for this model
    existing = db.query(ModelVersion).filter(
        ModelVersion.model_id == model_id,
        ModelVersion.version_number == version_number
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Version {version_number} already exists for this model"
        )

    # Capture point-in-time snapshot of MV approval requirement
    requires_mv_approval = None
    if version_data.change_type_id:
        # Look up current approval requirement from taxonomy
        change_type_detail = db.query(ModelChangeType).filter(
            ModelChangeType.change_type_id == version_data.change_type_id
        ).first()
        if change_type_detail:
            requires_mv_approval = change_type_detail.requires_mv_approval
    elif version_data.change_type == "MAJOR":
        # Legacy fallback: MAJOR changes require approval
        requires_mv_approval = True
    elif version_data.change_type == "MINOR":
        # Legacy fallback: MINOR changes do not require approval
        requires_mv_approval = False

    # Create version with regional scope support
    new_version = ModelVersion(
        model_id=model_id,
        version_number=version_number,
        change_type=version_data.change_type,
        change_type_id=version_data.change_type_id,
        change_description=version_data.change_description,
        scope=version_data.scope,
        planned_production_date=version_data.planned_production_date or version_data.production_date,
        actual_production_date=version_data.actual_production_date,
        production_date=version_data.production_date or version_data.planned_production_date,  # Legacy field
        created_by_id=current_user.user_id,
        status=VersionStatus.DRAFT,
        change_requires_mv_approval=requires_mv_approval  # Point-in-time snapshot
    )

    db.add(new_version)
    db.flush()  # Get version_id before adding regions

    # Handle affected regions (if REGIONAL scope)
    if version_data.scope == "REGIONAL" and version_data.affected_region_ids:
        from app.models.model_version_region import ModelVersionRegion
        from app.models.region import Region

        # Verify regions exist
        regions = db.query(Region).filter(
            Region.region_id.in_(version_data.affected_region_ids)
        ).all()

        # Create associations
        for region in regions:
            assoc = ModelVersionRegion(
                version_id=new_version.version_id,
                region_id=region.region_id
            )
            db.add(assoc)

    db.flush()

    # Auto-create validation request for MAJOR changes (requires MV approval)
    validation_request = None
    validation_warning = None
    validation_type_code = None

    # Determine production date (prefer planned_production_date)
    target_production_date = version_data.planned_production_date or version_data.production_date

    # Get ValidationWorkflowSLA configuration (needed for lead time calculation)
    sla_config = db.query(ValidationWorkflowSLA).first()
    if not sla_config:
        # Create default SLA if doesn't exist
        sla_config = ValidationWorkflowSLA()
        db.add(sla_config)
        db.flush()
        db.refresh(sla_config)

    # Check lead time policy for ALL changes if production date is provided
    if target_production_date:
        from app.models.validation import ValidationPolicy

        # Calculate lead time based on submission date (today) vs implementation date
        days_lead_time = (target_production_date - date.today()).days

        # Get model-specific completion lead time from validation policy
        completion_lead_time = 90  # Default
        if model.risk_tier_id:
            policy = db.query(ValidationPolicy).filter(
                ValidationPolicy.risk_tier_id == model.risk_tier_id
            ).first()
            if policy:
                completion_lead_time = policy.model_change_lead_time_days

        # Total lead time = completion lead time + workflow SLA phases
        lead_time_required = completion_lead_time
        if sla_config:
            lead_time_required += (sla_config.assignment_days or 0)
            lead_time_required += (sla_config.begin_work_days or 0)
            lead_time_required += (sla_config.approval_days or 0)

        if days_lead_time < lead_time_required:
            msg = f"Request submitted with insufficient lead time. Policy requires {lead_time_required} days lead time before implementation, but only {max(0, days_lead_time)} days remain."
            validation_warning = msg

    if version_data.change_type == "MAJOR":
        from datetime import timedelta

        # Calculate total SLA time using risk-tier-based lead time
        # lead_time_required was calculated above if target_production_date exists
        # Use default of 90 if not set (no production date provided)
        work_lead_time = lead_time_required if target_production_date else 90
        total_sla_days = (
            sla_config.assignment_days +
            sla_config.begin_work_days +
            work_lead_time +  # Risk-tier-based lead time (replaces fixed complete_work_days)
            sla_config.approval_days
        )

        # Determine validation type and priority based on production date
        is_interim = False
        validation_type_code = "TARGETED"
        priority_code = "MEDIUM"  # Medium by default

        if target_production_date:
            days_until_production = (
                target_production_date - date.today()).days

            if days_until_production <= total_sla_days:
                # Within lead time window - use INTERIM validation
                is_interim = True
                validation_type_code = "INTERIM"
                priority_code = "HIGH"  # High priority
                # Only add SLA message if no lead time warning already set (avoid redundant messaging)
                if not validation_warning:
                    validation_warning = f"Production date ({target_production_date}) is within {days_until_production} days. " \
                        f"Standard validation SLA is {total_sla_days} days. Expedited INTERIM review required."

        conflicts = find_active_validation_conflicts(
            db,
            [model_id],
            validation_type_code
        )
        if conflicts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=build_validation_conflict_message(conflicts, validation_type_code)
            )

        # Get validation type from taxonomy
        validation_type = db.query(TaxonomyValue).join(
            TaxonomyValue.taxonomy
        ).filter(
            TaxonomyValue.code == validation_type_code,
            TaxonomyValue.taxonomy.has(name="Validation Type")
        ).first()

        if validation_type:
            # Get priority
            priority = db.query(TaxonomyValue).join(
                TaxonomyValue.taxonomy
            ).filter(
                TaxonomyValue.code == priority_code,
                TaxonomyValue.taxonomy.has(name="Validation Priority")
            ).first()

            if priority:
                # Calculate target completion date
                if target_production_date:
                    # Target completion should be 5 business days before production (safety buffer)
                    target_date = target_production_date - \
                        timedelta(days=5)

                    # Check if target completion is after production date (out of order)
                    if target_date > target_production_date:
                        if validation_warning:
                            validation_warning += " Target completion date exceeds planned production date."
                        else:
                            validation_warning = "WARNING: Validation target completion date exceeds planned production date."
                else:
                    # No production date provided, use standard 30 days
                    target_date = date.today() + timedelta(days=30)

                # Build trigger reason
                trigger_reason = f"Auto-created for model version {version_number} - {version_data.change_description[:100]}"
                if validation_warning:
                    trigger_reason = validation_warning + " " + trigger_reason

                # Get initial status (INTAKE)
                initial_status = db.query(TaxonomyValue).join(
                    TaxonomyValue.taxonomy
                ).filter(
                    TaxonomyValue.code == "INTAKE",
                    TaxonomyValue.taxonomy.has(
                        name="Validation Request Status")
                ).first()

                # Create validation request (without model_id - uses association table)
                validation_request = ValidationRequest(
                    request_date=date.today(),
                    requestor_id=current_user.user_id,
                    validation_type_id=validation_type.value_id,
                    priority_id=priority.value_id,
                    current_status_id=initial_status.value_id,
                    target_completion_date=target_date,
                    trigger_reason=trigger_reason
                )

                db.add(validation_request)
                db.flush()  # Get request_id without full commit

                # Link model and version to validation request via association table
                from app.models.validation import ValidationRequestModelVersion
                model_version_link = ValidationRequestModelVersion(
                    request_id=validation_request.request_id,
                    model_id=model_id,
                    version_id=new_version.version_id
                )
                db.add(model_version_link)

                # Link validation request to version
                new_version.validation_request_id = validation_request.request_id

                # Handle regional scope - add regions to validation request
                # Use the regions from the version's affected_regions relationship
                if version_data.scope == "REGIONAL" and new_version.affected_regions:
                    validation_request.regions = new_version.affected_regions

                # Audit log for validation request creation
                create_audit_log(
                    db=db,
                    entity_type="ValidationRequest",
                    entity_id=validation_request.request_id,
                    action="CREATE",
                    user_id=current_user.user_id,
                    changes={
                        "auto_created": True,
                        "model_version_id": new_version.version_id,
                        "is_interim": is_interim,
                        "production_date": str(target_production_date) if target_production_date else None,
                        "scope": version_data.scope,
                        "affected_region_ids": version_data.affected_region_ids
                    }
                )

    # Audit log for version creation
    create_audit_log(
        db=db,
        entity_type="ModelVersion",
        entity_id=new_version.version_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={"version_number": version_number, "change_type": version_data.change_type,
                 "auto_generated": not version_data.version_number}
    )
    db.commit()
    db.refresh(new_version)

    # Eager-load the affected_regions_assoc for the response
    if new_version.scope == "REGIONAL":
        _ = new_version.affected_regions_assoc

    # Create response with validation info
    response_dict = {
        **new_version.__dict__,
        "affected_region_ids": new_version.affected_region_ids,  # Use property
        "validation_request_created": validation_request is not None,
        "validation_type": validation_type_code if validation_request else None,
        "validation_warning": validation_warning
    }

    return ModelVersionResponse(**response_dict)


@router.get("/models/{model_id}/versions", response_model=List[ModelVersionResponse])
def list_model_versions(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all versions for a model (newest first)."""
    from app.core.rls import can_access_model

    # Check RLS access
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    versions = db.query(ModelVersion).options(
        joinedload(ModelVersion.change_type_detail).joinedload(
            ModelChangeType.category),
        joinedload(ModelVersion.created_by),
        # Eager-load for affected_region_ids property
        joinedload(ModelVersion.affected_regions_assoc)
    ).filter(
        ModelVersion.model_id == model_id
    ).order_by(desc(ModelVersion.created_at)).all()

    # Pre-fetch validation request statuses for versions that have validation_request_id
    validation_request_ids = [v.validation_request_id for v in versions if v.validation_request_id]
    validation_status_map = {}
    if validation_request_ids:
        # Get validation requests with their current status codes
        validation_requests = db.query(
            ValidationRequest.request_id,
            TaxonomyValue.code
        ).join(
            TaxonomyValue,
            ValidationRequest.current_status_id == TaxonomyValue.value_id
        ).filter(
            ValidationRequest.request_id.in_(validation_request_ids)
        ).all()
        validation_status_map = {req.request_id: req.code for req in validation_requests}

    # Populate taxonomy names in response
    result = []
    for version in versions:
        version_dict = {
            "version_id": version.version_id,
            "model_id": version.model_id,
            "version_number": version.version_number,
            "change_type": version.change_type,
            "change_type_id": version.change_type_id,
            "change_description": version.change_description,
            "status": version.status,
            "created_by_id": version.created_by_id,
            "created_at": version.created_at,
            # Production dates (new fields)
            "planned_production_date": version.planned_production_date,
            "actual_production_date": version.actual_production_date,
            "production_date": version.production_date,  # Legacy field
            # Regional scope (new fields)
            "scope": version.scope,
            "affected_region_ids": version.affected_region_ids,
            # Validation
            "validation_request_id": version.validation_request_id,
            # Validation workflow status (for edit permission checks)
            "validation_request_status": validation_status_map.get(version.validation_request_id) if version.validation_request_id else None,
            # Point-in-time compliance snapshot
            "change_requires_mv_approval": version.change_requires_mv_approval,
            # Nested/populated fields
            "created_by_name": version.created_by.full_name if version.created_by else None,
            "change_type_name": version.change_type_detail.name if version.change_type_detail else None,
            "change_category_name": version.change_type_detail.category.name if version.change_type_detail and version.change_type_detail.category else None,
        }
        result.append(version_dict)

    return result


@router.get("/models/{model_id}/versions/current", response_model=ModelVersionResponse)
def get_current_version(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the current ACTIVE version for a model."""
    from app.core.rls import can_access_model

    # Check RLS access
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    current_version = db.query(ModelVersion).filter(
        ModelVersion.model_id == model_id,
        ModelVersion.status == VersionStatus.ACTIVE
    ).first()

    if not current_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active version found for this model"
        )

    return current_version


@router.patch("/versions/{version_id}/approve", response_model=ModelVersionResponse)
def approve_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a version as APPROVED (requires Validator or Admin role)."""
    # Only validators and admins can approve
    if not (is_admin(current_user) or is_validator(current_user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Validators and Admins can approve versions"
        )

    version = db.query(ModelVersion).filter(
        ModelVersion.version_id == version_id).first()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    # Can only approve versions that are IN_VALIDATION
    if version.status != VersionStatus.IN_VALIDATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve version with status {version.status}. Must be IN_VALIDATION."
        )

    old_status = version.status
    version.status = VersionStatus.APPROVED

    # Audit log
    create_audit_log(
        db=db,
        entity_type="ModelVersion",
        entity_id=version.version_id,
        action="UPDATE",
        user_id=current_user.user_id,
        changes={"status": {"old": old_status, "new": VersionStatus.APPROVED}}
    )

    db.commit()
    db.refresh(version)

    return version


@router.patch("/versions/{version_id}/activate", response_model=ModelVersionResponse)
def activate_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a version as ACTIVE (only one ACTIVE per model, requires model owner/developer permission)."""
    version = db.query(ModelVersion).filter(
        ModelVersion.version_id == version_id).first()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    # Check permissions
    model = db.query(Model).filter(Model.model_id == version.model_id).first()
    if not check_version_permission(db, model, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only model owner, developer, or admin can activate versions"
        )

    # Can only activate APPROVED versions
    if version.status != VersionStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot activate version with status {version.status}. Must be APPROVED first."
        )

    # Mark current ACTIVE version as SUPERSEDED
    current_active = db.query(ModelVersion).filter(
        ModelVersion.model_id == version.model_id,
        ModelVersion.status == VersionStatus.ACTIVE
    ).first()

    if current_active:
        current_active.status = VersionStatus.SUPERSEDED
        create_audit_log(
            db=db,
            entity_type="ModelVersion",
            entity_id=current_active.version_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes={"status": {"old": VersionStatus.ACTIVE,
                                "new": VersionStatus.SUPERSEDED}}
        )

    # Activate new version
    old_status = version.status
    version.status = VersionStatus.ACTIVE

    create_audit_log(
        db=db,
        entity_type="ModelVersion",
        entity_id=version.version_id,
        action="UPDATE",
        user_id=current_user.user_id,
        changes={"status": {"old": old_status, "new": VersionStatus.ACTIVE}}
    )

    db.commit()
    db.refresh(version)

    return version


@router.patch("/versions/{version_id}/production", response_model=ModelVersionResponse)
def set_production_date(
    version_id: int,
    production_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Set the production deployment date for a version."""
    version = db.query(ModelVersion).filter(
        ModelVersion.version_id == version_id).first()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    # Check permissions
    model = db.query(Model).filter(Model.model_id == version.model_id).first()
    if not check_version_permission(db, model, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only model owner, developer, or admin can set production date"
        )

    old_date = version.production_date
    version.production_date = production_date

    create_audit_log(
        db=db,
        entity_type="ModelVersion",
        entity_id=version.version_id,
        action="UPDATE",
        user_id=current_user.user_id,
        changes={"production_date": {"old": str(
            old_date) if old_date else None, "new": str(production_date)}}
    )

    db.commit()
    db.refresh(version)

    return version


@router.delete("/versions/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a DRAFT version (only DRAFT versions can be deleted)."""
    version = db.query(ModelVersion).filter(
        ModelVersion.version_id == version_id).first()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    # Check permissions
    model = db.query(Model).filter(Model.model_id == version.model_id).first()
    if not check_version_permission(db, model, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only model owner, developer, or admin can delete versions"
        )

    # Can only delete DRAFT versions
    if version.status != VersionStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete version with status {version.status}. Only DRAFT versions can be deleted."
        )

    # Check for blockers (version linked to validation)
    blocker = check_version_deletion_blockers(db, version)
    if blocker:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=blocker
        )

    create_audit_log(
        db=db,
        entity_type="ModelVersion",
        entity_id=version.version_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={"version_number": version.version_number}
    )

    db.delete(version)
    db.commit()

    return None


@router.get("/models/{model_id}/versions/export/csv")
def export_model_versions_csv(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export all versions for a model to CSV.

    Row-Level Security:
    - Admin, Validator, Global Approver, Regional Approver: Can export any model's versions
    - User: Can only export versions for models they have access to
    """
    from app.core.rls import can_access_model

    # Check RLS access
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Get all versions with relationships
    versions = db.query(ModelVersion).options(
        joinedload(ModelVersion.change_type_detail).joinedload(
            ModelChangeType.category),
        joinedload(ModelVersion.created_by),
        # Eager-load for affected_region_ids property
        joinedload(ModelVersion.affected_regions_assoc)
    ).filter(
        ModelVersion.model_id == model_id
    ).order_by(desc(ModelVersion.created_at)).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "Version ID",
        "Version Number",
        "Change Type",
        "Change Category",
        "Change Type Detail",
        "Status",
        "Change Description",
        "Created By",
        "Created At",
        "Production Date",
        "Validation Request ID"
    ])

    # Write data rows
    for version in versions:
        writer.writerow([
            version.version_id,
            version.version_number,
            version.change_type,
            version.change_type_detail.category.name if version.change_type_detail and version.change_type_detail.category else "",
            version.change_type_detail.name if version.change_type_detail else "",
            version.status,
            version.change_description,
            version.created_by.full_name if version.created_by else "",
            version.created_at.strftime(
                "%Y-%m-%d %H:%M:%S") if version.created_at else "",
            version.production_date.strftime(
                "%Y-%m-%d") if version.production_date else "",
            version.validation_request_id or ""
        ])

    # Prepare response
    output.seek(0)
    filename = f"model_{model_id}_versions_{date.today().strftime('%Y-%m-%d')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/models/{model_id}/versions/export/pdf")
def export_model_versions_pdf(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export all versions for a model to PDF.
    """
    from app.core.rls import can_access_model

    # Check RLS access
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Verify model exists
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Get all versions with relationships
    versions = db.query(ModelVersion).options(
        joinedload(ModelVersion.change_type_detail).joinedload(
            ModelChangeType.category),
        joinedload(ModelVersion.created_by),
        joinedload(ModelVersion.affected_regions_assoc)
    ).filter(
        ModelVersion.model_id == model_id
    ).order_by(desc(ModelVersion.created_at)).all()

    # Create PDF
    try:
        from app.models.region import Region

        # Fetch regions for lookup
        all_regions = db.query(Region).all()
        region_map = {r.region_id: r.code for r in all_regions}

        class PDF(FPDF):
            def header(self):
                self.set_font('Helvetica', 'B', 15)
                # Sanitize model name for Latin-1 encoding
                model_name = model.model_name.encode(
                    'latin-1', 'replace').decode('latin-1')
                self.cell(
                    0, 10, f'Model Change Log: {model_name}', 0, 1, 'C')
                self.set_font('Helvetica', 'I', 10)
                self.cell(
                    0, 10, f'Generated on {date.today().strftime("%Y-%m-%d")}', 0, 1, 'C')
                self.ln(5)

            def footer(self):
                self.set_y(-15)
                self.set_font('Helvetica', 'I', 8)
                self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

        pdf = PDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        pdf.set_font("Helvetica", size=10)

        # Table Header
        headers = ["Ver", "Type", "Status", "Description", "Date", "User"]
        widths = [15, 25, 25, 75, 25, 25]

        pdf.set_fill_color(200, 220, 255)
        pdf.set_font("Helvetica", 'B', 8)
        for i, header in enumerate(headers):
            pdf.cell(widths[i], 6, header, 1, 0, 'C', True)
        pdf.ln()

        # Table Rows
        pdf.set_font("Helvetica", size=8)
        for version in versions:
            # Calculate description text with regions
            description_text = version.change_description or ""
            if version.scope == "REGIONAL":
                region_codes = []
                for assoc in version.affected_regions_assoc:
                    r_code = region_map.get(assoc.region_id, "Unknown")
                    region_codes.append(r_code)
                region_codes.sort()
                if region_codes:
                    description_text = f"[Regions: {', '.join(region_codes)}]\n{description_text}"

            # Sanitize description
            description_text = description_text.encode(
                'latin-1', 'replace').decode('latin-1')

            # Calculate row height based on description
            # Use dry_run to calculate lines
            lines = pdf.multi_cell(
                widths[3], 5, description_text, dry_run=True, output='LINES')
            num_lines = len(lines)
            row_height = max(6, num_lines * 5)

            # Check page break
            if pdf.get_y() + row_height > pdf.page_break_trigger:
                pdf.add_page()
                # Re-draw header
                pdf.set_fill_color(200, 220, 255)
                pdf.set_font("Helvetica", 'B', 8)
                for i, header in enumerate(headers):
                    pdf.cell(widths[i], 6, header, 1, 0, 'C', True)
                pdf.ln()
                pdf.set_font("Helvetica", size=8)

            # Sanitize other fields
            v_num = str(version.version_number).encode(
                'latin-1', 'replace').decode('latin-1')

            change_type = version.change_type
            if version.change_type_detail:
                change_type = version.change_type_detail.name
            change_type = change_type.encode(
                'latin-1', 'replace').decode('latin-1')

            status_text = version.status.encode(
                'latin-1', 'replace').decode('latin-1')

            prod_date = version.production_date or version.created_at.date()

            user_name = version.created_by.full_name if version.created_by else "Unknown"
            user_name = user_name.encode(
                'latin-1', 'replace').decode('latin-1')

            # Draw cells
            # Save current position
            x_start = pdf.get_x()
            y_start = pdf.get_y()

            pdf.cell(widths[0], row_height, v_num, 1, 0, 'C')
            pdf.cell(widths[1], row_height, change_type[:15], 1, 0, 'C')
            pdf.cell(widths[2], row_height, status_text, 1, 0, 'C')

            # Description (MultiCell)
            x_desc = pdf.get_x()
            y_desc = pdf.get_y()

            # Draw text
            pdf.multi_cell(widths[3], 5, description_text, border=0, align='L')

            # Draw border
            pdf.rect(x_desc, y_desc, widths[3], row_height)

            # Move to next column
            pdf.set_xy(x_desc + widths[3], y_desc)

            pdf.cell(widths[4], row_height, str(prod_date), 1, 0, 'C')
            pdf.cell(widths[5], row_height, user_name[:15],
                     1, 1, 'C')  # ln=1 to move to next line

        # Output PDF
        pdf_bytes = pdf.output()

        filename = f"model_{model_id}_changelog_{date.today().strftime('%Y-%m-%d')}.pdf"

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )


# ============================================================================
# READY TO DEPLOY - Must come before generic /versions/{version_id} routes
# ============================================================================
@router.get("/versions/ready-to-deploy", response_model=List[ReadyToDeployVersion])
def get_ready_to_deploy_versions(
    model_id: int = None,
    my_models_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get versions that are validated (APPROVED) but not yet fully deployed.

    This helps model owners identify what needs to be deployed to production.

    A version appears here if:
    - Its linked ValidationRequest has current_status_id = APPROVED
    - It hasn't been deployed to ALL model regions yet

    Query params:
    - model_id: Filter to specific model
    - my_models_only: Only show versions for models user owns/develops/delegates
    """
    from app.core.rls import can_access_model

    # Find the APPROVED status value_id
    status_taxonomy = db.query(Taxonomy).filter(
        Taxonomy.name == "Validation Request Status"
    ).first()

    if not status_taxonomy:
        return []

    approved_status = db.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == status_taxonomy.taxonomy_id,
        TaxonomyValue.code == "APPROVED"
    ).first()

    if not approved_status:
        return []

    # Query versions with APPROVED validation requests
    versions_query = db.query(ModelVersion).join(
        ValidationRequest,
        ModelVersion.validation_request_id == ValidationRequest.request_id
    ).join(
        Model,
        ModelVersion.model_id == Model.model_id
    ).filter(
        ValidationRequest.current_status_id == approved_status.value_id
    ).options(
        joinedload(ModelVersion.model),
        joinedload(ModelVersion.validation_request)
    )

    # Apply model_id filter
    if model_id:
        versions_query = versions_query.filter(ModelVersion.model_id == model_id)

    # Apply my_models_only filter
    if my_models_only:
        from app.models.model_delegate import ModelDelegate
        # Filter to models user owns, develops, or is a delegate for
        versions_query = versions_query.filter(
            (Model.owner_id == current_user.user_id) |
            (Model.developer_id == current_user.user_id) |
            Model.model_id.in_(
                db.query(ModelDelegate.model_id).filter(
                    ModelDelegate.user_id == current_user.user_id,
                    ModelDelegate.revoked_at.is_(None)
                )
            )
        )

    versions = versions_query.all()

    # Filter by RLS access and deployment status
    results = []

    for version in versions:
        # Check RLS access
        if not can_access_model(version.model_id, current_user, db):
            continue

        # Get all regions for this model
        model_regions = db.query(ModelRegion).filter(
            ModelRegion.model_id == version.model_id
        ).options(joinedload(ModelRegion.region)).all()

        total_regions_count = len(model_regions)

        if total_regions_count == 0:
            # Model has no regions, skip (can't be deployed)
            continue

        # Get CONFIRMED deployment tasks for this version
        confirmed_tasks = db.query(VersionDeploymentTask).filter(
            VersionDeploymentTask.version_id == version.version_id,
            VersionDeploymentTask.status == "CONFIRMED"
        ).all()

        confirmed_region_ids = {task.region_id for task in confirmed_tasks}
        deployed_regions_count = len(confirmed_region_ids)

        # Skip if fully deployed
        if deployed_regions_count >= total_regions_count:
            continue

        # Calculate pending regions
        pending_regions = []
        for mr in model_regions:
            if mr.region_id not in confirmed_region_ids:
                pending_regions.append(mr.region.code if mr.region else "Unknown")

        # Get PENDING deployment tasks count
        pending_tasks_count = db.query(VersionDeploymentTask).filter(
            VersionDeploymentTask.version_id == version.version_id,
            VersionDeploymentTask.status == "PENDING"
        ).count()

        # Get owner name
        owner = db.query(User).filter(User.user_id == version.model.owner_id).first()
        owner_name = owner.full_name if owner else "Unknown"

        # Calculate days since approval
        val_request = version.validation_request
        if val_request and val_request.completion_date:
            # Convert datetime to date if needed
            completion = val_request.completion_date
            if hasattr(completion, 'date'):
                completion = completion.date()
            days_since_approval = (date.today() - completion).days
        else:
            # Use request_date as fallback
            if val_request and val_request.request_date:
                request_dt = val_request.request_date
                if hasattr(request_dt, 'date'):
                    request_dt = request_dt.date()
                days_since_approval = (date.today() - request_dt).days
            else:
                days_since_approval = 0

        # Get validation_approved_date, converting datetime to date if needed
        validation_approved_date = None
        if val_request and val_request.completion_date:
            approved_dt = val_request.completion_date
            if hasattr(approved_dt, 'date'):
                validation_approved_date = approved_dt.date()
            else:
                validation_approved_date = approved_dt

        results.append(ReadyToDeployVersion(
            version_id=version.version_id,
            version_number=version.version_number,
            model_id=version.model_id,
            model_name=version.model.model_name,
            validation_status="Approved",
            validation_approved_date=validation_approved_date,
            total_regions_count=total_regions_count,
            deployed_regions_count=deployed_regions_count,
            pending_regions=pending_regions,
            pending_tasks_count=pending_tasks_count,
            has_pending_tasks=pending_tasks_count > 0,
            owner_name=owner_name,
            days_since_approval=days_since_approval
        ))

    # Sort by days_since_approval descending (oldest approvals first)
    results.sort(key=lambda x: x.days_since_approval, reverse=True)

    return results


@router.get("/versions/ready-to-deploy/summary", response_model=ReadyToDeploySummary)
def get_ready_to_deploy_summary(
    my_models_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get summary statistics for ready-to-deploy versions.

    Useful for dashboard badges and quick metrics.

    Returns:
    - ready_count: Total versions ready to deploy
    - partially_deployed_count: Deployed to some but not all regions
    - with_pending_tasks_count: Have scheduled deployment tasks
    """
    # Reuse the main endpoint logic to get the data
    versions = get_ready_to_deploy_versions(
        model_id=None,
        my_models_only=my_models_only,
        db=db,
        current_user=current_user
    )

    ready_count = len(versions)
    partially_deployed_count = sum(1 for v in versions if v.deployed_regions_count > 0)
    with_pending_tasks_count = sum(1 for v in versions if v.has_pending_tasks)

    return ReadyToDeploySummary(
        ready_count=ready_count,
        partially_deployed_count=partially_deployed_count,
        with_pending_tasks_count=with_pending_tasks_count
    )


# ============================================================================
# GENERIC VERSION ROUTES - Must come after specific routes
# ============================================================================
@router.get("/versions/{version_id}", response_model=ModelVersionResponse)
def get_version_details(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a specific version."""
    from app.core.rls import can_access_model

    version = db.query(ModelVersion).options(
        joinedload(ModelVersion.change_type_detail).joinedload(
            ModelChangeType.category),
        joinedload(ModelVersion.created_by),
        joinedload(ModelVersion.model),
        # Eager-load for affected_region_ids property
        joinedload(ModelVersion.affected_regions_assoc)
    ).filter(ModelVersion.version_id == version_id).first()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    # Check RLS access to the model
    if not can_access_model(version.model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    # Get validation request status if version has a linked validation request
    validation_request_status = None
    if version.validation_request_id:
        validation_status = db.query(TaxonomyValue.code).join(
            ValidationRequest,
            ValidationRequest.current_status_id == TaxonomyValue.value_id
        ).filter(
            ValidationRequest.request_id == version.validation_request_id
        ).first()
        if validation_status:
            validation_request_status = validation_status.code

    # Build response with taxonomy names
    return {
        "version_id": version.version_id,
        "model_id": version.model_id,
        "version_number": version.version_number,
        "change_type": version.change_type,
        "change_type_id": version.change_type_id,
        "change_description": version.change_description,
        "status": version.status,
        "created_by_id": version.created_by_id,
        "created_at": version.created_at,
        # Production dates (new fields)
        "planned_production_date": version.planned_production_date,
        "actual_production_date": version.actual_production_date,
        "production_date": version.production_date,  # Legacy field
        # Regional scope (new fields)
        "scope": version.scope,
        "affected_region_ids": version.affected_region_ids,
        # Validation
        "validation_request_id": version.validation_request_id,
        # Point-in-time compliance snapshot
        "change_requires_mv_approval": version.change_requires_mv_approval,
        # Nested/populated fields
        "created_by_name": version.created_by.full_name if version.created_by else None,
        "change_type_name": version.change_type_detail.name if version.change_type_detail else None,
        "change_category_name": version.change_type_detail.category.name if version.change_type_detail and version.change_type_detail.category else None,
        # Validation workflow status (for edit permission checks)
        "validation_request_status": validation_request_status,
    }


@router.patch("/versions/{version_id}", response_model=ModelVersionResponse)
def update_version(
    version_id: int,
    version_data: ModelVersionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a version (only DRAFT versions can be edited, and only before validation begins)."""
    version = db.query(ModelVersion).filter(
        ModelVersion.version_id == version_id).first()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    # Check permissions
    model = db.query(Model).filter(Model.model_id == version.model_id).first()
    if not check_version_permission(db, model, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only model owner, developer, or delegates can edit versions"
        )

    # Can only edit DRAFT versions
    if version.status != VersionStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit version with status {version.status}. Only DRAFT versions can be edited."
        )

    # If validation has begun, only validators/admins can edit
    if version.validation_request_id is not None:
        if not (is_admin(current_user) or is_validator(current_user)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only validators and admins can edit versions after validation has begun"
            )

    # Track changes for audit log
    changes = {}

    # Update fields if provided
    if version_data.version_number is not None:
        # Check if new version number already exists for this model
        existing = db.query(ModelVersion).filter(
            ModelVersion.model_id == version.model_id,
            ModelVersion.version_number == version_data.version_number,
            ModelVersion.version_id != version_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Version {version_data.version_number} already exists for this model"
            )
        changes["version_number"] = {
            "old": version.version_number, "new": version_data.version_number}
        version.version_number = version_data.version_number

    if version_data.change_type is not None:
        changes["change_type"] = {
            "old": version.change_type, "new": version_data.change_type}
        version.change_type = version_data.change_type

    if version_data.change_description is not None:
        changes["change_description"] = {
            "old": version.change_description, "new": version_data.change_description}
        version.change_description = version_data.change_description

    if version_data.production_date is not None:
        changes["production_date"] = {
            "old": str(version.production_date) if version.production_date else None,
            "new": str(version_data.production_date)
        }
        version.production_date = version_data.production_date

    # Audit log
    if changes:
        create_audit_log(
            db=db,
            entity_type="ModelVersion",
            entity_id=version.version_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes
        )

    db.commit()
    db.refresh(version)

    return version


@router.get("/models/{model_id}/regional-versions")
def get_regional_versions(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get version deployment status by region for a model.
    Shows which version is currently deployed in each region.
    """
    from app.core.rls import can_access_model
    from app.models.region import Region
    from app.models.model_region import ModelRegion

    # Check RLS access
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Get model
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Get the latest ACTIVE global version (if any)
    global_version = db.query(ModelVersion).filter(
        ModelVersion.model_id == model_id,
        ModelVersion.status == VersionStatus.ACTIVE,
        ModelVersion.scope == "GLOBAL"
    ).order_by(desc(ModelVersion.created_at)).first()

    # Get all model-region links with their versions
    model_regions = db.query(ModelRegion).join(
        Region
    ).filter(
        ModelRegion.model_id == model_id
    ).options(
        joinedload(ModelRegion.region),
        joinedload(ModelRegion.version)
    ).all()

    regional_versions = []
    for mr in model_regions:
        # Get the current version for this region (either regional specific or global)
        current_version = mr.version if mr.version_id else global_version

        is_same_as_global = False
        if current_version and global_version:
            is_same_as_global = current_version.version_id == global_version.version_id

        regional_versions.append({
            "region_id": mr.region.region_id,
            "region_code": mr.region.code,
            "region_name": mr.region.name,
            "current_version_id": current_version.version_id if current_version else None,
            "version_number": current_version.version_number if current_version else None,
            "version_status": current_version.status if current_version else None,
            "deployed_at": mr.deployed_at,
            "deployment_notes": mr.deployment_notes,
            "is_same_as_global": is_same_as_global,
            # True if region has specific version
            "is_regional_override": mr.version_id is not None
        })

    return {
        "model_id": model_id,
        "model_name": model.model_name,
        "global_version": {
            "version_id": global_version.version_id if global_version else None,
            "version_number": global_version.version_number if global_version else None,
            "status": global_version.status if global_version else None,
            "planned_production_date": global_version.planned_production_date if global_version else None,
            "actual_production_date": global_version.actual_production_date if global_version else None
        } if global_version else None,
        "regional_versions": regional_versions
    }
