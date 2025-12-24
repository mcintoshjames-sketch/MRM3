"""Dashboard routes."""
from typing import List, Any
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.model import Model
from app.models.model_submission_comment import ModelSubmissionComment
from app.models.decommissioning import DecommissioningStatusHistory, DecommissioningRequest
from app.models.monitoring import MonitoringCycle, MonitoringCycleApproval, MonitoringPlan, monitoring_plan_models
from app.models.validation import (
    ValidationApproval, ValidationRequest, validation_request_models,
    ValidationStatusHistory
)
from app.models.recommendation import Recommendation, RecommendationStatusHistory
from app.models.model_approval_status_history import ModelApprovalStatusHistory
from app.models.attestation import AttestationRecord
from app.models.model_version import ModelVersion
from app.models.model_exception import ModelException, ModelExceptionStatusHistory
from app.models.mrsa_review_policy import MRSAReviewPolicy, MRSAReviewException
from app.models.irp import IRP
from app.models.taxonomy import TaxonomyValue
from app.core.rls import apply_model_rls
from app.core.mrsa_review_utils import get_mrsa_review_details
from app.schemas.mrsa_review_policy import (
    MRSAReviewSummary, MRSAReviewStatus, MRSAReviewStatusEnum
)

router = APIRouter()


@router.get("/news-feed")
def get_news_feed(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get news feed for the dashboard.

    Returns recent activity for models the user has access to, including:
    - Comments and actions
    - Decommissioning status changes
    - Monitoring cycle completions and approvals
    - Validation workflow approvals and status changes
    - Recommendation status changes
    - Model approval status changes
    - Attestation submissions and reviews
    - Model version creations
    - Model exceptions (detected, acknowledged, closed)
    """
    # Get models user has access to
    models_query = db.query(Model)
    models_query = apply_model_rls(models_query, current_user, db)
    accessible_model_ids = [m.model_id for m in models_query.all()]

    if not accessible_model_ids:
        return []

    # Get recent comments/activities for these models
    comments = db.query(ModelSubmissionComment).options(
        joinedload(ModelSubmissionComment.user),
        joinedload(ModelSubmissionComment.model)
    ).filter(
        ModelSubmissionComment.model_id.in_(accessible_model_ids)
    ).order_by(ModelSubmissionComment.created_at.desc()).limit(50).all()

    # Get recent decommissioning status changes for accessible models
    decom_history = db.query(DecommissioningStatusHistory).options(
        joinedload(DecommissioningStatusHistory.changed_by),
        joinedload(DecommissioningStatusHistory.request).joinedload(DecommissioningRequest.model),
        joinedload(DecommissioningStatusHistory.request).joinedload(DecommissioningRequest.reason)
    ).join(DecommissioningRequest).filter(
        DecommissioningRequest.model_id.in_(accessible_model_ids)
    ).order_by(DecommissioningStatusHistory.changed_at.desc()).limit(50).all()

    # Format response
    feed = []
    for comment in comments:
        feed.append({
            "id": comment.comment_id,
            "type": "comment" if not comment.action_taken else "action",
            "action": comment.action_taken,
            "text": comment.comment_text,
            "user_name": comment.user.full_name,
            "model_name": comment.model.model_name,
            "model_id": comment.model_id,
            "entity_link": f"/models/{comment.model_id}",
            "created_at": comment.created_at
        })

    # Add decommissioning activity to feed
    for history in decom_history:
        action_text = _format_decom_action(history)
        feed.append({
            "id": f"decom_{history.history_id}",
            "type": "decommissioning",
            "action": history.new_status,
            "text": action_text,
            "user_name": history.changed_by.full_name,
            "model_name": history.request.model.model_name,
            "model_id": history.request.model_id,
            "entity_link": "/pending-decommissioning",
            "created_at": history.changed_at
        })

    # Get recent monitoring cycle completions for accessible models
    # Query cycles via the monitoring_plan_models association table
    monitoring_cycles = db.query(MonitoringCycle).options(
        joinedload(MonitoringCycle.plan).joinedload(MonitoringPlan.models),
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
        monitoring_plan_models.c.model_id.in_(accessible_model_ids)
    ).order_by(MonitoringCycle.updated_at.desc()).limit(50).all()

    # Add monitoring activity to feed
    for cycle in monitoring_cycles:
        plan_name = cycle.plan.name if cycle.plan else "Unknown Plan"
        period_text = f"{cycle.period_start_date} to {cycle.period_end_date}"

        # Get model names for context (may be multiple models in a plan)
        model_names = [m.model_name for m in cycle.plan.models if m.model_id in accessible_model_ids]
        model_context = model_names[0] if len(model_names) == 1 else f"{len(model_names)} models"
        first_model_id = next((m.model_id for m in cycle.plan.models if m.model_id in accessible_model_ids), None)

        # Add completed/approved cycles
        if cycle.status == "APPROVED" and cycle.completed_at:
            feed.append({
                "id": f"monitoring_cycle_{cycle.cycle_id}",
                "type": "monitoring",
                "action": "completed",
                "text": f"Monitoring cycle completed: {plan_name} ({period_text})",
                "user_name": cycle.completed_by.full_name if cycle.completed_by else None,
                "model_name": model_context,
                "model_id": first_model_id,
                "entity_link": f"/monitoring/cycles/{cycle.cycle_id}",
                "created_at": cycle.completed_at
            })

        # Add individual approvals
        for approval in cycle.approvals:
            if approval.approved_at and approval.approval_status in ["Approved", "Rejected"]:
                region_text = f" ({approval.region.name})" if approval.region else ""
                approval_status = "approved" if approval.approval_status == "Approved" else "rejected"
                feed.append({
                    "id": f"monitoring_approval_{approval.approval_id}",
                    "type": "monitoring",
                    "action": approval_status,
                    "text": f"Monitoring {approval.approval_type}{region_text} {approval_status}: {plan_name}",
                    "user_name": approval.approver.full_name if approval.approver else None,
                    "model_name": model_context,
                    "model_id": first_model_id,
                    "entity_link": f"/monitoring/cycles/{cycle.cycle_id}",
                    "created_at": approval.approved_at
                })

    # Get recent validation workflow approvals for accessible models
    validation_approvals = db.query(ValidationApproval).options(
        joinedload(ValidationApproval.approver),
        joinedload(ValidationApproval.request).joinedload(ValidationRequest.models),
        joinedload(ValidationApproval.represented_region)
    ).join(
        ValidationRequest, ValidationApproval.request_id == ValidationRequest.request_id
    ).join(
        validation_request_models,
        ValidationRequest.request_id == validation_request_models.c.request_id
    ).filter(
        validation_request_models.c.model_id.in_(accessible_model_ids),
        ValidationApproval.approval_status.in_(["Approved", "Rejected", "Sent Back"]),
        ValidationApproval.approved_at.isnot(None)
    ).order_by(ValidationApproval.approved_at.desc()).limit(50).all()

    # Add validation workflow approvals to feed
    for approval in validation_approvals:
        # Get model names for context
        model_names = [m.model_name for m in approval.request.models if m.model_id in accessible_model_ids]
        model_context = model_names[0] if len(model_names) == 1 else f"{len(model_names)} models"
        first_model_id = next((m.model_id for m in approval.request.models if m.model_id in accessible_model_ids), None)

        # Build approval description
        # Map status to display action (keeping "rejected" for historical records)
        if approval.approval_status == "Approved":
            approval_status = "approved"
        elif approval.approval_status == "Sent Back":
            approval_status = "sent_back"
        else:
            approval_status = "rejected"
        role_text = approval.approver_role or "Approver"

        # Only add region if not already in the role text
        if approval.represented_region and approval.represented_region.code not in role_text:
            role_text = f"{role_text} ({approval.represented_region.name})"

        feed.append({
            "id": f"validation_approval_{approval.approval_id}",
            "type": "validation",
            "action": approval_status,
            "text": f"Validation {role_text} {approval_status}",
            "user_name": approval.approver.full_name if approval.approver else None,
            "model_name": model_context,
            "model_id": first_model_id,
            "entity_link": f"/validation-workflow/{approval.request_id}",
            "created_at": approval.approved_at
        })

    # =========================================================================
    # RECOMMENDATION STATUS CHANGES (P1 - Critical)
    # =========================================================================
    recommendation_events = db.query(RecommendationStatusHistory).options(
        joinedload(RecommendationStatusHistory.recommendation).joinedload(Recommendation.model),
        joinedload(RecommendationStatusHistory.changed_by),
        joinedload(RecommendationStatusHistory.old_status),
        joinedload(RecommendationStatusHistory.new_status)
    ).join(Recommendation).filter(
        Recommendation.model_id.in_(accessible_model_ids)
    ).order_by(RecommendationStatusHistory.changed_at.desc()).limit(50).all()

    for event in recommendation_events:
        rec = event.recommendation
        old_status_label = event.old_status.label if event.old_status else "Created"
        new_status_label = event.new_status.label if event.new_status else "Unknown"
        feed.append({
            "id": f"recommendation_{event.history_id}",
            "type": "recommendation",
            "action": new_status_label.lower().replace(" ", "_"),
            "text": f"Recommendation {rec.recommendation_code}: {old_status_label} → {new_status_label}",
            "user_name": event.changed_by.full_name if event.changed_by else None,
            "model_name": rec.model.model_name,
            "model_id": rec.model_id,
            "entity_link": f"/recommendations/{rec.recommendation_id}",
            "created_at": event.changed_at
        })

    # =========================================================================
    # VALIDATION STATUS CHANGES (P2 - High)
    # Note: This captures workflow progress, not just final approvals
    # =========================================================================
    validation_status_events = db.query(ValidationStatusHistory).options(
        joinedload(ValidationStatusHistory.request).joinedload(ValidationRequest.models),
        joinedload(ValidationStatusHistory.changed_by),
        joinedload(ValidationStatusHistory.old_status),
        joinedload(ValidationStatusHistory.new_status)
    ).join(ValidationRequest).join(
        validation_request_models,
        ValidationRequest.request_id == validation_request_models.c.request_id
    ).filter(
        validation_request_models.c.model_id.in_(accessible_model_ids)
    ).order_by(ValidationStatusHistory.changed_at.desc()).limit(50).all()

    for event in validation_status_events:
        model_names = [m.model_name for m in event.request.models if m.model_id in accessible_model_ids]
        model_context = model_names[0] if len(model_names) == 1 else f"{len(model_names)} models"
        first_model_id = next((m.model_id for m in event.request.models if m.model_id in accessible_model_ids), None)

        old_status_label = event.old_status.label if event.old_status else "Created"
        new_status_label = event.new_status.label if event.new_status else "Unknown"

        feed.append({
            "id": f"validation_status_{event.history_id}",
            "type": "validation_status",
            "action": new_status_label.lower().replace(" ", "_"),
            "text": f"Validation status: {old_status_label} → {new_status_label}",
            "user_name": event.changed_by.full_name if event.changed_by else None,
            "model_name": model_context,
            "model_id": first_model_id,
            "entity_link": f"/validation-workflow/{event.request.request_id}",
            "created_at": event.changed_at
        })

    # =========================================================================
    # MODEL APPROVAL STATUS CHANGES (P3 - Medium)
    # =========================================================================
    approval_status_events = db.query(ModelApprovalStatusHistory).options(
        joinedload(ModelApprovalStatusHistory.model)
    ).filter(
        ModelApprovalStatusHistory.model_id.in_(accessible_model_ids)
    ).order_by(ModelApprovalStatusHistory.changed_at.desc()).limit(50).all()

    for event in approval_status_events:
        old_status = event.old_status
        new_status = event.new_status
        # Format status text - if no old status, just show "set to X"
        if old_status:
            status_text = f"Model approval status: {old_status} → {new_status}"
        else:
            status_text = f"Model approval status set to {new_status}"
        feed.append({
            "id": f"approval_status_{event.history_id}",
            "type": "approval_status",
            "action": new_status.lower(),
            "text": status_text,
            "user_name": "System",  # System-triggered events
            "model_name": event.model.model_name,
            "model_id": event.model_id,
            "entity_link": f"/models/{event.model_id}",
            "created_at": event.changed_at
        })

    # =========================================================================
    # ATTESTATION EVENTS (P4 - Medium)
    # =========================================================================
    attestation_events = db.query(AttestationRecord).options(
        joinedload(AttestationRecord.model),
        joinedload(AttestationRecord.attesting_user),
        joinedload(AttestationRecord.reviewed_by),
        joinedload(AttestationRecord.cycle)
    ).filter(
        AttestationRecord.model_id.in_(accessible_model_ids)
    ).order_by(AttestationRecord.updated_at.desc()).limit(50).all()

    for record in attestation_events:
        cycle_name = record.cycle.cycle_name if record.cycle else "Unknown Cycle"
        # Submission event
        if record.attested_at:
            feed.append({
                "id": f"attestation_submit_{record.attestation_id}",
                "type": "attestation",
                "action": "submitted",
                "text": f"Attestation submitted for {cycle_name}",
                "user_name": record.attesting_user.full_name if record.attesting_user else None,
                "model_name": record.model.model_name,
                "model_id": record.model_id,
                "entity_link": f"/attestations/{record.attestation_id}",
                "created_at": record.attested_at
            })
        # Admin review event
        if record.reviewed_at:
            review_action = "accepted" if record.status == "ACCEPTED" else "reviewed"
            feed.append({
                "id": f"attestation_review_{record.attestation_id}",
                "type": "attestation",
                "action": review_action,
                "text": f"Attestation {review_action} for {cycle_name}",
                "user_name": record.reviewed_by.full_name if record.reviewed_by else None,
                "model_name": record.model.model_name,
                "model_id": record.model_id,
                "entity_link": f"/attestations/{record.attestation_id}",
                "created_at": record.reviewed_at
            })

    # =========================================================================
    # MODEL VERSION EVENTS (P5 - Lower)
    # =========================================================================
    version_events = db.query(ModelVersion).options(
        joinedload(ModelVersion.model),
        joinedload(ModelVersion.created_by)
    ).filter(
        ModelVersion.model_id.in_(accessible_model_ids)
    ).order_by(ModelVersion.created_at.desc()).limit(50).all()

    for version in version_events:
        feed.append({
            "id": f"version_{version.version_id}",
            "type": "version",
            "action": "created",
            "text": f"Version {version.version_number} created: {version.change_type}",
            "user_name": version.created_by.full_name if version.created_by else None,
            "model_name": version.model.model_name,
            "model_id": version.model_id,
            "entity_link": f"/models/{version.model_id}/versions/{version.version_id}",
            "created_at": version.created_at
        })

    # =========================================================================
    # MODEL EXCEPTION EVENTS (P6 - Risk Alerts)
    # =========================================================================
    exception_events = db.query(ModelException).options(
        joinedload(ModelException.model),
        joinedload(ModelException.acknowledged_by),
        joinedload(ModelException.closed_by)
    ).filter(
        ModelException.model_id.in_(accessible_model_ids)
    ).order_by(ModelException.detected_at.desc()).limit(50).all()

    exception_type_labels = {
        "UNMITIGATED_PERFORMANCE": "Unmitigated Performance Problem",
        "OUTSIDE_INTENDED_PURPOSE": "Model Used Outside Intended Purpose",
        "USE_PRIOR_TO_VALIDATION": "Model In Use Prior to Full Validation"
    }

    for exc in exception_events:
        type_label = exception_type_labels.get(exc.exception_type, exc.exception_type)

        # Exception detected event
        feed.append({
            "id": f"exception_detected_{exc.exception_id}",
            "type": "exception",
            "action": "detected",
            "text": f"Exception detected: {type_label}",
            "user_name": "System",  # Auto-detected
            "model_name": exc.model.model_name,
            "model_id": exc.model_id,
            "entity_link": f"/models/{exc.model_id}",
            "created_at": exc.detected_at
        })

        # Exception acknowledged event
        if exc.acknowledged_at:
            feed.append({
                "id": f"exception_acknowledged_{exc.exception_id}",
                "type": "exception",
                "action": "acknowledged",
                "text": f"Exception {exc.exception_code} acknowledged",
                "user_name": exc.acknowledged_by.full_name if exc.acknowledged_by else None,
                "model_name": exc.model.model_name,
                "model_id": exc.model_id,
                "entity_link": f"/models/{exc.model_id}",
                "created_at": exc.acknowledged_at
            })

        # Exception closed event
        if exc.closed_at:
            close_method = "auto-closed" if exc.auto_closed else "closed"
            feed.append({
                "id": f"exception_closed_{exc.exception_id}",
                "type": "exception",
                "action": close_method,
                "text": f"Exception {exc.exception_code} {close_method}",
                "user_name": exc.closed_by.full_name if exc.closed_by else "System",
                "model_name": exc.model.model_name,
                "model_id": exc.model_id,
                "entity_link": f"/models/{exc.model_id}",
                "created_at": exc.closed_at
            })

    # Sort combined feed by created_at descending and limit to 50
    feed.sort(key=lambda x: x["created_at"], reverse=True)
    return feed[:50]


# ============================================================================
# MRSA Review Dashboard Endpoints
# ============================================================================

@router.get("/mrsa-reviews/summary", response_model=MRSAReviewSummary)
def get_mrsa_reviews_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get summary counts of MRSA review statuses.

    Returns counts grouped by status:
    - CURRENT: Reviews not yet due
    - UPCOMING: Due within warning period
    - OVERDUE: Past due date
    - NO_IRP: Requires IRP but has no coverage
    - NEVER_REVIEWED: No reviews recorded
    - NO_REQUIREMENT: No review policy applies
    """
    today = date.today()

    # Get all MRSAs with necessary relationships eagerly loaded
    mrsas = db.query(Model).options(
        joinedload(Model.mrsa_risk_level),
        joinedload(Model.owner),
        joinedload(Model.irps).joinedload(IRP.reviews)
    ).filter(Model.is_mrsa == True).all()

    # Initialize counters
    counts = {
        "total_count": len(mrsas),
        "current_count": 0,
        "upcoming_count": 0,
        "overdue_count": 0,
        "no_irp_count": 0,
        "never_reviewed_count": 0,
        "no_requirement_count": 0
    }

    # Count by status
    for mrsa in mrsas:
        review_details = get_mrsa_review_details(mrsa, db, today)
        status = review_details["status"]

        if status == MRSAReviewStatusEnum.CURRENT:
            counts["current_count"] += 1
        elif status == MRSAReviewStatusEnum.UPCOMING:
            counts["upcoming_count"] += 1
        elif status == MRSAReviewStatusEnum.OVERDUE:
            counts["overdue_count"] += 1
        elif status == MRSAReviewStatusEnum.NO_IRP:
            counts["no_irp_count"] += 1
        elif status == MRSAReviewStatusEnum.NEVER_REVIEWED:
            counts["never_reviewed_count"] += 1
        elif status == MRSAReviewStatusEnum.NO_REQUIREMENT:
            counts["no_requirement_count"] += 1

    return MRSAReviewSummary(**counts)


@router.get("/mrsa-reviews/upcoming", response_model=List[MRSAReviewStatus])
def get_mrsa_reviews_upcoming(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get MRSAs with reviews due within warning period.

    Returns MRSAs in UPCOMING status, sorted by days_until_due (ascending).
    """
    today = date.today()

    # Get all MRSAs with necessary relationships eagerly loaded
    mrsas = db.query(Model).options(
        joinedload(Model.mrsa_risk_level),
        joinedload(Model.owner),
        joinedload(Model.irps).joinedload(IRP.reviews)
    ).filter(Model.is_mrsa == True).all()

    # Filter to upcoming only
    upcoming = []
    for mrsa in mrsas:
        review_details = get_mrsa_review_details(mrsa, db, today)
        if review_details["status"] == MRSAReviewStatusEnum.UPCOMING:
            upcoming.append(MRSAReviewStatus(**review_details))

    # Sort by days_until_due (ascending - soonest first)
    upcoming.sort(key=lambda x: x.days_until_due if x.days_until_due is not None else 999999)

    return upcoming


@router.get("/mrsa-reviews/overdue", response_model=List[MRSAReviewStatus])
def get_mrsa_reviews_overdue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get overdue/no-coverage MRSAs.

    Returns MRSAs with past-due review dates or missing IRP coverage,
    sorted by severity then by days overdue (worst first).
    """
    today = date.today()

    # Get all MRSAs with necessary relationships eagerly loaded
    mrsas = db.query(Model).options(
        joinedload(Model.mrsa_risk_level),
        joinedload(Model.owner),
        joinedload(Model.irps).joinedload(IRP.reviews)
    ).filter(Model.is_mrsa == True).all()

    problems = []
    for mrsa in mrsas:
        review_details = get_mrsa_review_details(mrsa, db, today)
        status = review_details["status"]
        days_until_due = review_details["days_until_due"]

        if status == MRSAReviewStatusEnum.NO_IRP:
            problems.append(MRSAReviewStatus(**review_details))
            continue

        if days_until_due is not None and days_until_due < 0:
            problems.append(MRSAReviewStatus(**review_details))

    # Sort by severity then by days overdue
    # Severity order: NO_IRP > NEVER_REVIEWED > OVERDUE
    severity_order = {
        MRSAReviewStatusEnum.NO_IRP: 0,
        MRSAReviewStatusEnum.NEVER_REVIEWED: 1,
        MRSAReviewStatusEnum.OVERDUE: 2
    }

    problems.sort(key=lambda x: (
        severity_order.get(x.status, 999),
        x.days_until_due if x.days_until_due is not None else 0  # More negative = worse
    ))

    return problems


def _format_decom_action(history: DecommissioningStatusHistory) -> str:
    """Format decommissioning status change as readable text."""
    new_status = history.new_status
    old_status = history.old_status
    reason_label = history.request.reason.label if history.request.reason else "Unknown"
    notes = history.notes or ""

    if old_status is None:
        # Initial creation
        return f"Decommissioning request created (Reason: {reason_label})"
    elif new_status == "VALIDATOR_APPROVED":
        # Check notes to determine if this was triggered by owner or validator
        if "Model owner approved" in notes:
            return "Stage 1 complete: model owner approved (validator previously approved)"
        else:
            return "Stage 1 complete: validator approved"
    elif new_status == "APPROVED":
        return "Decommissioning request fully approved"
    elif new_status == "REJECTED":
        return "Decommissioning request rejected"
    elif new_status == "WITHDRAWN":
        return "Decommissioning request withdrawn"
    elif old_status == new_status:
        # Status unchanged - could be partial approval (awaiting other party) or update
        if "Validator approved" in notes:
            return "Validator approved (awaiting model owner approval)"
        elif "Model owner approved" in notes:
            return "Model owner approved (awaiting validator approval)"
        return notes if notes else "Decommissioning request updated"
    else:
        return f"Decommissioning status changed: {old_status} → {new_status}"
