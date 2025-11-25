"""
Overdue Revalidation Report API

This endpoint generates a comprehensive report showing all overdue items:
- Models past submission due date (PRE_SUBMISSION overdue)
- Validations past completion due date (VALIDATION_IN_PROGRESS overdue)
- Commentary status for each item (Current/Stale/Missing)
- Responsible party information
- Target dates from commentary

Key Features:
- Combined view of submission and validation overdue items
- Commentary tracking with staleness detection
- Filtering by type, risk tier, owner, and commentary status
- Exportable to CSV for regulatory reporting
"""
from typing import List, Optional
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.model import Model
from app.models.taxonomy import TaxonomyValue
from app.models.validation import (
    ValidationRequest, ValidationRequestModelVersion,
    ValidationAssignment, ValidationWorkflowSLA
)
from app.api.validation_workflow import get_commentary_status_for_request

router = APIRouter(prefix="/overdue-revalidation-report", tags=["Reports"])


def check_admin(user: User):
    """Check if user has Admin role."""
    if user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can perform this action"
        )


class OverdueRevalidationRecord(BaseModel):
    """Single record in the overdue revalidation report."""
    # Overdue Type
    overdue_type: str = Field(..., description="PRE_SUBMISSION or VALIDATION_IN_PROGRESS")

    # Request Information
    request_id: int
    validation_type: Optional[str] = None

    # Model Information
    model_id: int
    model_name: str
    risk_tier: Optional[str] = None

    # Ownership Information
    model_owner_id: Optional[int] = None
    model_owner_name: Optional[str] = None
    model_owner_email: Optional[str] = None
    model_developer_name: Optional[str] = None

    # Validator Information (for VALIDATION_IN_PROGRESS)
    primary_validator_id: Optional[int] = None
    primary_validator_name: Optional[str] = None
    primary_validator_email: Optional[str] = None

    # Due Date Information
    due_date: Optional[date] = Field(None, description="Original due date")
    grace_period_end: Optional[date] = Field(None, description="Grace period end (for submissions)")
    days_overdue: int = Field(0, description="Days past due date")
    urgency: str = Field("overdue", description="overdue or in_grace_period")

    # Current Status
    current_status: str
    current_status_code: Optional[str] = None

    # Commentary Status
    comment_status: str = Field("MISSING", description="CURRENT, STALE, or MISSING")
    latest_comment: Optional[str] = None
    latest_comment_date: Optional[datetime] = None
    latest_comment_by: Optional[str] = None
    target_date_from_comment: Optional[date] = None
    stale_reason: Optional[str] = None
    needs_comment_update: bool = Field(True, description="True if commentary needs attention")

    # Computed Completion Date
    computed_completion_date: Optional[date] = Field(
        None, description="Estimated completion based on target + lead time"
    )

    class Config:
        from_attributes = True


class OverdueRevalidationReportResponse(BaseModel):
    """Complete overdue revalidation report."""
    report_generated_at: datetime
    filters_applied: dict
    summary: dict
    total_records: int
    records: List[OverdueRevalidationRecord]


@router.get("/", response_model=OverdueRevalidationReportResponse)
def get_overdue_revalidation_report(
    overdue_type: Optional[str] = Query(None, description="Filter: PRE_SUBMISSION or VALIDATION_IN_PROGRESS"),
    risk_tier: Optional[str] = Query(None, description="Filter by risk tier code"),
    comment_status: Optional[str] = Query(None, description="Filter: CURRENT, STALE, or MISSING"),
    owner_id: Optional[int] = Query(None, description="Filter by model owner ID"),
    days_overdue_min: Optional[int] = Query(None, description="Minimum days overdue"),
    needs_update_only: bool = Query(False, description="Show only items needing commentary update"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate Overdue Revalidation Report.

    **REGULATORY QUESTION:**
    "Show me all overdue model revalidations with their delay explanations,
    target dates, and responsible parties."

    This report combines:
    - Overdue submissions (past submission_due_date or grace period)
    - Overdue validations (past model_validation_due_date)
    """
    check_admin(current_user)

    today = date.today()
    results = []

    # Get SLA config for lead time calculation
    sla_config = db.query(ValidationWorkflowSLA).first()
    lead_time_days = sla_config.model_change_lead_time_days if sla_config else 90

    # =====================================================
    # Part 1: Get PRE_SUBMISSION overdue items
    # =====================================================
    if overdue_type is None or overdue_type == "PRE_SUBMISSION":
        pre_submission_requests = db.query(ValidationRequest).options(
            joinedload(ValidationRequest.model_versions_assoc).joinedload(
                ValidationRequestModelVersion.model
            ).joinedload(Model.owner),
            joinedload(ValidationRequest.model_versions_assoc).joinedload(
                ValidationRequestModelVersion.model
            ).joinedload(Model.developer),
            joinedload(ValidationRequest.model_versions_assoc).joinedload(
                ValidationRequestModelVersion.model
            ).joinedload(Model.risk_tier),
            joinedload(ValidationRequest.current_status),
            joinedload(ValidationRequest.validation_type)
        ).filter(
            ValidationRequest.validation_type.has(
                TaxonomyValue.code.in_(["COMPREHENSIVE", "ANNUAL"])),
            ValidationRequest.submission_received_date.is_(None),
            ValidationRequest.current_status.has(
                TaxonomyValue.code.in_(["INTAKE", "PLANNING"]))
        ).all()

        for req in pre_submission_requests:
            # Check if past due
            is_past_due = req.submission_due_date and today > req.submission_due_date
            is_past_grace = req.submission_grace_period_end and today > req.submission_grace_period_end

            if not (is_past_due or is_past_grace):
                continue

            # Get model info
            if not req.model_versions_assoc:
                continue
            model_assoc = req.model_versions_assoc[0]
            model = model_assoc.model

            # Apply filters
            if risk_tier and (not model.risk_tier or model.risk_tier.code != risk_tier):
                continue
            if owner_id and model.owner_id != owner_id:
                continue

            # Calculate days overdue and urgency
            if is_past_grace:
                days_overdue = (today - req.submission_grace_period_end).days
                urgency = "overdue"
            else:
                days_overdue = (today - req.submission_due_date).days
                urgency = "in_grace_period"

            if days_overdue_min and days_overdue < days_overdue_min:
                continue

            # Get commentary status
            commentary = get_commentary_status_for_request(db, req.request_id, "PRE_SUBMISSION")

            # Apply comment_status filter
            if comment_status and commentary["comment_status"] != comment_status:
                continue
            if needs_update_only and not commentary["needs_comment_update"]:
                continue

            # Compute completion date
            computed_completion = None
            if commentary["target_date_from_comment"]:
                computed_completion = commentary["target_date_from_comment"] + timedelta(days=lead_time_days)

            record = OverdueRevalidationRecord(
                overdue_type="PRE_SUBMISSION",
                request_id=req.request_id,
                validation_type=req.validation_type.label if req.validation_type else None,
                model_id=model.model_id,
                model_name=model.model_name,
                risk_tier=model.risk_tier.label if model.risk_tier else None,
                model_owner_id=model.owner_id,
                model_owner_name=model.owner.full_name if model.owner else None,
                model_owner_email=model.owner.email if model.owner else None,
                model_developer_name=model.developer.full_name if model.developer else None,
                primary_validator_id=None,
                primary_validator_name=None,
                primary_validator_email=None,
                due_date=req.submission_due_date,
                grace_period_end=req.submission_grace_period_end,
                days_overdue=days_overdue,
                urgency=urgency,
                current_status=req.current_status.label if req.current_status else "Unknown",
                current_status_code=req.current_status.code if req.current_status else None,
                comment_status=commentary["comment_status"],
                latest_comment=commentary["latest_comment"],
                latest_comment_date=commentary["latest_comment_date"],
                latest_comment_by=commentary.get("latest_comment_by"),
                target_date_from_comment=commentary["target_date_from_comment"],
                stale_reason=commentary["stale_reason"],
                needs_comment_update=commentary["needs_comment_update"],
                computed_completion_date=computed_completion
            )
            results.append(record)

    # =====================================================
    # Part 2: Get VALIDATION_IN_PROGRESS overdue items
    # =====================================================
    if overdue_type is None or overdue_type == "VALIDATION_IN_PROGRESS":
        in_progress_requests = db.query(ValidationRequest).options(
            joinedload(ValidationRequest.model_versions_assoc).joinedload(
                ValidationRequestModelVersion.model
            ).joinedload(Model.owner),
            joinedload(ValidationRequest.model_versions_assoc).joinedload(
                ValidationRequestModelVersion.model
            ).joinedload(Model.developer),
            joinedload(ValidationRequest.model_versions_assoc).joinedload(
                ValidationRequestModelVersion.model
            ).joinedload(Model.risk_tier),
            joinedload(ValidationRequest.current_status),
            joinedload(ValidationRequest.validation_type),
            joinedload(ValidationRequest.assignments).joinedload(ValidationAssignment.validator)
        ).filter(
            ValidationRequest.validation_type.has(
                TaxonomyValue.code.in_(["COMPREHENSIVE", "ANNUAL"])),
            ValidationRequest.current_status.has(
                TaxonomyValue.code.notin_(["APPROVED", "CANCELLED"]))
        ).all()

        for req in in_progress_requests:
            # Check if past validation due
            if not (req.model_validation_due_date and today > req.model_validation_due_date):
                continue

            # Get model info
            if not req.model_versions_assoc:
                continue
            model_assoc = req.model_versions_assoc[0]
            model = model_assoc.model

            # Apply filters
            if risk_tier and (not model.risk_tier or model.risk_tier.code != risk_tier):
                continue
            if owner_id and model.owner_id != owner_id:
                continue

            days_overdue = (today - req.model_validation_due_date).days

            if days_overdue_min and days_overdue < days_overdue_min:
                continue

            # Get primary validator
            primary_validator = None
            for assignment in req.assignments:
                if assignment.is_primary:
                    primary_validator = assignment.validator
                    break

            # Get commentary status
            commentary = get_commentary_status_for_request(db, req.request_id, "VALIDATION_IN_PROGRESS")

            # Apply comment_status filter
            if comment_status and commentary["comment_status"] != comment_status:
                continue
            if needs_update_only and not commentary["needs_comment_update"]:
                continue

            record = OverdueRevalidationRecord(
                overdue_type="VALIDATION_IN_PROGRESS",
                request_id=req.request_id,
                validation_type=req.validation_type.label if req.validation_type else None,
                model_id=model.model_id,
                model_name=model.model_name,
                risk_tier=model.risk_tier.label if model.risk_tier else None,
                model_owner_id=model.owner_id,
                model_owner_name=model.owner.full_name if model.owner else None,
                model_owner_email=model.owner.email if model.owner else None,
                model_developer_name=model.developer.full_name if model.developer else None,
                primary_validator_id=primary_validator.user_id if primary_validator else None,
                primary_validator_name=primary_validator.full_name if primary_validator else None,
                primary_validator_email=primary_validator.email if primary_validator else None,
                due_date=req.model_validation_due_date,
                grace_period_end=None,
                days_overdue=days_overdue,
                urgency="overdue",
                current_status=req.current_status.label if req.current_status else "Unknown",
                current_status_code=req.current_status.code if req.current_status else None,
                comment_status=commentary["comment_status"],
                latest_comment=commentary["latest_comment"],
                latest_comment_date=commentary["latest_comment_date"],
                latest_comment_by=commentary.get("latest_comment_by"),
                target_date_from_comment=commentary["target_date_from_comment"],
                stale_reason=commentary["stale_reason"],
                needs_comment_update=commentary["needs_comment_update"],
                computed_completion_date=req.target_completion_date
            )
            results.append(record)

    # Sort by days_overdue descending (most urgent first)
    results.sort(key=lambda x: x.days_overdue, reverse=True)

    # Calculate summary stats
    summary = {
        "total_overdue": len(results),
        "pre_submission_overdue": len([r for r in results if r.overdue_type == "PRE_SUBMISSION"]),
        "validation_overdue": len([r for r in results if r.overdue_type == "VALIDATION_IN_PROGRESS"]),
        "missing_commentary": len([r for r in results if r.comment_status == "MISSING"]),
        "stale_commentary": len([r for r in results if r.comment_status == "STALE"]),
        "current_commentary": len([r for r in results if r.comment_status == "CURRENT"]),
        "needs_attention": len([r for r in results if r.needs_comment_update]),
        "average_days_overdue": round(sum(r.days_overdue for r in results) / len(results), 1) if results else 0,
        "max_days_overdue": max((r.days_overdue for r in results), default=0)
    }

    return OverdueRevalidationReportResponse(
        report_generated_at=datetime.now(),
        filters_applied={
            "overdue_type": overdue_type,
            "risk_tier": risk_tier,
            "comment_status": comment_status,
            "owner_id": owner_id,
            "days_overdue_min": days_overdue_min,
            "needs_update_only": needs_update_only
        },
        summary=summary,
        total_records=len(results),
        records=results
    )
