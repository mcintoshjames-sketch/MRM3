"""Models routes."""
import csv
import io
import json
from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.time import utc_now
from app.core.deps import get_current_user
from app.models.user import User
from app.models.model import Model
from app.models.vendor import Vendor
from app.models.audit_log import AuditLog
from app.models.taxonomy import TaxonomyValue
from app.models.model_version import ModelVersion
from app.models.model_region import ModelRegion
from app.models.validation_grouping import ValidationGroupingMemory
from app.models.model_hierarchy import ModelHierarchy
from app.models.monitoring import MonitoringCycle, MonitoringCycleApproval, MonitoringPlan, monitoring_plan_models
from app.schemas.model import (
    ModelCreate, ModelUpdate, ModelDetailResponse, ValidationGroupingSuggestion, ModelCreateResponse,
    ModelNameHistoryItem, ModelNameHistoryResponse, NameChangeStatistics
)
from app.schemas.submission_action import SubmissionAction, SubmissionFeedback, SubmissionCommentCreate
from app.schemas.activity_timeline import ActivityTimelineItem, ActivityTimelineResponse
from app.models.model_name_history import ModelNameHistory

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
    # Note: commit happens with the main transaction


@router.get("/", response_model=List[ModelDetailResponse])
def list_models(
    exclude_sub_models: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List models with details.

    Row-Level Security:
    - Admin, Validator, Global Approver, Regional Approver: See all models
    - User: Only see models where they are owner, developer, or delegate

    Query Parameters:
    - exclude_sub_models: If True, exclude models that are sub-models (children) in hierarchy
    """
    from app.core.rls import apply_model_rls

    query = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories),
        joinedload(Model.model_regions).joinedload(ModelRegion.region),
        joinedload(Model.submitted_by_user),
        joinedload(Model.wholly_owned_region),  # For regional ownership models
        # For ownership taxonomy classification
        joinedload(Model.ownership_type)
        # Note: submission_comments intentionally excluded from list view for performance
        # They are only loaded in the detail endpoint where they're actually displayed
    )

    # Apply row-level security filtering
    query = apply_model_rls(query, current_user, db)

    models = query.all()

    # Filter out sub-models if requested
    if exclude_sub_models:
        # Get all model IDs that are children in active hierarchy relationships
        from sqlalchemy import func
        sub_model_ids = db.query(ModelHierarchy.child_model_id).filter(
            (ModelHierarchy.end_date == None) | (
                ModelHierarchy.end_date >= func.current_date())
        ).distinct().all()
        sub_model_ids = [row[0] for row in sub_model_ids]

        # Filter out sub-models from results
        models = [m for m in models if m.model_id not in sub_model_ids]

    return models


@router.post("/", response_model=ModelCreateResponse, status_code=status.HTTP_201_CREATED)
def create_model(
    model_data: ModelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new model."""
    # Check if user is Admin
    is_admin = current_user.role == "Admin"

    # Non-Admin users must include themselves as owner, developer, or model user
    if not is_admin:
        user_ids = model_data.user_ids or []
        is_owner = model_data.owner_id == current_user.user_id
        is_developer = model_data.developer_id == current_user.user_id
        is_model_user = current_user.user_id in user_ids

        if not (is_owner or is_developer or is_model_user):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must include yourself as the Owner, Developer, or a Model User when creating a model."
            )

    # Validate vendor requirement for third-party models
    if model_data.development_type == "Third-Party" and not model_data.vendor_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor is required for third-party models"
        )

    # Validate vendor exists if provided
    if model_data.vendor_id:
        vendor = db.query(Vendor).filter(
            Vendor.vendor_id == model_data.vendor_id).first()
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )

    # Validate owner exists
    owner = db.query(User).filter(User.user_id == model_data.owner_id).first()
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner user not found"
        )

    # Validate developer exists if provided
    if model_data.developer_id:
        developer = db.query(User).filter(
            User.user_id == model_data.developer_id).first()
        if not developer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Developer user not found"
            )

    # Extract user_ids, regulatory_category_ids, region_ids, initial_version_number, initial_implementation_date, and validation request fields before creating model
    user_ids = model_data.user_ids or []
    regulatory_category_ids = model_data.regulatory_category_ids or []
    region_ids = model_data.region_ids or []
    initial_version_number = model_data.initial_version_number or "1.0"
    initial_implementation_date = model_data.initial_implementation_date
    auto_create_validation = model_data.auto_create_validation
    validation_request_data = {
        'type_id': model_data.validation_request_type_id,
        'priority_id': model_data.validation_request_priority_id,
        'target_date': model_data.validation_request_target_date,
        'trigger_reason': model_data.validation_request_trigger_reason
    }
    model_dict = model_data.model_dump(exclude={
        'user_ids', 'regulatory_category_ids', 'region_ids',
        'initial_version_number', 'initial_implementation_date',
        'auto_create_validation', 'validation_request_type_id',
        'validation_request_priority_id', 'validation_request_target_date',
        'validation_request_trigger_reason'
    })

    model = Model(**model_dict)

    # Set row approval status for non-Admin users
    if not is_admin:
        model.row_approval_status = "pending"
        model.submitted_by_user_id = current_user.user_id
        model.submitted_at = utc_now()

    # Add model users
    if user_ids:
        users = db.query(User).filter(User.user_id.in_(user_ids)).all()
        if len(users) != len(user_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more model users not found"
            )
        model.users = users

    # Add regulatory categories
    if regulatory_category_ids:
        categories = db.query(TaxonomyValue).filter(
            TaxonomyValue.value_id.in_(regulatory_category_ids)).all()
        if len(categories) != len(regulatory_category_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more regulatory categories not found"
            )
        model.regulatory_categories = categories

    db.add(model)
    db.commit()
    db.refresh(model)

    # Add deployment regions
    # Combine wholly-owned region and additional regions, removing duplicates
    all_region_ids = set(region_ids)
    if model.wholly_owned_region_id is not None:
        all_region_ids.add(model.wholly_owned_region_id)

    if all_region_ids:
        # Validate all regions exist
        from app.models import Region
        regions = db.query(Region).filter(
            Region.region_id.in_(all_region_ids)).all()
        if len(regions) != len(all_region_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more regions not found"
            )

        # Create ModelRegion entries
        for region_id in all_region_ids:
            new_model_region = ModelRegion(
                model_id=model.model_id,
                region_id=region_id,
                created_at=utc_now()
            )
            db.add(new_model_region)
        db.commit()

    # Create initial version with change_type_id = 1 (New Model Development)
    # Use custom version number if provided, otherwise default to "1.0"
    # Use implementation date if provided, otherwise DRAFT status with no date
    version_status = "ACTIVE" if initial_implementation_date else "DRAFT"
    initial_version = ModelVersion(
        model_id=model.model_id,
        version_number=initial_version_number,
        change_type="MAJOR",  # New models are MAJOR changes
        change_type_id=1,  # Code 1 = "New Model Development"
        change_description="Initial model version",
        created_by_id=current_user.user_id,
        production_date=initial_implementation_date,
        status=version_status
    )
    db.add(initial_version)
    db.commit()
    db.refresh(initial_version)

    # Audit log for model creation
    create_audit_log(
        db=db,
        entity_type="Model",
        entity_id=model.model_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={"model_name": model.model_name, "status": model.status,
                 "development_type": model.development_type}
    )

    # Audit log for initial version
    create_audit_log(
        db=db,
        entity_type="ModelVersion",
        entity_id=initial_version.version_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={"version_number": initial_version_number,
                 "change_type_id": 1, "auto_created": True}
    )

    # Create initial submission comment for non-Admin users
    if not is_admin:
        from app.models import ModelSubmissionComment
        initial_comment = ModelSubmissionComment(
            model_id=model.model_id,
            user_id=current_user.user_id,
            comment_text=f"Model '{model.model_name}' submitted for admin approval.",
            action_taken="submitted",
            created_at=utc_now()
        )
        db.add(initial_comment)

    db.commit()

    # Validate implementation date vs validation timing
    warnings = []
    if auto_create_validation and initial_implementation_date:
        # Get validation type to check if it's Interim Review
        from app.models import TaxonomyValue
        validation_type = db.query(TaxonomyValue).filter(
            TaxonomyValue.value_id == validation_request_data['type_id']
        ).first()
        is_interim = validation_type and (
            'interim' in validation_type.label.lower() or validation_type.code == 'INTERIM')

        # Check if implementation date is before validation target completion date
        if validation_request_data['target_date']:
            target_date = validation_request_data['target_date']
            if initial_implementation_date < target_date:
                if not is_interim:
                    warnings.append({
                        'type': 'IMPLEMENTATION_BEFORE_VALIDATION',
                        'message': f"Implementation date ({initial_implementation_date}) is before validation target completion date ({target_date}). Consider: (1) using 'Interim Review' validation type for faster approval, (2) setting an earlier validation target date, or (3) delaying implementation to {target_date} or later."
                    })

        # Check if implementation date is within policy lead time
        if model.risk_tier_id:
            from app.models import ValidationPolicy
            policy = db.query(ValidationPolicy).filter(
                ValidationPolicy.risk_tier_id == model.risk_tier_id
            ).first()

            if policy:
                lead_time_days = policy.model_change_lead_time_days
                days_until_implementation = (
                    initial_implementation_date - date.today()).days

                if days_until_implementation < lead_time_days:
                    # Warn if not using Interim Review
                    if not is_interim:
                        suggested_impl_date = date.today() + timedelta(days=lead_time_days)
                        warnings.append({
                            'type': 'LEAD_TIME_WARNING',
                            'message': f"Implementation date is only {days_until_implementation} days away, but policy requires {lead_time_days} days lead time for this risk tier. Consider using 'Interim Review' validation type or delaying implementation to {suggested_impl_date.isoformat()}."
                        })

    # Auto-create validation request if requested
    if auto_create_validation and validation_request_data['type_id'] and validation_request_data['priority_id']:
        from app.models import ValidationRequest, ValidationRequestModelVersion, TaxonomyValue, Taxonomy
        # datetime is already imported at module level

        # Get INTAKE status
        intake_status = db.query(TaxonomyValue).join(Taxonomy).filter(
            Taxonomy.name == "Validation Request Status",
            TaxonomyValue.code == "INTAKE"
        ).first()

        if intake_status:
            # Create validation request
            validation_request = ValidationRequest(
                request_date=date.today(),
                requestor_id=current_user.user_id,
                validation_type_id=validation_request_data['type_id'],
                priority_id=validation_request_data['priority_id'],
                target_completion_date=validation_request_data['target_date'],
                trigger_reason=validation_request_data['trigger_reason'] or "Auto-created with new model",
                current_status_id=intake_status.value_id,
                created_at=utc_now(),
                updated_at=utc_now()
            )
            db.add(validation_request)
            db.flush()

            # Associate model with validation request, including version if implementation date was set
            assoc = ValidationRequestModelVersion(
                request_id=validation_request.request_id,
                model_id=model.model_id,
                version_id=initial_version.version_id if initial_implementation_date else None
            )
            db.add(assoc)

            # Create initial status history entry
            from app.models import ValidationStatusHistory
            status_history = ValidationStatusHistory(
                request_id=validation_request.request_id,
                old_status_id=None,
                new_status_id=intake_status.value_id,
                changed_by_id=current_user.user_id,
                changed_at=utc_now(),
                change_reason="Auto-created with new model"
            )
            db.add(status_history)

            # Create audit log for validation request
            validation_audit = AuditLog(
                entity_type="ValidationRequest",
                entity_id=validation_request.request_id,
                action="CREATE",
                user_id=current_user.user_id,
                changes={
                    "model_id": model.model_id,
                    "model_name": model.model_name,
                    "auto_created": True
                },
                timestamp=utc_now()
            )
            db.add(validation_audit)
            db.commit()

    # Reload with relationships
    from app.models import ModelSubmissionComment
    model = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories),
        joinedload(Model.submitted_by_user),
        joinedload(Model.submission_comments).joinedload(
            ModelSubmissionComment.user)
    ).filter(Model.model_id == model.model_id).first()

    # Return model with warnings if any
    # Convert model to dict and add warnings
    from pydantic import TypeAdapter
    model_dict = ModelCreateResponse.model_validate(model).model_dump()
    if warnings:
        model_dict['warnings'] = warnings
    return model_dict


# ============================================================================
# Model Submission Approval Workflow Endpoints
# ============================================================================


@router.get("/name-changes/stats", response_model=NameChangeStatistics)
def get_name_change_statistics(
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics on model name changes.

    Query Parameters:
    - start_date: Filter changes on or after this date (YYYY-MM-DD)
    - end_date: Filter changes on or before this date (YYYY-MM-DD)

    Returns:
    - Total models with name changes (all time)
    - Models with name changes in last 90 days
    - Models with name changes in last 30 days
    - Total number of name changes
    - Recent name changes (filtered by date range if provided)
    """
    from sqlalchemy import func, distinct

    now = utc_now()
    ninety_days_ago = now - timedelta(days=90)
    thirty_days_ago = now - timedelta(days=30)

    # Total models that have ever had a name change
    total_models_with_changes = db.query(
        func.count(distinct(ModelNameHistory.model_id))
    ).scalar() or 0

    # Models with name changes in last 90 days
    models_changed_90 = db.query(
        func.count(distinct(ModelNameHistory.model_id))
    ).filter(
        ModelNameHistory.changed_at >= ninety_days_ago
    ).scalar() or 0

    # Models with name changes in last 30 days
    models_changed_30 = db.query(
        func.count(distinct(ModelNameHistory.model_id))
    ).filter(
        ModelNameHistory.changed_at >= thirty_days_ago
    ).scalar() or 0

    # Total name changes
    total_changes = db.query(func.count(
        ModelNameHistory.history_id)).scalar() or 0

    # Build query for recent changes with optional date filtering
    changes_query = db.query(ModelNameHistory).options(
        joinedload(ModelNameHistory.changed_by)
    )

    if start_date:
        changes_query = changes_query.filter(
            ModelNameHistory.changed_at >= datetime.combine(
                start_date, datetime.min.time())
        )
    if end_date:
        changes_query = changes_query.filter(
            ModelNameHistory.changed_at <= datetime.combine(
                end_date, datetime.max.time())
        )

    recent = changes_query.order_by(
        ModelNameHistory.changed_at.desc()).limit(100).all()

    recent_changes = [
        ModelNameHistoryItem(
            history_id=h.history_id,
            model_id=h.model_id,
            old_name=h.old_name,
            new_name=h.new_name,
            changed_by_id=h.changed_by_id,
            changed_by_name=h.changed_by.full_name if h.changed_by else None,
            changed_at=h.changed_at,
            change_reason=h.change_reason
        )
        for h in recent
    ]

    return NameChangeStatistics(
        total_models_with_changes=total_models_with_changes,
        models_changed_last_90_days=models_changed_90,
        models_changed_last_30_days=models_changed_30,
        total_name_changes=total_changes,
        recent_changes=recent_changes
    )


@router.get("/pending-submissions", response_model=List[ModelDetailResponse])
def get_pending_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all models pending admin approval.

    Admin only. Returns models with row_approval_status IN ('pending', 'needs_revision').
    """
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view pending submissions"
        )

    from app.models import ModelSubmissionComment
    models = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.submitted_by_user),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories),
        joinedload(Model.model_regions).joinedload(ModelRegion.region),
        joinedload(Model.submission_comments).joinedload(
            ModelSubmissionComment.user)
    ).filter(
        Model.row_approval_status.in_(['pending', 'needs_revision'])
    ).order_by(Model.submitted_at.desc()).all()

    return models


@router.get("/my-submissions", response_model=List[ModelDetailResponse])
def get_my_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's model submissions (pending/needs_revision/rejected).

    Non-Admin users can see their own submissions.
    """
    from app.models import ModelSubmissionComment
    models = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.submitted_by_user),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories),
        joinedload(Model.model_regions).joinedload(ModelRegion.region),
        joinedload(Model.submission_comments).joinedload(
            ModelSubmissionComment.user)
    ).filter(
        Model.submitted_by_user_id == current_user.user_id,
        Model.row_approval_status != None  # Not approved yet
    ).order_by(Model.submitted_at.desc()).all()

    return models


@router.get("/{model_id}", response_model=ModelDetailResponse)
def get_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific model with details.

    Row-Level Security:
    - Admin, Validator, Global Approver, Regional Approver: Can access any model
    - User: Can only access models where they are owner, developer, or delegate
    """
    from app.core.rls import can_access_model

    # Check RLS access
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    model = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.wholly_owned_region),
        joinedload(Model.regulatory_categories)
    ).filter(Model.model_id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )
    return model


@router.get("/{model_id}/revalidation-status")
def get_model_revalidation_status(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get revalidation status for a specific model.

    Row-Level Security:
    - Admin, Validator, Global Approver, Regional Approver: Can access any model's status
    - User: Can only access status for models they have access to
    """
    from app.api.validation_workflow import calculate_model_revalidation_status
    from app.core.rls import can_access_model

    # Check RLS access
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    model = db.query(Model).filter(Model.model_id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    return calculate_model_revalidation_status(model, db)


@router.get("/{model_id}/validation-suggestions", response_model=ValidationGroupingSuggestion)
def get_validation_grouping_suggestions(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get suggested models for validation based on previous groupings.

    Returns models that were previously validated together with this model
    in the most recent regular validation (Comprehensive, etc.).
    Targeted validations are excluded from suggestions.

    Row-Level Security:
    - Admin, Validator, Global Approver, Regional Approver: Can access any model's suggestions
    - User: Can only access suggestions for models they have access to
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

    # Look up grouping memory
    grouping_memory = db.query(ValidationGroupingMemory).filter(
        ValidationGroupingMemory.model_id == model_id
    ).first()

    # If no grouping memory, return empty suggestion
    if not grouping_memory:
        return ValidationGroupingSuggestion(
            suggested_model_ids=[],
            suggested_models=[],
            last_validation_request_id=None,
            last_grouped_at=None
        )

    # Parse grouped model IDs from JSON
    try:
        grouped_model_ids = json.loads(grouping_memory.grouped_model_ids)
    except (json.JSONDecodeError, TypeError):
        # If JSON is invalid, return empty suggestion
        return ValidationGroupingSuggestion(
            suggested_model_ids=[],
            suggested_models=[],
            last_validation_request_id=grouping_memory.last_validation_request_id,
            last_grouped_at=grouping_memory.updated_at
        )

    # Fetch the suggested models with full details
    suggested_models = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories)
    ).filter(Model.model_id.in_(grouped_model_ids)).all()

    return ValidationGroupingSuggestion(
        suggested_model_ids=grouped_model_ids,
        suggested_models=suggested_models,
        last_validation_request_id=grouping_memory.last_validation_request_id,
        last_grouped_at=grouping_memory.updated_at
    )


@router.patch("/{model_id}")
def update_model(
    model_id: int,
    model_data: ModelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a model.

    For approved models edited by non-admins, changes are held for admin approval.
    Returns 202 Accepted with pending edit details in that case.

    Row-Level Security:
    - Admin: Can update any model directly
    - Owner/Developer/Delegate: Can update pending/needs_revision models directly;
      for approved models, changes are held for admin approval
    """
    from app.core.rls import can_access_model, can_modify_model
    from app.models.model_pending_edit import ModelPendingEdit
    from app.schemas.model import ModelUpdateWithPendingResponse
    from datetime import datetime, UTC

    # Check RLS access first (can user see this model?)
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    is_admin = current_user.role == "Admin"

    # For non-admins editing APPROVED models, create a pending edit instead
    if not is_admin and model.row_approval_status is None:
        update_data = model_data.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No changes provided"
            )

        # Capture original values for the fields being changed
        original_values = {}
        for field in update_data.keys():
            if field == 'user_ids':
                original_values[field] = [u.user_id for u in model.users]
            elif field == 'regulatory_category_ids':
                original_values[field] = [c.value_id for c in model.regulatory_categories]
            else:
                original_values[field] = getattr(model, field, None)

        # Create pending edit record
        pending_edit = ModelPendingEdit(
            model_id=model_id,
            requested_by_id=current_user.user_id,
            requested_at=datetime.now(UTC),
            proposed_changes=update_data,
            original_values=original_values,
            status="pending"
        )
        db.add(pending_edit)

        # Create audit log for pending edit creation
        create_audit_log(
            db=db,
            entity_type="ModelPendingEdit",
            entity_id=model_id,
            action="CREATE",
            user_id=current_user.user_id,
            changes={"proposed_changes": update_data, "model_name": model.model_name}
        )

        db.commit()
        db.refresh(pending_edit)

        # Return 202 Accepted with pending edit info
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "message": "Your changes have been submitted for admin approval.",
                "pending_edit_id": pending_edit.pending_edit_id,
                "status": "pending",
                "proposed_changes": update_data,
                "model_id": model_id
            }
        )

    # For admins or non-approved models, check standard modification rights
    if not can_modify_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this model"
        )

    update_data = model_data.model_dump(exclude_unset=True)

    # Handle development_type and vendor_id together
    new_dev_type = update_data.get('development_type', model.development_type)
    new_vendor_id = update_data.get('vendor_id', model.vendor_id)

    if new_dev_type == "Third-Party" and new_vendor_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor is required for third-party models"
        )

    # Validate vendor exists if provided
    if 'vendor_id' in update_data and update_data['vendor_id'] is not None:
        vendor = db.query(Vendor).filter(Vendor.vendor_id ==
                                         update_data['vendor_id']).first()
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found"
            )

    # Validate owner exists if provided
    if 'owner_id' in update_data:
        owner = db.query(User).filter(
            User.user_id == update_data['owner_id']).first()
        if not owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Owner user not found"
            )

    # Validate developer exists if provided
    if 'developer_id' in update_data and update_data['developer_id'] is not None:
        developer = db.query(User).filter(
            User.user_id == update_data['developer_id']).first()
        if not developer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Developer user not found"
            )

    # Handle user_ids separately
    user_ids_changed = False
    if 'user_ids' in update_data:
        user_ids = update_data.pop('user_ids')
        if user_ids is not None:
            users = db.query(User).filter(User.user_id.in_(user_ids)).all()
            if len(users) != len(user_ids):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or more model users not found"
                )
            model.users = users
            user_ids_changed = True

    # Handle regulatory_category_ids separately
    regulatory_categories_changed = False
    if 'regulatory_category_ids' in update_data:
        category_ids = update_data.pop('regulatory_category_ids')
        if category_ids is not None:
            categories = db.query(TaxonomyValue).filter(
                TaxonomyValue.value_id.in_(category_ids)).all()
            if len(categories) != len(category_ids):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or more regulatory categories not found"
                )
            model.regulatory_categories = categories
            regulatory_categories_changed = True

    # Track changes for audit log
    changes_made = {}
    risk_tier_changed = False
    old_risk_tier_id = model.risk_tier_id

    # Track name change specifically for history
    old_model_name = model.model_name
    name_changed = False

    for field, value in update_data.items():
        old_value = getattr(model, field, None)
        if old_value != value:
            changes_made[field] = {"old": old_value, "new": value}
            if field == "risk_tier_id":
                risk_tier_changed = True
            if field == "model_name":
                name_changed = True
        setattr(model, field, value)

    if user_ids_changed:
        changes_made["user_ids"] = "modified"

    if regulatory_categories_changed:
        changes_made["regulatory_category_ids"] = "modified"

    # Auto-sync deployment regions when wholly_owned_region_id changes
    if 'wholly_owned_region_id' in update_data and update_data['wholly_owned_region_id'] is not None:
        new_region_id = update_data['wholly_owned_region_id']

        # Check if this region already exists in deployment regions
        existing_region = db.query(ModelRegion).filter(
            ModelRegion.model_id == model_id,
            ModelRegion.region_id == new_region_id
        ).first()

        # If not, add it
        if not existing_region:
            new_model_region = ModelRegion(
                model_id=model_id,
                region_id=new_region_id,
                created_at=utc_now()
            )
            db.add(new_model_region)
            changes_made["auto_added_deployment_region"] = new_region_id

    # Audit log for model update
    if changes_made:
        create_audit_log(
            db=db,
            entity_type="Model",
            entity_id=model_id,
            action="UPDATE",
            user_id=current_user.user_id,
            changes=changes_made
        )

    # Create name history record if name changed
    if name_changed:
        name_history = ModelNameHistory(
            model_id=model_id,
            old_name=old_model_name,
            new_name=model.model_name,
            changed_by_id=current_user.user_id,
            changed_at=utc_now()
        )
        db.add(name_history)

    db.commit()
    db.refresh(model)

    # Force reset validation plans if risk tier changed (voids approvals, regenerates components)
    if risk_tier_changed:
        from app.api.validation_workflow import reset_validation_plan_for_tier_change
        new_tier_id = model.risk_tier_id  # Could be None if tier was cleared
        reset_result = reset_validation_plan_for_tier_change(
            db=db,
            model_id=model_id,
            new_tier_id=new_tier_id,
            user_id=current_user.user_id,
            force=True
        )
        if reset_result["reset_count"] > 0:
            changes_made["validation_plans_reset"] = reset_result["reset_count"]
            changes_made["approvals_voided"] = reset_result["approvals_voided"]
            db.commit()  # Commit the reset changes

    # Reload with relationships
    from app.models import ModelSubmissionComment
    model = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories),
        joinedload(Model.submitted_by_user),
        joinedload(Model.submission_comments).joinedload(
            ModelSubmissionComment.user)
    ).filter(Model.model_id == model.model_id).first()

    return model


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a model.

    Row-Level Security:
    - Admin: Can delete any model
    - Owner: Can delete their models
    - Developer: Can delete models they develop
    - Delegate with can_submit_changes: Can delete delegated models
    """
    from app.core.rls import can_access_model, can_modify_model

    # Check RLS access first (can user see this model?)
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Check modification rights
    if not can_modify_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this model"
        )

    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Audit log for model deletion (before delete)
    model_name = model.model_name
    create_audit_log(
        db=db,
        entity_type="Model",
        entity_id=model_id,
        action="DELETE",
        user_id=current_user.user_id,
        changes={"model_name": model_name}
    )

    db.delete(model)
    db.commit()
    return None


@router.get("/export/csv")
def export_models_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export models to CSV.

    Row-Level Security:
    - Admin, Validator, Global Approver, Regional Approver: Export all models
    - User: Export only models where they are owner, developer, or delegate
    """
    from app.core.rls import apply_model_rls

    query = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.users),
        joinedload(Model.regulatory_categories)
    )

    # Apply row-level security filtering
    query = apply_model_rls(query, current_user, db)
    models = query.all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "Model ID",
        "Model Name",
        "Description",
        "Development Type",
        "Model Type",
        "Status",
        "Owner",
        "Owner Email",
        "Developer",
        "Developer Email",
        "Vendor",
        "Risk Tier",
        "Validation Type",
        "Regulatory Categories",
        "Model Users",
        "Created At",
        "Updated At"
    ])

    # Write data rows
    for model in models:
        # Format model users as comma-separated list
        model_users_str = ", ".join(
            [u.full_name for u in model.users]) if model.users else ""
        # Format regulatory categories as comma-separated list
        reg_categories_str = ", ".join(
            [c.label for c in model.regulatory_categories]) if model.regulatory_categories else ""

        writer.writerow([
            model.model_id,
            model.model_name,
            model.description or "",
            model.development_type,
            model.model_type.label if model.model_type else "",
            model.status,
            model.owner.full_name if model.owner else "",
            model.owner.email if model.owner else "",
            model.developer.full_name if model.developer else "",
            model.developer.email if model.developer else "",
            model.vendor.name if model.vendor else "",
            model.risk_tier.label if model.risk_tier else "",
            model.validation_type.label if model.validation_type else "",
            reg_categories_str,
            model_users_str,
            model.created_at.isoformat() if model.created_at else "",
            model.updated_at.isoformat() if model.updated_at else ""
        ])

    # Reset stream position
    output.seek(0)

    # Return as streaming response
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=models_export.csv"
        }
    )


@router.get("/{model_id}/submission-thread")
def get_submission_thread(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get submission comment thread for a model."""
    from app.core.rls import can_access_model
    from app.models import ModelSubmissionComment
    from app.schemas.model_submission_comment import ModelSubmissionCommentResponse

    # Check access
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Get comments
    comments = db.query(ModelSubmissionComment).options(
        joinedload(ModelSubmissionComment.user)
    ).filter(
        ModelSubmissionComment.model_id == model_id
    ).order_by(ModelSubmissionComment.created_at.asc()).all()

    return [ModelSubmissionCommentResponse.model_validate(c) for c in comments]


@router.post("/{model_id}/comments")
def add_submission_comment(
    model_id: int,
    comment_data: SubmissionCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a comment to the submission thread."""
    from app.core.rls import can_access_model
    from app.models import ModelSubmissionComment

    # Check access
    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    model = db.query(Model).filter(Model.model_id == model_id).first()

    # Only allow comments on pending/needs_revision models
    if model.row_approval_status not in ('pending', 'needs_revision'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only comment on pending or needs_revision models"
        )

    comment = ModelSubmissionComment(
        model_id=model_id,
        user_id=current_user.user_id,
        comment_text=comment_data.comment_text,
        action_taken=None,
        created_at=utc_now()
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {"message": "Comment added", "comment_id": comment.comment_id}


@router.post("/{model_id}/approve", response_model=ModelDetailResponse)
def approve_model_submission(
    model_id: int,
    action: SubmissionAction,
    create_validation: bool = False,
    validation_type_id: int | None = None,
    validation_priority_id: int | None = None,
    validation_target_date: str | None = None,
    validation_trigger_reason: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve a model submission (Admin only).

    Optionally creates a validation request for the approved model.
    """
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can approve models"
        )

    model = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories),
        joinedload(Model.submitted_by_user),
        joinedload(Model.submission_comments)
    ).filter(Model.model_id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    if model.row_approval_status not in ('pending', 'needs_revision'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model is not pending approval"
        )

    # Approve the model
    model.row_approval_status = None

    # Add approval comment
    from app.models import ModelSubmissionComment
    comment_text = action.comment or f"Model approved by {current_user.full_name} and added to inventory."
    approval_comment = ModelSubmissionComment(
        model_id=model_id,
        user_id=current_user.user_id,
        comment_text=comment_text,
        action_taken="approved",
        created_at=utc_now()
    )
    db.add(approval_comment)

    # Audit log
    create_audit_log(
        db=db,
        entity_type="Model",
        entity_id=model_id,
        action="APPROVE",
        user_id=current_user.user_id,
        changes={"row_approval_status": "approved",
                 "approved_by": current_user.full_name}
    )

    db.commit()

    # Optionally create validation request
    if create_validation and validation_type_id and validation_priority_id:
        from app.models import ValidationRequest, ValidationRequestModelVersion, Taxonomy

        # Get INTAKE status
        intake_status = db.query(TaxonomyValue).join(Taxonomy).filter(
            Taxonomy.name == "Validation Request Status",
            TaxonomyValue.code == "INTAKE"
        ).first()

        if not intake_status:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="INTAKE status not found in taxonomy"
            )

        # Get current version
        current_version = db.query(ModelVersion).filter(
            ModelVersion.model_id == model_id,
            ModelVersion.status == "ACTIVE"
        ).order_by(ModelVersion.created_at.desc()).first()

        if not current_version:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active model version found"
            )

        # Create validation request
        validation_request = ValidationRequest(
            request_date=date.today(),
            type_id=validation_type_id,
            priority_id=validation_priority_id,
            status_id=intake_status.value_id,
            target_completion_date=date.fromisoformat(
                validation_target_date) if validation_target_date else None,
            trigger_reason=validation_trigger_reason or f"Initial validation for approved model {model.model_name}",
            created_by_id=current_user.user_id
        )
        db.add(validation_request)
        db.commit()
        db.refresh(validation_request)

        # Link model version
        link = ValidationRequestModelVersion(
            request_id=validation_request.request_id,
            model_id=model_id,
            version_id=current_version.version_id
        )
        db.add(link)
        db.commit()

    # Reload model to ensure all relationships are populated for response
    db.refresh(model)
    return model


@router.post("/{model_id}/send-back", response_model=ModelDetailResponse)
def send_back_model_submission(
    model_id: int,
    feedback: SubmissionFeedback,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a model submission back to submitter with feedback (Admin only)."""
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can send back models"
        )

    model = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories),
        joinedload(Model.submitted_by_user),
        joinedload(Model.submission_comments)
    ).filter(Model.model_id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    if model.row_approval_status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only send back pending models"
        )

    # Change status to needs_revision
    model.row_approval_status = 'needs_revision'

    # Add feedback comment
    from app.models import ModelSubmissionComment
    feedback_comment = ModelSubmissionComment(
        model_id=model_id,
        user_id=current_user.user_id,
        comment_text=feedback.comment,
        action_taken="sent_back",
        created_at=utc_now()
    )
    db.add(feedback_comment)

    # Audit log
    create_audit_log(
        db=db,
        entity_type="Model",
        entity_id=model_id,
        action="SEND_BACK",
        user_id=current_user.user_id,
        changes={"row_approval_status": "needs_revision",
                 "feedback": feedback.comment}
    )

    db.commit()
    db.refresh(model)
    return model


@router.post("/{model_id}/resubmit", response_model=ModelDetailResponse)
def resubmit_model(
    model_id: int,
    action: SubmissionAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resubmit a model after addressing feedback (Submitter only)."""
    model = db.query(Model).options(
        joinedload(Model.owner),
        joinedload(Model.developer),
        joinedload(Model.vendor),
        joinedload(Model.users),
        joinedload(Model.risk_tier),
        joinedload(Model.validation_type),
        joinedload(Model.model_type),
        joinedload(Model.regulatory_categories),
        joinedload(Model.submitted_by_user),
        joinedload(Model.submission_comments)
    ).filter(Model.model_id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Only submitter can resubmit
    if model.submitted_by_user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the submitter can resubmit this model"
        )

    if model.row_approval_status != 'needs_revision':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only resubmit models that need revision"
        )

    # Change status back to pending
    model.row_approval_status = 'pending'

    # Add resubmission comment
    from app.models import ModelSubmissionComment
    note_text = action.comment or "Model resubmitted after addressing feedback."
    resubmit_comment = ModelSubmissionComment(
        model_id=model_id,
        user_id=current_user.user_id,
        comment_text=note_text,
        action_taken="resubmitted",
        created_at=utc_now()
    )
    db.add(resubmit_comment)

    # Audit log
    create_audit_log(
        db=db,
        entity_type="Model",
        entity_id=model_id,
        action="RESUBMIT",
        user_id=current_user.user_id,
        changes={"row_approval_status": "pending"}
    )

    db.commit()
    db.refresh(model)
    return model


@router.get("/{model_id}/activity-timeline", response_model=ActivityTimelineResponse)
def get_model_activity_timeline(
    model_id: int,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive activity timeline for a model.

    Includes:
    - Model created/updated (audit logs)
    - Versions created
    - Validation requests created/status changes
    - Validation approvals
    - Delegates added/removed
    - Comments added
    - Deployment tasks confirmed
    - Decommissioning requests/reviews/approvals
    - Monitoring cycles (created/submitted/completed/approvals)
    """
    from app.core.rls import can_access_model
    from app.models.model_delegate import ModelDelegate
    from app.models.model_submission_comment import ModelSubmissionComment
    from app.models.validation import ValidationRequest, ValidationStatusHistory, ValidationApproval
    from app.models.version_deployment_task import VersionDeploymentTask

    # Check model exists and user has access
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    if not can_access_model(model.model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this model"
        )

    activities = []

    # 1. Model audit logs (created, updated)
    model_audits = db.query(AuditLog).options(
        joinedload(AuditLog.user)
    ).filter(
        AuditLog.entity_type == "Model",
        AuditLog.entity_id == model_id
    ).all()

    for audit in model_audits:
        icon = "📝"
        title = f"Model {audit.action.lower()}"
        if audit.action == "CREATE":
            title = "Model created"
            icon = "✨"
        elif audit.action == "UPDATE":
            title = "Model updated"
            icon = "📝"
        elif audit.action == "SUBMIT":
            title = "Model submitted for approval"
            icon = "📤"
        elif audit.action == "APPROVE":
            title = "Model approved"
            icon = "✅"
        elif audit.action == "REJECT":
            title = "Model submission rejected"
            icon = "❌"
        elif audit.action == "RESUBMIT":
            title = "Model resubmitted"
            icon = "🔄"

        activities.append(ActivityTimelineItem(
            timestamp=audit.timestamp,
            activity_type=f"model_{audit.action.lower()}",
            title=title,
            description=None,
            user_name=audit.user.full_name if audit.user else None,
            user_id=audit.user_id,
            entity_type="Model",
            entity_id=model_id,
            icon=icon
        ))

    # 2. Model versions created
    versions = db.query(ModelVersion).options(
        joinedload(ModelVersion.created_by)
    ).filter(
        ModelVersion.model_id == model_id
    ).all()

    for version in versions:
        scope_text = f" ({version.scope})" if version.scope != "GLOBAL" else ""
        activities.append(ActivityTimelineItem(
            timestamp=version.created_at,
            activity_type="version_created",
            title=f"Version {version.version_number} created{scope_text}",
            description=version.change_description,
            user_name=version.created_by.full_name if version.created_by else None,
            user_id=version.created_by_id,
            entity_type="ModelVersion",
            entity_id=version.version_id,
            icon="🚀"
        ))

    # 3. Validation requests for this model
    validation_requests = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.requestor),
        joinedload(ValidationRequest.current_status)
    ).join(
        ValidationRequest.models
    ).filter(
        Model.model_id == model_id
    ).all()

    for req in validation_requests:
        activities.append(ActivityTimelineItem(
            timestamp=req.created_at,
            activity_type="validation_request_created",
            title=f"Validation request #{req.request_id} created",
            description=None,
            user_name=req.requestor.full_name if req.requestor else None,
            user_id=req.requestor_id,
            entity_type="ValidationRequest",
            entity_id=req.request_id,
            icon="🔍"
        ))

        # Get status history for this request
        status_history = db.query(ValidationStatusHistory).options(
            joinedload(ValidationStatusHistory.changed_by),
            joinedload(ValidationStatusHistory.new_status)
        ).filter(
            ValidationStatusHistory.request_id == req.request_id
        ).all()

        for history in status_history:
            activities.append(ActivityTimelineItem(
                timestamp=history.changed_at,
                activity_type="validation_status_change",
                title=f"Validation #{req.request_id} status changed to {history.new_status.label if history.new_status else 'Unknown'}",
                description=history.change_reason,
                user_name=history.changed_by.full_name if history.changed_by else None,
                user_id=history.changed_by_id,
                entity_type="ValidationRequest",
                entity_id=req.request_id,
                icon="🔄"
            ))

    # 4. Validation approvals
    approvals = db.query(ValidationApproval).options(
        joinedload(ValidationApproval.approver),
        joinedload(ValidationApproval.request)
    ).join(
        ValidationApproval.request
    ).join(
        ValidationRequest.models
    ).filter(
        Model.model_id == model_id,
        ValidationApproval.approved_at.isnot(None)
    ).all()

    for approval in approvals:
        status_icon = "✅" if approval.approval_status == "Approved" else "❌"
        activities.append(ActivityTimelineItem(
            timestamp=approval.approved_at,
            activity_type="validation_approval",
            title=f"Validation #{approval.request_id} {approval.approval_status.lower()}",
            description=approval.comments,
            user_name=approval.approver.full_name if approval.approver else None,
            user_id=approval.approver_id,
            entity_type="ValidationApproval",
            entity_id=approval.approval_id,
            icon=status_icon
        ))

    # 5. Delegates added/removed
    delegates = db.query(ModelDelegate).options(
        joinedload(ModelDelegate.user),
        joinedload(ModelDelegate.delegated_by),
        joinedload(ModelDelegate.revoked_by)
    ).filter(
        ModelDelegate.model_id == model_id
    ).all()

    for delegate in delegates:
        # Delegate added
        activities.append(ActivityTimelineItem(
            timestamp=delegate.delegated_at,
            activity_type="delegate_added",
            title=f"{delegate.user.full_name} added as delegate",
            description=None,
            user_name=delegate.delegated_by.full_name if delegate.delegated_by else None,
            user_id=delegate.delegated_by_id,
            entity_type="ModelDelegate",
            entity_id=delegate.delegate_id,
            icon="👤"
        ))

        # Delegate removed (if revoked)
        if delegate.revoked_at:
            activities.append(ActivityTimelineItem(
                timestamp=delegate.revoked_at,
                activity_type="delegate_removed",
                title=f"{delegate.user.full_name} removed as delegate",
                description=None,
                user_name=delegate.revoked_by.full_name if delegate.revoked_by else None,
                user_id=delegate.revoked_by_id,
                entity_type="ModelDelegate",
                entity_id=delegate.delegate_id,
                icon="👤"
            ))

    # 6. Submission comments
    comments = db.query(ModelSubmissionComment).options(
        joinedload(ModelSubmissionComment.user)
    ).filter(
        ModelSubmissionComment.model_id == model_id
    ).all()

    for comment in comments:
        activities.append(ActivityTimelineItem(
            timestamp=comment.created_at,
            activity_type="comment_added",
            title=f"Comment added by {comment.user.full_name if comment.user else 'Unknown'}",
            description=comment.comment_text[:100] + "..." if len(
                comment.comment_text) > 100 else comment.comment_text,
            user_name=comment.user.full_name if comment.user else None,
            user_id=comment.user_id,
            entity_type="ModelSubmissionComment",
            entity_id=comment.comment_id,
            icon="💬"
        ))

    # 7. Deployment tasks confirmed
    deployment_tasks = db.query(VersionDeploymentTask).options(
        joinedload(VersionDeploymentTask.version),
        joinedload(VersionDeploymentTask.confirmed_by),
        joinedload(VersionDeploymentTask.region)
    ).filter(
        VersionDeploymentTask.model_id == model_id,
        VersionDeploymentTask.confirmed_at.isnot(None)
    ).all()

    for task in deployment_tasks:
        region_text = f" to {task.region.name}" if task.region else ""
        activities.append(ActivityTimelineItem(
            timestamp=task.confirmed_at,
            activity_type="deployment_confirmed",
            title=f"Version {task.version.version_number} deployed{region_text}",
            description=task.confirmation_notes,
            user_name=task.confirmed_by.full_name if task.confirmed_by else None,
            user_id=task.confirmed_by_id,
            entity_type="VersionDeploymentTask",
            entity_id=task.task_id,
            icon="🚀"
        ))

    # 8. Decommissioning requests
    from app.models.decommissioning import DecommissioningRequest, DecommissioningStatusHistory, DecommissioningApproval

    decom_requests = db.query(DecommissioningRequest).options(
        joinedload(DecommissioningRequest.created_by),
        joinedload(DecommissioningRequest.reason),
        joinedload(DecommissioningRequest.validator_reviewed_by),
        joinedload(DecommissioningRequest.owner_reviewed_by),
        joinedload(DecommissioningRequest.status_history).joinedload(
            DecommissioningStatusHistory.changed_by),
        joinedload(DecommissioningRequest.approvals).joinedload(
            DecommissioningApproval.approved_by)
    ).filter(
        DecommissioningRequest.model_id == model_id
    ).all()

    for decom in decom_requests:
        # Decommissioning request created
        reason_text = decom.reason.label if decom.reason else "Unknown reason"
        activities.append(ActivityTimelineItem(
            timestamp=decom.created_at,
            activity_type="decommissioning_request_created",
            title=f"Decommissioning request #{decom.request_id} created",
            description=f"Reason: {reason_text}",
            user_name=decom.created_by.full_name if decom.created_by else None,
            user_id=decom.created_by_id,
            entity_type="DecommissioningRequest",
            entity_id=decom.request_id,
            icon="🗑️"
        ))

        # Validator review (if completed)
        if decom.validator_reviewed_at:
            activities.append(ActivityTimelineItem(
                timestamp=decom.validator_reviewed_at,
                activity_type="decommissioning_validator_review",
                title=f"Decommissioning #{decom.request_id} validator review",
                description=decom.validator_comment,
                user_name=decom.validator_reviewed_by.full_name if decom.validator_reviewed_by else None,
                user_id=decom.validator_reviewed_by_id,
                entity_type="DecommissioningRequest",
                entity_id=decom.request_id,
                icon="✍️"
            ))

        # Owner review (if completed and was required)
        if decom.owner_approval_required and decom.owner_reviewed_at:
            activities.append(ActivityTimelineItem(
                timestamp=decom.owner_reviewed_at,
                activity_type="decommissioning_owner_review",
                title=f"Decommissioning #{decom.request_id} owner review",
                description=decom.owner_comment,
                user_name=decom.owner_reviewed_by.full_name if decom.owner_reviewed_by else None,
                user_id=decom.owner_reviewed_by_id,
                entity_type="DecommissioningRequest",
                entity_id=decom.request_id,
                icon="👤"
            ))

        # Status changes (from history)
        for history in decom.status_history:
            # Skip the initial creation record (already covered above)
            if history.old_status is None:
                continue
            status_icon = "🔄"
            if history.new_status == "APPROVED":
                status_icon = "✅"
            elif history.new_status == "REJECTED":
                status_icon = "❌"
            elif history.new_status == "WITHDRAWN":
                status_icon = "↩️"
            elif history.new_status == "VALIDATOR_APPROVED":
                status_icon = "📋"

            activities.append(ActivityTimelineItem(
                timestamp=history.changed_at,
                activity_type="decommissioning_status_change",
                title=f"Decommissioning #{decom.request_id} status: {history.new_status}",
                description=history.notes,
                user_name=history.changed_by.full_name if history.changed_by else None,
                user_id=history.changed_by_id,
                entity_type="DecommissioningRequest",
                entity_id=decom.request_id,
                icon=status_icon
            ))

        # Stage 2 approvals (Global/Regional)
        for approval in decom.approvals:
            if approval.approved_at:
                region_text = f" ({approval.region.name})" if approval.region else ""
                approval_status = "approved" if approval.is_approved else "rejected"
                activities.append(ActivityTimelineItem(
                    timestamp=approval.approved_at,
                    activity_type="decommissioning_approval",
                    title=f"Decommissioning #{decom.request_id} {approval.approver_type}{region_text} {approval_status}",
                    description=approval.comment,
                    user_name=approval.approved_by.full_name if approval.approved_by else None,
                    user_id=approval.approved_by_id,
                    entity_type="DecommissioningApproval",
                    entity_id=approval.approval_id,
                    icon="✅" if approval.is_approved else "❌"
                ))

    # 9. Monitoring cycles (performance monitoring)
    # Find monitoring plans that include this model
    monitoring_cycles = db.query(MonitoringCycle).options(
        joinedload(MonitoringCycle.plan),
        joinedload(MonitoringCycle.submitted_by),
        joinedload(MonitoringCycle.completed_by),
        joinedload(MonitoringCycle.approvals).joinedload(MonitoringCycleApproval.approver),
        joinedload(MonitoringCycle.approvals).joinedload(MonitoringCycleApproval.region)
    ).join(
        MonitoringPlan, MonitoringCycle.plan_id == MonitoringPlan.plan_id
    ).join(
        monitoring_plan_models,
        MonitoringPlan.plan_id == monitoring_plan_models.c.plan_id
    ).filter(
        monitoring_plan_models.c.model_id == model_id
    ).all()

    for cycle in monitoring_cycles:
        plan_name = cycle.plan.name if cycle.plan else "Unknown Plan"
        period_text = f"{cycle.period_start_date} to {cycle.period_end_date}"

        # Cycle created
        activities.append(ActivityTimelineItem(
            timestamp=cycle.created_at,
            activity_type="monitoring_cycle_created",
            title=f"Monitoring cycle started: {plan_name}",
            description=f"Period: {period_text}",
            user_name=None,
            user_id=None,
            entity_type="MonitoringCycle",
            entity_id=cycle.cycle_id,
            icon="📊"
        ))

        # Cycle submitted (if submitted)
        if cycle.submitted_at:
            activities.append(ActivityTimelineItem(
                timestamp=cycle.submitted_at,
                activity_type="monitoring_cycle_submitted",
                title=f"Monitoring data submitted: {plan_name}",
                description=f"Period: {period_text}",
                user_name=cycle.submitted_by.full_name if cycle.submitted_by else None,
                user_id=cycle.submitted_by_user_id,
                entity_type="MonitoringCycle",
                entity_id=cycle.cycle_id,
                icon="📤"
            ))

        # Cycle completed/approved (if completed)
        if cycle.completed_at and cycle.status == "APPROVED":
            activities.append(ActivityTimelineItem(
                timestamp=cycle.completed_at,
                activity_type="monitoring_cycle_completed",
                title=f"Monitoring cycle completed: {plan_name}",
                description=f"Period: {period_text}",
                user_name=cycle.completed_by.full_name if cycle.completed_by else None,
                user_id=cycle.completed_by_user_id,
                entity_type="MonitoringCycle",
                entity_id=cycle.cycle_id,
                icon="✅"
            ))

        # Individual approvals
        for approval in cycle.approvals:
            if approval.approved_at and approval.approval_status in ["Approved", "Rejected"]:
                region_text = f" ({approval.region.name})" if approval.region else ""
                approval_status = "approved" if approval.approval_status == "Approved" else "rejected"
                activities.append(ActivityTimelineItem(
                    timestamp=approval.approved_at,
                    activity_type="monitoring_cycle_approval",
                    title=f"Monitoring {approval.approval_type}{region_text} {approval_status}: {plan_name}",
                    description=approval.comments,
                    user_name=approval.approver.full_name if approval.approver else None,
                    user_id=approval.approver_id,
                    entity_type="MonitoringCycleApproval",
                    entity_id=approval.approval_id,
                    icon="✅" if approval.approval_status == "Approved" else "❌"
                ))

    # Sort all activities by timestamp (newest first)
    activities.sort(key=lambda x: x.timestamp, reverse=True)

    # Apply limit
    activities = activities[:limit]

    return ActivityTimelineResponse(
        model_id=model_id,
        model_name=model.model_name,
        activities=activities,
        total_count=len(activities)
    )


@router.get("/{model_id}/name-history", response_model=ModelNameHistoryResponse)
def get_model_name_history(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the name change history for a specific model.

    Returns all name changes in reverse chronological order.
    """
    from app.core.rls import can_access_model

    # Check model exists and user has access
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    if not can_access_model(model.model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this model"
        )

    # Get name history
    history = db.query(ModelNameHistory).options(
        joinedload(ModelNameHistory.changed_by)
    ).filter(
        ModelNameHistory.model_id == model_id
    ).order_by(ModelNameHistory.changed_at.desc()).all()

    history_items = [
        ModelNameHistoryItem(
            history_id=h.history_id,
            model_id=h.model_id,
            old_name=h.old_name,
            new_name=h.new_name,
            changed_by_id=h.changed_by_id,
            changed_by_name=h.changed_by.full_name if h.changed_by else None,
            changed_at=h.changed_at,
            change_reason=h.change_reason
        )
        for h in history
    ]

    return ModelNameHistoryResponse(
        model_id=model_id,
        current_name=model.model_name,
        history=history_items,
        total_changes=len(history_items)
    )


# ============================================================================
# Pending Edit Endpoints (Model Edit Approval Workflow)
# ============================================================================

@router.get("/pending-edits/all", response_model=List[dict])
def list_all_pending_edits(
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all pending model edits across all models (Admin only).

    Used for admin dashboard to review pending changes.
    """
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    from app.models.model_pending_edit import ModelPendingEdit

    query = db.query(ModelPendingEdit).options(
        joinedload(ModelPendingEdit.model).joinedload(Model.owner),
        joinedload(ModelPendingEdit.requested_by),
        joinedload(ModelPendingEdit.reviewed_by)
    )

    if status_filter:
        query = query.filter(ModelPendingEdit.status == status_filter)
    else:
        # Default to pending only
        query = query.filter(ModelPendingEdit.status == "pending")

    pending_edits = query.order_by(ModelPendingEdit.requested_at.desc()).all()

    return [
        {
            "pending_edit_id": pe.pending_edit_id,
            "model_id": pe.model_id,
            "model_name": pe.model.model_name,
            "model_owner": {
                "user_id": pe.model.owner.user_id,
                "full_name": pe.model.owner.full_name,
                "email": pe.model.owner.email
            } if pe.model.owner else None,
            "requested_by": {
                "user_id": pe.requested_by.user_id,
                "full_name": pe.requested_by.full_name,
                "email": pe.requested_by.email
            },
            "requested_at": pe.requested_at.isoformat() if pe.requested_at else None,
            "proposed_changes": pe.proposed_changes,
            "original_values": pe.original_values,
            "status": pe.status,
            "reviewed_by": {
                "user_id": pe.reviewed_by.user_id,
                "full_name": pe.reviewed_by.full_name,
                "email": pe.reviewed_by.email
            } if pe.reviewed_by else None,
            "reviewed_at": pe.reviewed_at.isoformat() if pe.reviewed_at else None,
            "review_comment": pe.review_comment
        }
        for pe in pending_edits
    ]


@router.get("/{model_id}/pending-edits", response_model=List[dict])
def list_model_pending_edits(
    model_id: int,
    include_all: bool = Query(False, description="Include approved/rejected edits"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List pending edits for a specific model.

    Accessible by model owners, developers, delegates, and admins.
    """
    from app.core.rls import can_access_model
    from app.models.model_pending_edit import ModelPendingEdit

    if not can_access_model(model_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    query = db.query(ModelPendingEdit).options(
        joinedload(ModelPendingEdit.requested_by),
        joinedload(ModelPendingEdit.reviewed_by)
    ).filter(ModelPendingEdit.model_id == model_id)

    if not include_all:
        query = query.filter(ModelPendingEdit.status == "pending")

    pending_edits = query.order_by(ModelPendingEdit.requested_at.desc()).all()

    return [
        {
            "pending_edit_id": pe.pending_edit_id,
            "model_id": pe.model_id,
            "requested_by": {
                "user_id": pe.requested_by.user_id,
                "full_name": pe.requested_by.full_name,
                "email": pe.requested_by.email
            },
            "requested_at": pe.requested_at.isoformat() if pe.requested_at else None,
            "proposed_changes": pe.proposed_changes,
            "original_values": pe.original_values,
            "status": pe.status,
            "reviewed_by": {
                "user_id": pe.reviewed_by.user_id,
                "full_name": pe.reviewed_by.full_name,
                "email": pe.reviewed_by.email
            } if pe.reviewed_by else None,
            "reviewed_at": pe.reviewed_at.isoformat() if pe.reviewed_at else None,
            "review_comment": pe.review_comment
        }
        for pe in pending_edits
    ]


@router.post("/{model_id}/pending-edits/{edit_id}/approve")
def approve_pending_edit(
    model_id: int,
    edit_id: int,
    review_data: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve a pending edit and apply the changes to the model.

    Admin only.
    """
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    from app.models.model_pending_edit import ModelPendingEdit
    from datetime import datetime, UTC

    pending_edit = db.query(ModelPendingEdit).filter(
        ModelPendingEdit.pending_edit_id == edit_id,
        ModelPendingEdit.model_id == model_id
    ).first()

    if not pending_edit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending edit not found"
        )

    if pending_edit.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve edit with status '{pending_edit.status}'"
        )

    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    # Apply the proposed changes to the model
    proposed_changes = pending_edit.proposed_changes
    changes_applied = {}

    for field, value in proposed_changes.items():
        if field == 'user_ids':
            # Handle user_ids separately - only log if actually changed
            if value is not None:
                old_user_ids = sorted([u.user_id for u in model.users])
                new_user_ids = sorted(value)
                if old_user_ids != new_user_ids:
                    users = db.query(User).filter(User.user_id.in_(value)).all()
                    model.users = users
                    changes_applied[field] = {"old": old_user_ids, "new": new_user_ids}
        elif field == 'regulatory_category_ids':
            # Handle regulatory_category_ids separately - only log if actually changed
            if value is not None:
                old_category_ids = sorted([c.value_id for c in model.regulatory_categories])
                new_category_ids = sorted(value)
                if old_category_ids != new_category_ids:
                    categories = db.query(TaxonomyValue).filter(
                        TaxonomyValue.value_id.in_(value)).all()
                    model.regulatory_categories = categories
                    changes_applied[field] = {"old": old_category_ids, "new": new_category_ids}
        else:
            old_value = getattr(model, field, None)
            if old_value != value:
                setattr(model, field, value)
                changes_applied[field] = {"old": old_value, "new": value}

    # Update pending edit status
    pending_edit.status = "approved"
    pending_edit.reviewed_by_id = current_user.user_id
    pending_edit.reviewed_at = datetime.now(UTC)
    pending_edit.review_comment = review_data.get("comment") if review_data else None

    # Audit log for approval
    create_audit_log(
        db=db,
        entity_type="ModelPendingEdit",
        entity_id=edit_id,
        action="APPROVE",
        user_id=current_user.user_id,
        changes={"model_id": model_id, "changes_applied": changes_applied}
    )

    # Audit log for model update
    create_audit_log(
        db=db,
        entity_type="Model",
        entity_id=model_id,
        action="UPDATE",
        user_id=current_user.user_id,
        changes={"approved_pending_edit_id": edit_id, **changes_applied}
    )

    db.commit()

    return {
        "message": "Pending edit approved and changes applied",
        "pending_edit_id": edit_id,
        "status": "approved",
        "model_id": model_id
    }


@router.post("/{model_id}/pending-edits/{edit_id}/reject")
def reject_pending_edit(
    model_id: int,
    edit_id: int,
    review_data: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reject a pending edit.

    Admin only. The proposed changes are NOT applied.
    """
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    from app.models.model_pending_edit import ModelPendingEdit
    from datetime import datetime, UTC

    pending_edit = db.query(ModelPendingEdit).filter(
        ModelPendingEdit.pending_edit_id == edit_id,
        ModelPendingEdit.model_id == model_id
    ).first()

    if not pending_edit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending edit not found"
        )

    if pending_edit.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject edit with status '{pending_edit.status}'"
        )

    # Update pending edit status
    pending_edit.status = "rejected"
    pending_edit.reviewed_by_id = current_user.user_id
    pending_edit.reviewed_at = datetime.now(UTC)
    pending_edit.review_comment = review_data.get("comment") if review_data else None

    # Audit log for rejection
    create_audit_log(
        db=db,
        entity_type="ModelPendingEdit",
        entity_id=edit_id,
        action="REJECT",
        user_id=current_user.user_id,
        changes={
            "model_id": model_id,
            "rejected_changes": pending_edit.proposed_changes,
            "comment": pending_edit.review_comment
        }
    )

    db.commit()

    return {
        "message": "Pending edit rejected",
        "pending_edit_id": edit_id,
        "status": "rejected",
        "model_id": model_id
    }
