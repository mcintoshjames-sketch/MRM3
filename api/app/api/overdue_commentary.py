"""Overdue Revalidation Commentary API endpoints."""
from datetime import datetime, date, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.roles import is_admin
from app.models import (
    User, Model, ValidationRequest, ValidationRequestModelVersion,
    ValidationAssignment, OverdueRevalidationComment
)
from app.models.audit_log import AuditLog
from app.schemas.overdue_commentary import (
    OverdueCommentaryCreate,
    OverdueCommentaryResponse,
    CurrentOverdueCommentaryResponse,
    OverdueCommentaryHistoryResponse
)
from app.models.model_delegate import ModelDelegate

router = APIRouter()

# Staleness threshold in days
COMMENT_STALENESS_DAYS = 45


def create_audit_log(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, changes: dict = None):
    """Create an audit log entry for overdue commentary operations."""
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(audit_log)


def get_stale_reason(comment: OverdueRevalidationComment) -> tuple[bool, Optional[str]]:
    """
    Check if a comment is stale and return the reason.

    A comment is stale if:
    1. It's older than 45 days, OR
    2. The target date has passed without resolution
    """
    if not comment:
        return False, None

    today = date.today()
    # Use timezone-aware datetime to match database field
    now_utc = datetime.now(timezone.utc)
    created_at = comment.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    comment_age = (now_utc - created_at).days

    if comment_age > COMMENT_STALENESS_DAYS:
        return True, f"Comment is {comment_age} days old (exceeds {COMMENT_STALENESS_DAYS}-day freshness requirement)"

    if comment.target_date < today:
        days_past = (today - comment.target_date).days
        return True, f"Target date has passed ({days_past} days ago) - update required"

    return False, None


def compute_completion_date(
    validation_request: ValidationRequest,
    commentary_target_date: Optional[date],
    lead_time_days: int
) -> Optional[date]:
    """
    Compute the expected completion date based on validation stage.

    - Pre-submission (PRE_SUBMISSION): commentary_target_date + lead_time_days
      (owner provides submission target, we add lead time for validation completion)
    - Post-submission (VALIDATION_IN_PROGRESS): commentary_target_date directly
      (validator provides their estimated completion date, no add-on needed)
    """
    # If validation has been submitted (moved to IN_PROGRESS or later)
    if validation_request.submission_received_date:
        # Post-submission: validator provides completion date directly
        if commentary_target_date:
            return commentary_target_date
        return validation_request.target_completion_date

    # Pre-submission: owner provides submission target + lead time
    if commentary_target_date:
        return commentary_target_date + timedelta(days=lead_time_days)

    return validation_request.target_completion_date


def can_user_create_commentary(
    user: User,
    validation_request: ValidationRequest,
    overdue_type: str,
    db: Session
) -> bool:
    """
    Check if a user is authorized to create/update overdue commentary.

    Authorization rules:
    - Admin: Can ALWAYS submit on anyone's behalf (both PRE_SUBMISSION and VALIDATION_IN_PROGRESS)
    - PRE_SUBMISSION: Model owner, developer, or delegate
    - VALIDATION_IN_PROGRESS: Assigned validator
    """
    # Admins can always submit on anyone's behalf
    if is_admin(user):
        return True

    # Get first model from validation request
    model_version = db.query(ValidationRequestModelVersion).filter(
        ValidationRequestModelVersion.request_id == validation_request.request_id
    ).first()

    if not model_version:
        return False

    model = db.query(Model).filter(
        Model.model_id == model_version.model_id
    ).first()

    if not model:
        return False

    if overdue_type == "PRE_SUBMISSION":
        # Check if user is owner, developer, or delegate
        if model.owner_id == user.user_id or model.developer_id == user.user_id:
            return True

        # Check delegate status
        delegate = db.query(ModelDelegate).filter(
            ModelDelegate.model_id == model.model_id,
            ModelDelegate.user_id == user.user_id,
            ModelDelegate.revoked_at.is_(None)
        ).first()

        return delegate is not None

    elif overdue_type == "VALIDATION_IN_PROGRESS":
        # Check if user is an assigned validator
        assignment = db.query(ValidationAssignment).filter(
            ValidationAssignment.request_id == validation_request.request_id,
            ValidationAssignment.validator_id == user.user_id
        ).first()

        return assignment is not None

    return False


@router.get(
    "/requests/{request_id}/overdue-commentary",
    response_model=CurrentOverdueCommentaryResponse
)
def get_overdue_commentary(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current overdue commentary for a validation request.

    Returns:
    - Current commentary if exists
    - Whether commentary is stale and needs update
    - Computed completion date based on validation stage
    """
    # Get validation request with model info
    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.model
        )
    ).filter(ValidationRequest.request_id == request_id).first()

    if not validation_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation request {request_id} not found"
        )

    # Get first model (most requests have single model)
    if not validation_request.model_versions_assoc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No models found for this validation request"
        )

    model = validation_request.model_versions_assoc[0].model

    # Get lead time from request's applicable_lead_time_days (computed from models' policies)
    lead_time_days = validation_request.applicable_lead_time_days

    # Determine overdue type based on submission status
    if validation_request.submission_received_date:
        overdue_type = "VALIDATION_IN_PROGRESS"
    else:
        overdue_type = "PRE_SUBMISSION"

    # Get current comment
    current_comment = db.query(OverdueRevalidationComment).filter(
        OverdueRevalidationComment.validation_request_id == request_id,
        OverdueRevalidationComment.is_current == True
    ).first()

    # Check staleness
    is_stale, stale_reason = get_stale_reason(current_comment)

    # Compute completion date
    target_date = current_comment.target_date if current_comment else None
    computed_completion = compute_completion_date(
        validation_request, target_date, lead_time_days
    )

    # Build response
    response = CurrentOverdueCommentaryResponse(
        validation_request_id=request_id,
        model_id=model.model_id,
        model_name=model.model_name,
        overdue_type=overdue_type,
        has_current_comment=current_comment is not None,
        is_stale=is_stale,
        stale_reason=stale_reason,
        computed_completion_date=computed_completion
    )

    if current_comment:
        response.current_comment = OverdueCommentaryResponse(
            comment_id=current_comment.comment_id,
            validation_request_id=current_comment.validation_request_id,
            overdue_type=current_comment.overdue_type,
            reason_comment=current_comment.reason_comment,
            target_date=current_comment.target_date,
            created_by_user_id=current_comment.created_by_user_id,
            created_by_user=current_comment.created_by_user,
            created_at=current_comment.created_at,
            is_current=current_comment.is_current,
            superseded_at=current_comment.superseded_at,
            superseded_by_comment_id=current_comment.superseded_by_comment_id
        )

    return response


@router.post(
    "/requests/{request_id}/overdue-commentary",
    response_model=OverdueCommentaryResponse,
    status_code=status.HTTP_201_CREATED
)
def create_overdue_commentary(
    request_id: int,
    commentary: OverdueCommentaryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create or update overdue commentary for a validation request.

    - Previous commentary is marked as superseded (is_current=False)
    - New commentary becomes the current record
    - Only authorized users can create commentary based on overdue_type
    """
    # Get validation request
    validation_request = db.query(ValidationRequest).filter(
        ValidationRequest.request_id == request_id
    ).first()

    if not validation_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation request {request_id} not found"
        )

    # Validate overdue type matches current state
    has_submission = validation_request.submission_received_date is not None

    if commentary.overdue_type == "VALIDATION_IN_PROGRESS" and not has_submission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit VALIDATION_IN_PROGRESS commentary before submission is received"
        )

    if commentary.overdue_type == "PRE_SUBMISSION" and has_submission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit PRE_SUBMISSION commentary after submission is received"
        )

    # Check authorization
    if not can_user_create_commentary(
        current_user, validation_request, commentary.overdue_type, db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not authorized to create {commentary.overdue_type} commentary for this validation request"
        )

    # Validate target date is in the future
    if commentary.target_date <= date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target date must be in the future"
        )

    # Mark existing current comment as superseded
    existing_current = db.query(OverdueRevalidationComment).filter(
        OverdueRevalidationComment.validation_request_id == request_id,
        OverdueRevalidationComment.is_current == True
    ).first()

    # Create new comment
    now_utc = datetime.now(timezone.utc)
    new_comment = OverdueRevalidationComment(
        validation_request_id=request_id,
        overdue_type=commentary.overdue_type,
        reason_comment=commentary.reason_comment,
        target_date=commentary.target_date,
        created_by_user_id=current_user.user_id,
        created_at=now_utc,
        is_current=True
    )
    db.add(new_comment)
    db.flush()  # Get the new comment_id

    # Update existing comment to point to new one
    if existing_current:
        existing_current.is_current = False
        existing_current.superseded_at = now_utc
        existing_current.superseded_by_comment_id = new_comment.comment_id

    # Create audit log entry for the validation request
    action = "overdue_commentary_updated" if existing_current else "overdue_commentary_created"
    create_audit_log(
        db=db,
        entity_type="ValidationRequest",
        entity_id=request_id,
        action=action,
        user_id=current_user.user_id,
        changes={
            "overdue_type": commentary.overdue_type,
            "reason_comment": commentary.reason_comment,
            "target_date": str(commentary.target_date),
            "comment_id": new_comment.comment_id,
            "previous_comment_id": existing_current.comment_id if existing_current else None
        }
    )

    db.commit()
    db.refresh(new_comment)

    return OverdueCommentaryResponse(
        comment_id=new_comment.comment_id,
        validation_request_id=new_comment.validation_request_id,
        overdue_type=new_comment.overdue_type,
        reason_comment=new_comment.reason_comment,
        target_date=new_comment.target_date,
        created_by_user_id=new_comment.created_by_user_id,
        created_by_user=new_comment.created_by_user,
        created_at=new_comment.created_at,
        is_current=new_comment.is_current,
        superseded_at=new_comment.superseded_at,
        superseded_by_comment_id=new_comment.superseded_by_comment_id
    )


@router.get(
    "/requests/{request_id}/overdue-commentary/history",
    response_model=OverdueCommentaryHistoryResponse
)
def get_overdue_commentary_history(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get full history of overdue commentary for a validation request.

    Returns current comment and all historical comments.
    """
    # Get validation request with model info
    validation_request = db.query(ValidationRequest).options(
        joinedload(ValidationRequest.model_versions_assoc).joinedload(
            ValidationRequestModelVersion.model
        )
    ).filter(ValidationRequest.request_id == request_id).first()

    if not validation_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation request {request_id} not found"
        )

    # Get first model (most requests have single model)
    first_model_version = validation_request.model_versions_assoc[0] if validation_request.model_versions_assoc else None

    model_id = first_model_version.model.model_id if first_model_version else None
    model_name = first_model_version.model.model_name if first_model_version else "Unknown"

    # Get all comments ordered by created_at desc
    comments = db.query(OverdueRevalidationComment).options(
        joinedload(OverdueRevalidationComment.created_by_user)
    ).filter(
        OverdueRevalidationComment.validation_request_id == request_id
    ).order_by(desc(OverdueRevalidationComment.created_at)).all()

    current_comment = None
    history = []

    for comment in comments:
        comment_response = OverdueCommentaryResponse(
            comment_id=comment.comment_id,
            validation_request_id=comment.validation_request_id,
            overdue_type=comment.overdue_type,
            reason_comment=comment.reason_comment,
            target_date=comment.target_date,
            created_by_user_id=comment.created_by_user_id,
            created_by_user=comment.created_by_user,
            created_at=comment.created_at,
            is_current=comment.is_current,
            superseded_at=comment.superseded_at,
            superseded_by_comment_id=comment.superseded_by_comment_id
        )

        if comment.is_current:
            current_comment = comment_response
        else:
            history.append(comment_response)

    return OverdueCommentaryHistoryResponse(
        validation_request_id=request_id,
        model_id=model_id,
        model_name=model_name,
        current_comment=current_comment,
        comment_history=history
    )


# ==================== MODEL CONVENIENCE ENDPOINTS ====================

# Create a separate router for model-based routes
model_router = APIRouter()


@model_router.get(
    "/{model_id}/overdue-commentary",
    response_model=CurrentOverdueCommentaryResponse
)
def get_model_overdue_commentary(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Convenience endpoint to get overdue commentary for a model's most recent validation request.

    This is useful for the model details page to show overdue status.
    Returns 404 if no validation request exists for the model.
    """
    # Get the model
    model = db.query(Model).filter(Model.model_id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found"
        )

    # Get most recent validation request for this model
    latest_request = db.query(ValidationRequest).join(
        ValidationRequestModelVersion
    ).filter(
        ValidationRequestModelVersion.model_id == model_id
    ).order_by(desc(ValidationRequest.created_at)).first()

    if not latest_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No validation request found for model {model_id}"
        )

    # Get lead time from request's applicable_lead_time_days (computed from models' policies)
    lead_time_days = latest_request.applicable_lead_time_days

    # Determine overdue type based on submission status
    if latest_request.submission_received_date:
        overdue_type = "VALIDATION_IN_PROGRESS"
    else:
        overdue_type = "PRE_SUBMISSION"

    # Get current comment
    current_comment = db.query(OverdueRevalidationComment).options(
        joinedload(OverdueRevalidationComment.created_by_user)
    ).filter(
        OverdueRevalidationComment.validation_request_id == latest_request.request_id,
        OverdueRevalidationComment.is_current == True
    ).first()

    # Check staleness
    is_stale, stale_reason = get_stale_reason(current_comment)

    # Compute completion date
    target_date = current_comment.target_date if current_comment else None
    computed_completion = compute_completion_date(
        latest_request, target_date, lead_time_days
    )

    # Build response
    response = CurrentOverdueCommentaryResponse(
        validation_request_id=latest_request.request_id,
        model_id=model.model_id,
        model_name=model.model_name,
        overdue_type=overdue_type,
        has_current_comment=current_comment is not None,
        is_stale=is_stale,
        stale_reason=stale_reason,
        computed_completion_date=computed_completion
    )

    if current_comment:
        response.current_comment = OverdueCommentaryResponse(
            comment_id=current_comment.comment_id,
            validation_request_id=current_comment.validation_request_id,
            overdue_type=current_comment.overdue_type,
            reason_comment=current_comment.reason_comment,
            target_date=current_comment.target_date,
            created_by_user_id=current_comment.created_by_user_id,
            created_by_user=current_comment.created_by_user,
            created_at=current_comment.created_at,
            is_current=current_comment.is_current,
            superseded_at=current_comment.superseded_at,
            superseded_by_comment_id=current_comment.superseded_by_comment_id
        )

    return response
