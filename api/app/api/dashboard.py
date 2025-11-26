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
from app.core.rls import apply_model_rls

router = APIRouter()


@router.get("/news-feed")
def get_news_feed(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get news feed for the dashboard.

    Returns recent activity (comments, status changes) for models the user has access to.
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
