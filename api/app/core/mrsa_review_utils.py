"""MRSA Review calculation utilities.

Shared logic for calculating MRSA review status, due dates, and compliance.
"""
from datetime import date, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from app.models.model import Model
from app.models.mrsa_review_policy import MRSAReviewPolicy, MRSAReviewException
from app.models.irp import IRP, IRPReview
from app.schemas.mrsa_review_policy import MRSAReviewStatusEnum


def calculate_mrsa_review_status(
    mrsa: Model,
    policy: Optional[MRSAReviewPolicy],
    exception: Optional[MRSAReviewException],
    latest_irp_review_date: Optional[date],
    today: Optional[date] = None
) -> Tuple[MRSAReviewStatusEnum, Optional[date], Optional[int]]:
    """Calculate MRSA review status and next due date.

    Args:
        mrsa: The MRSA model to evaluate
        policy: Active review policy for this MRSA's risk level (if any)
        exception: Active exception granting extended due date (if any)
        latest_irp_review_date: Date of most recent IRP review (if any)
        today: Current date (defaults to date.today())

    Returns:
        Tuple of (status, next_due_date, days_until_due)
    """
    if today is None:
        today = date.today()

    # NO_REQUIREMENT: No review policy applies to this risk level
    if not policy or not policy.is_active:
        return (MRSAReviewStatusEnum.NO_REQUIREMENT, None, None)

    # NO_IRP: Requires IRP but has no coverage
    requires_irp = False
    if mrsa.mrsa_risk_level and mrsa.mrsa_risk_level.requires_irp:
        requires_irp = True

    if requires_irp and len(mrsa.irps) == 0:
        return (MRSAReviewStatusEnum.NO_IRP, None, None)

    # Get MRSA designation date (use mrsa_designated_date if available, otherwise created_at)
    designation_date = getattr(mrsa, 'mrsa_designated_date', None) or mrsa.created_at.date()

    # Calculate next due date
    if exception and exception.is_active:
        next_due_date = exception.override_due_date
    else:
        if latest_irp_review_date:
            next_due_date = latest_irp_review_date + timedelta(days=policy.frequency_months * 30)
        elif designation_date:
            next_due_date = designation_date + timedelta(days=policy.initial_review_months * 30)
        else:
            return (MRSAReviewStatusEnum.NEVER_REVIEWED, None, None)

    days_until_due = (next_due_date - today).days

    if not latest_irp_review_date:
        if days_until_due < 0:
            return (MRSAReviewStatusEnum.OVERDUE, next_due_date, days_until_due)
        return (MRSAReviewStatusEnum.NEVER_REVIEWED, next_due_date, days_until_due)

    if days_until_due < 0:
        return (MRSAReviewStatusEnum.OVERDUE, next_due_date, days_until_due)
    if days_until_due <= policy.warning_days:
        return (MRSAReviewStatusEnum.UPCOMING, next_due_date, days_until_due)
    return (MRSAReviewStatusEnum.CURRENT, next_due_date, days_until_due)


def get_mrsa_review_details(mrsa: Model, db: Session, today: Optional[date] = None) -> dict:
    """Get comprehensive review status details for a single MRSA.

    Args:
        mrsa: The MRSA model to evaluate
        db: Database session
        today: Current date (defaults to date.today())

    Returns:
        Dictionary with status, dates, and related metadata
    """
    if today is None:
        today = date.today()

    # Get active policy for this MRSA's risk level
    policy = None
    if mrsa.mrsa_risk_level_id:
        policy = db.query(MRSAReviewPolicy).filter(
            MRSAReviewPolicy.mrsa_risk_level_id == mrsa.mrsa_risk_level_id,
            MRSAReviewPolicy.is_active == True
        ).first()

    # Get active exception
    exception = db.query(MRSAReviewException).filter(
        MRSAReviewException.mrsa_id == mrsa.model_id,
        MRSAReviewException.is_active == True
    ).first()

    # Get latest IRP review date
    latest_irp_review_date = None
    if mrsa.irps:
        # Find the most recent review across all IRPs covering this MRSA
        for irp in mrsa.irps:
            if irp.latest_review and irp.latest_review.review_date:
                if latest_irp_review_date is None or irp.latest_review.review_date > latest_irp_review_date:
                    latest_irp_review_date = irp.latest_review.review_date

    # Calculate status
    status, next_due_date, days_until_due = calculate_mrsa_review_status(
        mrsa=mrsa,
        policy=policy,
        exception=exception,
        latest_irp_review_date=latest_irp_review_date,
        today=today
    )

    return {
        "mrsa_id": mrsa.model_id,
        "mrsa_name": mrsa.model_name,
        "risk_level": mrsa.mrsa_risk_level.label if mrsa.mrsa_risk_level else None,
        "last_review_date": latest_irp_review_date,
        "next_due_date": next_due_date,
        "status": status,
        "days_until_due": days_until_due,
        "owner": {
            "user_id": mrsa.owner.user_id,
            "full_name": mrsa.owner.full_name,
            "email": mrsa.owner.email
        } if mrsa.owner else None,
        "has_exception": exception is not None and exception.is_active,
        "exception_due_date": exception.override_due_date if exception and exception.is_active else None,
    }
