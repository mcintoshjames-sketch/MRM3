"""Overdue Revalidation Comment model for tracking delay explanations."""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Date, Boolean, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class OverdueRevalidationComment(Base):
    """
    Tracks overdue revalidation comments/explanations.

    Commentary is always attached to a ValidationRequest (required).
    Each update creates a new record; previous records are marked is_current=FALSE.

    Two overdue types:
    - PRE_SUBMISSION: Model owner/developer explains submission delay
    - VALIDATION_IN_PROGRESS: Validator explains validation completion delay
    """
    __tablename__ = "overdue_revalidation_comments"

    comment_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Context: ValidationRequest is REQUIRED
    validation_request_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("validation_requests.request_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Type: determines who is responsible
    overdue_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="PRE_SUBMISSION or VALIDATION_IN_PROGRESS"
    )

    # Content
    reason_comment: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Explanation for the overdue status"
    )
    target_date: Mapped[datetime] = mapped_column(
        Date,
        nullable=False,
        comment="Target Submission Date (PRE_SUBMISSION) or Target Completion Date (VALIDATION_IN_PROGRESS)"
    )

    # Tracking
    created_by_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    # For history: when a new comment supersedes this one
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True
    )
    superseded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    superseded_by_comment_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("overdue_revalidation_comments.comment_id"),
        nullable=True
    )

    # Relationships
    validation_request = relationship("ValidationRequest", back_populates="overdue_comments")
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    superseded_by = relationship(
        "OverdueRevalidationComment",
        remote_side=[comment_id],
        foreign_keys=[superseded_by_comment_id]
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "overdue_type IN ('PRE_SUBMISSION', 'VALIDATION_IN_PROGRESS')",
            name="check_overdue_type_valid"
        ),
    )

    def __repr__(self):
        return f"<OverdueRevalidationComment(id={self.comment_id}, request_id={self.validation_request_id}, type={self.overdue_type}, current={self.is_current})>"
