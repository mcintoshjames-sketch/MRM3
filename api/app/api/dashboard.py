"""Dashboard routes."""
from typing import List, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.model import Model
from app.models.model_submission_comment import ModelSubmissionComment
from app.models.decommissioning import DecommissioningStatusHistory, DecommissioningRequest
from app.models.monitoring import MonitoringCycle, MonitoringCycleApproval, MonitoringPlan, monitoring_plan_models
from app.models.validation import ValidationApproval, ValidationRequest, validation_request_models
from app.core.rls import apply_model_rls

router = APIRouter()


@router.get("/news-feed")
def get_news_feed(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get news feed for the dashboard.

    Returns recent activity (comments, status changes, monitoring cycles) for models the user has access to.
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
        ValidationApproval.approval_status.in_(["Approved", "Rejected"]),
        ValidationApproval.approved_at.isnot(None)
    ).order_by(ValidationApproval.approved_at.desc()).limit(50).all()

    # Add validation workflow approvals to feed
    for approval in validation_approvals:
        # Get model names for context
        model_names = [m.model_name for m in approval.request.models if m.model_id in accessible_model_ids]
        model_context = model_names[0] if len(model_names) == 1 else f"{len(model_names)} models"
        first_model_id = next((m.model_id for m in approval.request.models if m.model_id in accessible_model_ids), None)

        # Build approval description
        approval_status = "approved" if approval.approval_status == "Approved" else "rejected"
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
            "created_at": approval.approved_at
        })

    # Sort combined feed by created_at descending and limit to 50
    feed.sort(key=lambda x: x["created_at"], reverse=True)
    return feed[:50]


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
