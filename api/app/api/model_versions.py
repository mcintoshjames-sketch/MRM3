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
from app.models.user import User
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.model_delegate import ModelDelegate
from app.models.audit_log import AuditLog
from app.models.model_change_taxonomy import ModelChangeType, ModelChangeCategory
from app.models.validation import ValidationRequest, ValidationWorkflowSLA
from app.models.taxonomy import TaxonomyValue
from app.schemas.model_version import (
    ModelVersionCreate,
    ModelVersionUpdate,
    ModelVersionResponse,
    VersionStatus,
)

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
    if user.role == "Admin":
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

    # Create version with regional scope support
    new_version = ModelVersion(
        model_id=model_id,
        version_number=version_number,
        change_type=version_data.change_type,
        change_type_id=version_data.change_type_id,
        change_description=version_data.change_description,
        scope=version_data.scope,
        affected_region_ids=version_data.affected_region_ids,
        planned_production_date=version_data.planned_production_date or version_data.production_date,
        actual_production_date=version_data.actual_production_date,
        production_date=version_data.production_date or version_data.planned_production_date,  # Legacy field
        created_by_id=current_user.user_id,
        status=VersionStatus.DRAFT
    )

    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    # Auto-create validation request for MAJOR changes (requires MV approval)
    validation_request = None
    validation_warning = None
    validation_type_code = None

    # Determine production date (prefer planned_production_date)
    target_production_date = version_data.planned_production_date or version_data.production_date

    # Check lead time policy for ALL changes if production date is provided
    if target_production_date:
        from app.models.validation import ValidationPolicy

        # Calculate lead time based on submission date (today) vs implementation date
        days_lead_time = (target_production_date - date.today()).days

        # Get model-specific lead time from validation policy
        lead_time_required = 90  # Default
        if model.risk_tier_id:
            policy = db.query(ValidationPolicy).filter(
                ValidationPolicy.risk_tier_id == model.risk_tier_id
            ).first()
            if policy:
                lead_time_required = policy.model_change_lead_time_days

        if days_lead_time < lead_time_required:
            msg = f"Request submitted with insufficient lead time. Policy requires {lead_time_required} days lead time before implementation, but only {max(0, days_lead_time)} days remain."
            validation_warning = "WARNING: " + msg

    if version_data.change_type == "MAJOR":
        from datetime import timedelta

        # Get ValidationWorkflowSLA configuration
        sla_config = db.query(ValidationWorkflowSLA).first()
        if not sla_config:
            # Create default SLA if doesn't exist
            sla_config = ValidationWorkflowSLA()
            db.add(sla_config)
            db.commit()
            db.refresh(sla_config)

        # Calculate total SLA time
        total_sla_days = (
            sla_config.assignment_days +
            sla_config.begin_work_days +
            sla_config.complete_work_days +
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
                msg = f"WARNING: Production date ({target_production_date}) is within {days_until_production} days. " \
                    f"Standard validation SLA is {total_sla_days} days. Expedited INTERIM review required."

                if validation_warning:
                    validation_warning += " " + msg
                else:
                    validation_warning = msg        # Get validation type from taxonomy
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
                    TaxonomyValue.taxonomy.has(name="Validation Request Status")
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
                if version_data.scope == "REGIONAL" and version_data.affected_region_ids:
                    # Import Region model
                    from app.models.region import Region

                    # Fetch and add affected regions
                    regions = db.query(Region).filter(
                        Region.region_id.in_(version_data.affected_region_ids)
                    ).all()

                    validation_request.regions = regions

                db.commit()
                db.refresh(validation_request)

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

    # Create response with validation info
    response_dict = {
        **new_version.__dict__,
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
        joinedload(ModelVersion.created_by)
    ).filter(
        ModelVersion.model_id == model_id
    ).order_by(desc(ModelVersion.created_at)).all()

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
    if current_user.role not in ["Validator", "Admin"]:
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
        joinedload(ModelVersion.created_by)
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
        joinedload(ModelVersion.model)
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
        # Nested/populated fields
        "created_by_name": version.created_by.full_name if version.created_by else None,
        "change_type_name": version.change_type_detail.name if version.change_type_detail else None,
        "change_category_name": version.change_type_detail.category.name if version.change_type_detail and version.change_type_detail.category else None,
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
        if current_user.role not in ["Validator", "Admin"]:
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
            "is_regional_override": mr.version_id is not None  # True if region has specific version
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
