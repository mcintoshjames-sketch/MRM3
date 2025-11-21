"""Dashboard routes."""
from typing import List, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.model import Model
from app.models.model_submission_comment import ModelSubmissionComment
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

    return feed
