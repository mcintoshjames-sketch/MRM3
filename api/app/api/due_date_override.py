"""Model Due Date Override API endpoints."""
from datetime import datetime, date, timezone
from typing import Optional
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.roles import is_admin
from app.core.time import utc_now
from app.models import (
    User, Model, ValidationRequest, ValidationRequestModelVersion,
    AuditLog, TaxonomyValue, Taxonomy
)
from app.models.due_date_override import ModelDueDateOverride
from app.models.validation import ValidationPolicy
from app.schemas.due_date_override import (
    DueDateOverrideCreate,
    DueDateOverrideClear,
    DueDateOverrideResponse,
    CurrentDueDateOverrideResponse,
    DueDateOverrideHistoryResponse
)

router = APIRouter()


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict | None = None):
    """Create an audit log entry."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


def get_current_validation_request(db: Session, model_id: int) -> Optional[ValidationRequest]:
    """Get the current/open validation request for a model."""
    # Get terminal status codes (APPROVED, CANCELLED)
    terminal_statuses = db.query(TaxonomyValue.value_id).join(
        Taxonomy, TaxonomyValue.taxonomy_id == Taxonomy.taxonomy_id
    ).filter(
        Taxonomy.name == "Validation Request Status",
        TaxonomyValue.code.in_(["APPROVED", "CANCELLED"])
    ).subquery()

    return db.query(ValidationRequest).join(
        ValidationRequestModelVersion,
        ValidationRequest.request_id == ValidationRequestModelVersion.request_id
    ).filter(
        ValidationRequestModelVersion.model_id == model_id,
        ~ValidationRequest.current_status_id.in_(terminal_statuses)
    ).order_by(desc(ValidationRequest.created_at)).first()


def get_policy_calculated_date(db: Session, model: Model, validation_request: Optional[ValidationRequest]) -> Optional[date]:
    """Calculate the policy-determined due date for a model."""
    if validation_request:
        # Use the validation request's submission due date
        return validation_request.get_submission_due_date()
    return None


def _to_override_response(override: ModelDueDateOverride) -> DueDateOverrideResponse:
    """Convert model to response schema."""
    return DueDateOverrideResponse(
        override_id=override.override_id,
        model_id=override.model_id,
        validation_request_id=override.validation_request_id,
        override_type=override.override_type,
        target_scope=override.target_scope,
        override_date=override.override_date,
        original_calculated_date=override.original_calculated_date,
        reason=override.reason,
        created_by_user_id=override.created_by_user_id,
        created_by_user=override.created_by_user,
        created_at=override.created_at,
        is_active=override.is_active,
        cleared_at=override.cleared_at,
        cleared_by_user_id=override.cleared_by_user_id,
        cleared_by_user=override.cleared_by_user,
        cleared_reason=override.cleared_reason,
        cleared_type=override.cleared_type,
        superseded_by_override_id=override.superseded_by_override_id,
        rolled_from_override_id=override.rolled_from_override_id
    )


@router.get(
    "/{model_id}/due-date-override",
    response_model=CurrentDueDateOverrideResponse
)
def get_due_date_override(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current due date override status for a model.

    Returns active override if any, along with calculated vs effective dates.
    """
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found"
        )

    # Get current validation request
    current_request = get_current_validation_request(db, model_id)

    # Get active override
    active_override = db.query(ModelDueDateOverride).options(
        joinedload(ModelDueDateOverride.created_by_user),
        joinedload(ModelDueDateOverride.cleared_by_user)
    ).filter(
        ModelDueDateOverride.model_id == model_id,
        ModelDueDateOverride.is_active == True
    ).first()

    # Calculate policy date
    policy_date = get_policy_calculated_date(db, model, current_request)

    # Determine effective date using min() to enforce earlier-only
    if active_override and policy_date:
        effective_date = min(active_override.override_date, policy_date)
    elif active_override:
        effective_date = active_override.override_date
    else:
        effective_date = policy_date

    response = CurrentDueDateOverrideResponse(
        model_id=model.model_id,
        model_name=model.model_name,
        has_active_override=active_override is not None,
        policy_calculated_date=policy_date,
        effective_due_date=effective_date,
        current_validation_request_id=current_request.request_id if current_request else None,
        current_validation_status=current_request.current_status.label if current_request and current_request.current_status else None
    )

    if active_override:
        response.active_override = _to_override_response(active_override)

    return response


@router.post(
    "/{model_id}/due-date-override",
    response_model=DueDateOverrideResponse,
    status_code=status.HTTP_201_CREATED
)
def create_due_date_override(
    model_id: int,
    override_data: DueDateOverrideCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a due date override for a model (Admin only).

    Business rules:
    - Override date must be earlier than policy-calculated date
    - Override date must be in the future
    - Only one active override per model at a time
    - Previous active override is superseded
    """
    # Admin check
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can create due date overrides"
        )

    # Get model
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found"
        )

    # Get current validation request
    current_request = get_current_validation_request(db, model_id)

    # Validate CURRENT_REQUEST scope requires an open validation
    if override_data.target_scope == "CURRENT_REQUEST" and not current_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create CURRENT_REQUEST override - no open validation request exists"
        )

    # Get policy-calculated date
    policy_date = get_policy_calculated_date(db, model, current_request)

    if not policy_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot determine policy-calculated date for this model. Ensure a validation request exists."
        )

    # Validate override date is earlier than calculated (EARLIER DIRECTION ONLY)
    if override_data.override_date >= policy_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Override date must be earlier than policy-calculated date ({policy_date}). Overrides can only pull dates forward, not push them back."
        )

    # Validate override date is in the future
    if override_data.override_date <= date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Override date must be in the future"
        )

    # Supersede any existing active override
    now_utc = utc_now()
    existing_active = db.query(ModelDueDateOverride).filter(
        ModelDueDateOverride.model_id == model_id,
        ModelDueDateOverride.is_active == True
    ).first()

    # Create new override
    new_override = ModelDueDateOverride(
        model_id=model_id,
        validation_request_id=current_request.request_id if override_data.target_scope == "CURRENT_REQUEST" and current_request else None,
        override_type=override_data.override_type,
        target_scope=override_data.target_scope,
        override_date=override_data.override_date,
        original_calculated_date=policy_date,
        reason=override_data.reason,
        created_by_user_id=current_user.user_id,
        created_at=now_utc,
        is_active=True
    )
    db.add(new_override)
    db.flush()  # Get the new ID

    # Update existing active override to superseded
    if existing_active:
        existing_active.is_active = False
        existing_active.cleared_at = now_utc
        existing_active.cleared_by_user_id = current_user.user_id
        existing_active.cleared_reason = f"Superseded by override #{new_override.override_id}"
        existing_active.cleared_type = "SUPERSEDED"
        existing_active.superseded_by_override_id = new_override.override_id

    # Create audit log
    create_audit_log(
        db=db,
        entity_type="Model",
        entity_id=model_id,
        action="due_date_override_created",
        user_id=current_user.user_id,
        changes={
            "override_id": new_override.override_id,
            "override_type": override_data.override_type,
            "target_scope": override_data.target_scope,
            "override_date": str(override_data.override_date),
            "original_calculated_date": str(policy_date),
            "reason": override_data.reason,
            "superseded_override_id": existing_active.override_id if existing_active else None
        }
    )

    db.commit()
    db.refresh(new_override)

    # Reload with relationships
    new_override = db.query(ModelDueDateOverride).options(
        joinedload(ModelDueDateOverride.created_by_user),
        joinedload(ModelDueDateOverride.cleared_by_user)
    ).filter(ModelDueDateOverride.override_id == new_override.override_id).first()

    return _to_override_response(new_override)


@router.delete(
    "/{model_id}/due-date-override",
    response_model=DueDateOverrideResponse
)
def clear_due_date_override(
    model_id: int,
    clear_data: DueDateOverrideClear,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clear/cancel an active due date override (Admin only).

    The override is marked inactive with the clear reason.
    """
    # Admin check
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can clear due date overrides"
        )

    # Get model
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found"
        )

    # Get active override
    active_override = db.query(ModelDueDateOverride).options(
        joinedload(ModelDueDateOverride.created_by_user)
    ).filter(
        ModelDueDateOverride.model_id == model_id,
        ModelDueDateOverride.is_active == True
    ).first()

    if not active_override:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active override found for this model"
        )

    # Clear the override
    now_utc = utc_now()
    active_override.is_active = False
    active_override.cleared_at = now_utc
    active_override.cleared_by_user_id = current_user.user_id
    active_override.cleared_reason = clear_data.reason
    active_override.cleared_type = "MANUAL"

    # Create audit log
    create_audit_log(
        db=db,
        entity_type="Model",
        entity_id=model_id,
        action="due_date_override_cleared",
        user_id=current_user.user_id,
        changes={
            "override_id": active_override.override_id,
            "clear_reason": clear_data.reason,
            "cleared_type": "MANUAL"
        }
    )

    db.commit()
    db.refresh(active_override)

    # Reload with relationships
    active_override = db.query(ModelDueDateOverride).options(
        joinedload(ModelDueDateOverride.created_by_user),
        joinedload(ModelDueDateOverride.cleared_by_user)
    ).filter(ModelDueDateOverride.override_id == active_override.override_id).first()

    return _to_override_response(active_override)


@router.get(
    "/{model_id}/due-date-override/history",
    response_model=DueDateOverrideHistoryResponse
)
def get_due_date_override_history(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get full history of due date overrides for a model.
    """
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found"
        )

    # Get all overrides ordered by created_at desc
    overrides = db.query(ModelDueDateOverride).options(
        joinedload(ModelDueDateOverride.created_by_user),
        joinedload(ModelDueDateOverride.cleared_by_user)
    ).filter(
        ModelDueDateOverride.model_id == model_id
    ).order_by(desc(ModelDueDateOverride.created_at)).all()

    active_override = None
    history = []

    for override in overrides:
        response = _to_override_response(override)
        if override.is_active:
            active_override = response
        else:
            history.append(response)

    return DueDateOverrideHistoryResponse(
        model_id=model.model_id,
        model_name=model.model_name,
        active_override=active_override,
        override_history=history
    )


# ==================== HELPER FUNCTIONS FOR WORKFLOW INTEGRATION ====================

def clear_override(
    db: Session,
    override: ModelDueDateOverride,
    cleared_type: str,
    user_id: int,
    reason: str
):
    """Helper to clear an override with specified type and reason."""
    now_utc = utc_now()
    override.is_active = False
    override.cleared_at = now_utc
    override.cleared_by_user_id = user_id
    override.cleared_reason = reason
    override.cleared_type = cleared_type


def get_active_override_for_request(
    db: Session,
    model_id: int,
    request_id: int
) -> Optional[ModelDueDateOverride]:
    """
    Get the active override linked to a specific validation request.

    Returns override if:
    - It's active AND
    - It's CURRENT_REQUEST scope linked to this request_id
    """
    return db.query(ModelDueDateOverride).filter(
        ModelDueDateOverride.model_id == model_id,
        ModelDueDateOverride.is_active == True,
        ModelDueDateOverride.target_scope == "CURRENT_REQUEST",
        ModelDueDateOverride.validation_request_id == request_id
    ).first()


def handle_override_on_approval(
    db: Session,
    validation_request: ValidationRequest,
    current_user_id: int
):
    """
    Handle due date override when a validation request is approved.

    - ONE_TIME: Clear the override (it's done)
    - PERMANENT: Create new override for next cycle (roll forward)
    """
    # Get model ID from validation request
    model_version = db.query(ValidationRequestModelVersion).filter(
        ValidationRequestModelVersion.request_id == validation_request.request_id
    ).first()

    if not model_version:
        return

    model_id = model_version.model_id
    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        return

    # Find active override linked to this request
    override = get_active_override_for_request(db, model_id, validation_request.request_id)

    if not override:
        return

    if override.override_type == "ONE_TIME":
        # Clear the override - it's done
        clear_override(
            db, override, "AUTO_VALIDATION_COMPLETE", current_user_id,
            f"Validation request #{validation_request.request_id} approved"
        )

        create_audit_log(
            db=db,
            entity_type="Model",
            entity_id=model_id,
            action="due_date_override_auto_cleared",
            user_id=current_user_id,
            changes={
                "override_id": override.override_id,
                "validation_request_id": validation_request.request_id,
                "cleared_type": "AUTO_VALIDATION_COMPLETE"
            }
        )

    elif override.override_type == "PERMANENT":
        # Get policy for frequency calculation
        policy = db.query(ValidationPolicy).filter(
            ValidationPolicy.risk_tier_id == model.risk_tier_id
        ).first()

        frequency_months = policy.frequency_months if policy else 12

        # Calculate new override date
        new_override_date = override.override_date + relativedelta(months=frequency_months)

        # Calculate new policy date (for reference)
        new_policy_date = override.original_calculated_date + relativedelta(months=frequency_months)

        # Clear current override with ROLL_FORWARD reason
        clear_override(
            db, override, "AUTO_ROLL_FORWARD", current_user_id,
            f"Rolled forward to {new_override_date}"
        )

        # Create new override for next cycle
        new_override = ModelDueDateOverride(
            model_id=model_id,
            validation_request_id=None,  # NEXT_CYCLE - no request yet
            override_type="PERMANENT",
            target_scope="NEXT_CYCLE",
            override_date=new_override_date,
            original_calculated_date=new_policy_date,
            reason=f"Auto-rolled from override #{override.override_id}",
            created_by_user_id=current_user_id,
            created_at=utc_now(),
            is_active=True,
            rolled_from_override_id=override.override_id
        )
        db.add(new_override)
        db.flush()

        # Link old override to new one
        override.superseded_by_override_id = new_override.override_id

        create_audit_log(
            db=db,
            entity_type="Model",
            entity_id=model_id,
            action="due_date_override_rolled_forward",
            user_id=current_user_id,
            changes={
                "old_override_id": override.override_id,
                "new_override_id": new_override.override_id,
                "old_override_date": str(override.override_date),
                "new_override_date": str(new_override_date),
                "validation_request_id": validation_request.request_id
            }
        )


def promote_next_cycle_override(
    db: Session,
    model_id: int,
    new_request_id: int,
    current_user_id: int
):
    """
    Promote a NEXT_CYCLE override to CURRENT_REQUEST when a new validation is created.
    """
    override = db.query(ModelDueDateOverride).filter(
        ModelDueDateOverride.model_id == model_id,
        ModelDueDateOverride.is_active == True,
        ModelDueDateOverride.target_scope == "NEXT_CYCLE"
    ).first()

    if override:
        old_scope = override.target_scope
        override.target_scope = "CURRENT_REQUEST"
        override.validation_request_id = new_request_id

        create_audit_log(
            db=db,
            entity_type="Model",
            entity_id=model_id,
            action="due_date_override_promoted",
            user_id=current_user_id,
            changes={
                "override_id": override.override_id,
                "old_scope": old_scope,
                "new_scope": "CURRENT_REQUEST",
                "validation_request_id": new_request_id
            }
        )


def void_override_on_cancellation(
    db: Session,
    validation_request: ValidationRequest,
    current_user_id: int
):
    """
    Void an override when its linked validation request is cancelled.
    """
    # Only affects CURRENT_REQUEST overrides linked to this request
    override = db.query(ModelDueDateOverride).filter(
        ModelDueDateOverride.validation_request_id == validation_request.request_id,
        ModelDueDateOverride.is_active == True
    ).first()

    if override:
        model_id = override.model_id

        clear_override(
            db, override, "AUTO_REQUEST_CANCELLED", current_user_id,
            f"Validation request #{validation_request.request_id} was cancelled"
        )

        create_audit_log(
            db=db,
            entity_type="Model",
            entity_id=model_id,
            action="due_date_override_voided",
            user_id=current_user_id,
            changes={
                "override_id": override.override_id,
                "validation_request_id": validation_request.request_id,
                "cleared_type": "AUTO_REQUEST_CANCELLED"
            }
        )
