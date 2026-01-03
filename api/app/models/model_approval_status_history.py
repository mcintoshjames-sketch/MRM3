"""Model Approval Status History - tracks changes to model approval status over time."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now

if TYPE_CHECKING:
    from app.models.model import Model


class ModelApprovalStatusHistory(Base):
    """Audit trail for model approval status changes.

    Tracks when a model's approval status changes (e.g., NEVER_VALIDATED -> APPROVED,
    APPROVED -> EXPIRED, etc.) for compliance and audit purposes.
    """
    __tablename__ = "model_approval_status_history"

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    old_status: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True,
        comment="Previous approval status (NULL for initial status)"
    )
    new_status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="New approval status"
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, index=True
    )
    trigger_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="What triggered this change: VALIDATION_APPROVED, VALIDATION_STATUS_CHANGE, APPROVAL_SUBMITTED, EXPIRATION_CHECK, BACKFILL, MANUAL"
    )
    trigger_entity_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="Entity type that triggered change: ValidationRequest, ValidationApproval, etc."
    )
    trigger_entity_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="ID of the entity that triggered the change"
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Additional context about the status change"
    )

    # Relationships
    model: Mapped["Model"] = relationship("Model", back_populates="approval_status_history")
