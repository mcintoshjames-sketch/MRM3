"""
Model Approval Status computation and history tracking.

This module provides functions to:
1. Compute the current approval status of a model
2. Record status changes to history
3. Trigger status recalculation when relevant events occur

The Model Approval Status answers: "Is this model currently approved for use
based on its validation history?"

Status Definitions:
- NEVER_VALIDATED: No validation request has ever been approved for this model
- APPROVED: Most recent validation is APPROVED with all required approvals complete
- INTERIM_APPROVED: Most recent completed validation was of INTERIM type
- VALIDATION_IN_PROGRESS: Model is overdue but has active validation in substantive stage
- EXPIRED: Model is overdue with no active validation or validation still in INTAKE
"""
from datetime import date, datetime
from typing import Optional, Tuple, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import (
    Model,
    ValidationRequest,
    ValidationRequestModelVersion,
    ValidationApproval,
    TaxonomyValue,
    ValidationOutcome,
)
from app.models.model_approval_status_history import ModelApprovalStatusHistory
from app.core.time import utc_now


class ApprovalStatus:
    """Enum-like class for approval status codes."""
    NEVER_VALIDATED = "NEVER_VALIDATED"
    APPROVED = "APPROVED"
    INTERIM_APPROVED = "INTERIM_APPROVED"
    VALIDATION_IN_PROGRESS = "VALIDATION_IN_PROGRESS"
    EXPIRED = "EXPIRED"


# Status labels for display
STATUS_LABELS = {
    ApprovalStatus.NEVER_VALIDATED: "Never Validated",
    ApprovalStatus.APPROVED: "Approved",
    ApprovalStatus.INTERIM_APPROVED: "Interim Approved",
    ApprovalStatus.VALIDATION_IN_PROGRESS: "Validation In Progress",
    ApprovalStatus.EXPIRED: "Expired",
}


def compute_model_approval_status(
    model: Model,
    db: Session
) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Compute the current approval status for a model.

    Key Logic:
    - Models remain APPROVED throughout the revalidation window
    - Status only changes to VALIDATION_IN_PROGRESS or EXPIRED after the model is OVERDUE
    - VALIDATION_IN_PROGRESS requires both: (1) model is overdue AND (2) active validation
      in substantive stage (PLANNING or later, not INTAKE)
    - EXPIRED means model is overdue with no substantive validation work happening

    Returns:
        Tuple of (status_code, context_dict)
        - status_code: One of ApprovalStatus constants, or None for non-models
        - context_dict: Additional context about the determination
    """
    # Non-models (is_model=False) don't have approval status
    if hasattr(model, 'is_model') and not model.is_model:
        return None, {"reason": "Non-model entity"}

    context: Dict[str, Any] = {
        "model_id": model.model_id,
        "computed_at": utc_now(),
    }

    # Get most recent APPROVED validation
    latest_approved = _get_latest_approved_validation(model, db)
    if not latest_approved:
        return ApprovalStatus.NEVER_VALIDATED, context

    context["latest_approved_validation_id"] = latest_approved.request_id
    context["latest_approved_date"] = (
        latest_approved.completion_date or latest_approved.updated_at
    )
    context["validation_type_code"] = (
        latest_approved.validation_type.code if latest_approved.validation_type else None
    )
    context["validation_type_label"] = (
        latest_approved.validation_type.label if latest_approved.validation_type else None
    )

    # Check if all required approvals are complete on the approved validation
    approvals_complete, pending_count = _check_approvals_complete(latest_approved, model, db)
    context["approvals_complete"] = approvals_complete
    context["pending_approval_count"] = pending_count

    # Check if model is overdue for revalidation
    is_overdue, revalidation_context = _is_model_overdue(model, latest_approved, db)
    context["is_overdue"] = is_overdue
    context["next_validation_due"] = revalidation_context.get("next_validation_due")
    context["days_until_due"] = revalidation_context.get("days_until_validation_due")

    if not is_overdue:
        # Model is within revalidation window - stays APPROVED or INTERIM_APPROVED
        # regardless of whether a new validation has been started
        validation_type_code = context["validation_type_code"]
        if validation_type_code == "INTERIM":
            return ApprovalStatus.INTERIM_APPROVED, context
        return ApprovalStatus.APPROVED, context

    # Model is OVERDUE - now check if there's substantive validation work happening
    active_validation = _get_active_substantive_validation(model, db)
    context["active_validation_id"] = active_validation.request_id if active_validation else None
    context["active_validation_status"] = (
        active_validation.current_status.code if active_validation and active_validation.current_status else None
    )

    if active_validation:
        # Overdue but validation work is in progress
        return ApprovalStatus.VALIDATION_IN_PROGRESS, context

    # Overdue with no substantive validation work
    return ApprovalStatus.EXPIRED, context


def _get_latest_approved_validation(model: Model, db: Session) -> Optional[ValidationRequest]:
    """Get most recent APPROVED validation for model."""
    return db.query(ValidationRequest).join(
        ValidationRequestModelVersion
    ).filter(
        ValidationRequestModelVersion.model_id == model.model_id,
        ValidationRequest.current_status.has(TaxonomyValue.code == "APPROVED")
    ).order_by(
        ValidationRequest.completion_date.desc().nullslast(),
        ValidationRequest.updated_at.desc()
    ).first()


def _get_active_substantive_validation(model: Model, db: Session) -> Optional[ValidationRequest]:
    """
    Get active validation request in a substantive stage for model.

    Substantive stages are: PLANNING, ASSIGNED, IN_PROGRESS, REVIEW, PENDING_APPROVAL
    INTAKE stage does NOT count as substantive work has not begun.
    """
    # Statuses that indicate substantive validation work (beyond INTAKE)
    substantive_statuses = ["PLANNING", "ASSIGNED", "IN_PROGRESS", "REVIEW", "PENDING_APPROVAL"]

    return db.query(ValidationRequest).join(
        ValidationRequestModelVersion
    ).filter(
        ValidationRequestModelVersion.model_id == model.model_id,
        ValidationRequest.current_status.has(
            TaxonomyValue.code.in_(substantive_statuses)
        )
    ).order_by(
        ValidationRequest.created_at.desc()
    ).first()


def _is_model_overdue(
    model: Model,
    latest_approved: ValidationRequest,
    db: Session
) -> Tuple[bool, Dict[str, Any]]:
    """
    Check if model is overdue for revalidation.

    Uses the existing revalidation status calculation logic.
    Model is overdue if today > next_validation_due.
    """
    # Import here to avoid circular imports
    from app.api.validation_workflow import calculate_model_revalidation_status

    status = calculate_model_revalidation_status(model, db)

    # Extract relevant info
    today = date.today()
    next_validation_due = status.get("next_validation_due")

    context = {
        "revalidation_status": status.get("status"),
        "next_validation_due": next_validation_due,
        "days_until_validation_due": status.get("days_until_validation_due"),
    }

    # Check if overdue based on the status string or date comparison
    overdue_statuses = [
        "Submission Overdue",
        "Validation Overdue",
        "Revalidation Overdue (No Request)",
        "Should Create Request",
        "INTERIM Expired - Full Validation Required",
        "Submission Overdue (INTERIM)",
    ]

    if status.get("status") in overdue_statuses:
        return True, context

    # Also check date directly if available
    if next_validation_due and today > next_validation_due:
        return True, context

    return False, context


def _check_approvals_complete(
    validation: ValidationRequest,
    model: Model,
    db: Session
) -> Tuple[bool, int]:
    """
    Check if all required approvals are complete for a validation.

    Returns:
        Tuple of (all_complete, pending_count)
    """
    # Check traditional approvals (non-conditional)
    pending_traditional = db.query(ValidationApproval).filter(
        ValidationApproval.request_id == validation.request_id,
        ValidationApproval.is_required == True,
        ValidationApproval.approval_status == "Pending",
        ValidationApproval.voided_at.is_(None)  # Not voided
    ).count()

    # Check conditional approvals (via use_approval_date)
    # If conditional approvals were required but not complete, use_approval_date would be None
    conditional_complete = True
    if _has_conditional_approval_requirements(validation, db):
        conditional_complete = model.use_approval_date is not None

    pending_count = pending_traditional
    if not conditional_complete:
        # Count pending conditional approvals
        pending_conditional = db.query(ValidationApproval).filter(
            ValidationApproval.request_id == validation.request_id,
            ValidationApproval.approver_role_id.isnot(None),  # Conditional approval
            ValidationApproval.approval_status == "Pending",
            ValidationApproval.voided_at.is_(None)
        ).count()
        pending_count += pending_conditional

    all_complete = pending_traditional == 0 and conditional_complete
    return all_complete, pending_count


def _has_conditional_approval_requirements(
    validation: ValidationRequest,
    db: Session
) -> bool:
    """Check if this validation has any conditional approval requirements."""
    return db.query(ValidationApproval).filter(
        ValidationApproval.request_id == validation.request_id,
        ValidationApproval.approver_role_id.isnot(None)
    ).count() > 0


def record_status_change(
    model_id: int,
    old_status: Optional[str],
    new_status: str,
    trigger_type: str,
    db: Session,
    trigger_entity_type: Optional[str] = None,
    trigger_entity_id: Optional[int] = None,
    notes: Optional[str] = None
) -> ModelApprovalStatusHistory:
    """Record a status change to history."""
    history = ModelApprovalStatusHistory(
        model_id=model_id,
        old_status=old_status,
        new_status=new_status,
        trigger_type=trigger_type,
        trigger_entity_type=trigger_entity_type,
        trigger_entity_id=trigger_entity_id,
        notes=notes
    )
    db.add(history)
    return history


def get_last_recorded_status(model: Model, db: Session) -> Optional[str]:
    """Get the most recent recorded approval status for a model."""
    last_history = db.query(ModelApprovalStatusHistory).filter(
        ModelApprovalStatusHistory.model_id == model.model_id
    ).order_by(
        ModelApprovalStatusHistory.changed_at.desc()
    ).first()

    return last_history.new_status if last_history else None


def get_status_label(status_code: Optional[str]) -> Optional[str]:
    """Get human-readable label for status code."""
    if status_code is None:
        return None
    return STATUS_LABELS.get(status_code, status_code)


def update_model_approval_status_if_changed(
    model: Model,
    db: Session,
    trigger_type: str,
    trigger_entity_type: Optional[str] = None,
    trigger_entity_id: Optional[int] = None,
    notes: Optional[str] = None
) -> Optional[ModelApprovalStatusHistory]:
    """
    Recalculate model approval status and record if it changed.

    This is the main function to call from integration points (validation workflow,
    approval submissions, etc.) to update status when relevant events occur.

    Returns:
        The new history record if status changed, None otherwise
    """
    # Get current computed status
    new_status, context = compute_model_approval_status(model, db)

    # Skip if model doesn't have approval status (non-models)
    if new_status is None:
        return None

    # Get last recorded status
    old_status = get_last_recorded_status(model, db)

    # Only record if changed
    if old_status != new_status:
        return record_status_change(
            model_id=model.model_id,
            old_status=old_status,
            new_status=new_status,
            trigger_type=trigger_type,
            trigger_entity_type=trigger_entity_type,
            trigger_entity_id=trigger_entity_id,
            notes=notes,
            db=db
        )

    return None


def backfill_model_approval_status(db: Session) -> int:
    """
    Create initial history records for all existing models that don't have any.

    Returns:
        Number of records created
    """
    count = 0

    # Get all models (not checking is_model since field may not exist)
    models = db.query(Model).all()

    for model in models:
        # Check if already has history
        existing = db.query(ModelApprovalStatusHistory).filter(
            ModelApprovalStatusHistory.model_id == model.model_id
        ).first()

        if not existing:
            current_status, context = compute_model_approval_status(model, db)
            if current_status:
                record_status_change(
                    model_id=model.model_id,
                    old_status=None,
                    new_status=current_status,
                    trigger_type="BACKFILL",
                    notes="Initial status record created during migration",
                    db=db
                )
                count += 1

    db.commit()
    return count
