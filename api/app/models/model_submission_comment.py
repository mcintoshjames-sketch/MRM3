"""Model Submission Comment model - for iterative review conversation."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now

if TYPE_CHECKING:
    from app.models.model import Model
    from app.models.user import User


class ModelSubmissionComment(Base):
    """Model submission comment table - tracks conversation between submitter and admin."""
    __tablename__ = "model_submission_comments"

    comment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    action_taken: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="Action: submitted, sent_back, resubmitted, approved, rejected")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False)

    # Relationships
    model: Mapped["Model"] = relationship("Model", back_populates="submission_comments")
    user: Mapped["User"] = relationship("User")
