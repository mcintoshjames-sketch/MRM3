"""User lookup endpoints (non-admin)."""
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.user_lookup import ModelAssigneeResponse

router = APIRouter(prefix="/users")


@router.get("/search", response_model=List[ModelAssigneeResponse])
def search_users(
    email: str = Query(..., min_length=1, description="Email prefix or exact match"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search users by email (available to all authenticated users)."""
    query = email.strip()
    if not query:
        return []
    users = db.query(User).filter(
        User.email.ilike(f"{query}%")
    ).order_by(User.email.asc()).limit(20).all()
    return users
