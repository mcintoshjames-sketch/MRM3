"""Model Due Date Override for admin schedule adjustments."""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Date, Boolean, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now


class ModelDueDateOverride(Base):
    """
    Admin-managed override for model validation due dates.

    Following the OverdueRevalidationComment pattern for history tracking:
    - Each update creates a new record with is_active=True
    - Previous active record is marked is_active=False with cleared_at timestamp
    - Full audit trail preserved

    Override Types:
    - ONE_TIME: Auto-clears when the targeted validation is approved
    - PERMANENT: Persists and auto-rolls forward when validation completes

    Target Scope:
    - CURRENT_REQUEST: Affects the active/open validation request
    - NEXT_CYCLE: Affects the next scheduled validation cycle

    Cleared Types:
    - MANUAL: Admin explicitly cleared the override
    - AUTO_VALIDATION_COMPLETE: ONE_TIME override auto-cleared on approval
    - AUTO_ROLL_FORWARD: PERMANENT override rolled forward to next cycle
    - AUTO_REQUEST_CANCELLED: Linked validation request was cancelled
    - SUPERSEDED: Replaced by a new override
    """
    __tablename__ = "model_due_date_overrides"

    override_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Required: Model this override applies to
    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("models.model_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Optional: Specific validation request (only for CURRENT_REQUEST scope)
    validation_request_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("validation_requests.request_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Linked validation request (only for CURRENT_REQUEST scope)"
    )

    # Override configuration
    override_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="ONE_TIME or PERMANENT"
    )
    target_scope: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="CURRENT_REQUEST or NEXT_CYCLE"
    )

    # The override date (must be earlier than policy-calculated date at creation)
    override_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="New due date - must be earlier than calculated date"
    )

    # Original calculated date (captured at creation for reference)
    original_calculated_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Policy-calculated date at time of override creation"
    )

    # Required justification (minimum 10 characters enforced at API level)
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Admin justification for override (min 10 chars)"
    )

    # Creation tracking
    created_by_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )

    # Active/history tracking
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True
    )

    # Clearing/superseding tracking
    cleared_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this override was cleared/superseded"
    )
    cleared_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=True
    )
    cleared_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for clearing (manual or auto-cleared)"
    )
    cleared_type: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="MANUAL, AUTO_VALIDATION_COMPLETE, AUTO_ROLL_FORWARD, AUTO_REQUEST_CANCELLED, or SUPERSEDED"
    )

    # Link to superseding override (if replaced by new override)
    superseded_by_override_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("model_due_date_overrides.override_id"),
        nullable=True
    )

    # Link to previous override (for roll-forward chain)
    rolled_from_override_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("model_due_date_overrides.override_id"),
        nullable=True,
        comment="For auto-rolled overrides: points to the previous cycle's override"
    )

    # Relationships
    model = relationship("Model", back_populates="due_date_overrides")
    validation_request = relationship("ValidationRequest", foreign_keys=[validation_request_id])
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    cleared_by_user = relationship("User", foreign_keys=[cleared_by_user_id])
    superseded_by = relationship(
        "ModelDueDateOverride",
        remote_side=[override_id],
        foreign_keys=[superseded_by_override_id],
        uselist=False
    )
    rolled_from = relationship(
        "ModelDueDateOverride",
        remote_side=[override_id],
        foreign_keys=[rolled_from_override_id],
        uselist=False
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "override_type IN ('ONE_TIME', 'PERMANENT')",
            name="check_override_type_valid"
        ),
        CheckConstraint(
            "target_scope IN ('CURRENT_REQUEST', 'NEXT_CYCLE')",
            name="check_target_scope_valid"
        ),
        CheckConstraint(
            "cleared_type IS NULL OR cleared_type IN ('MANUAL', 'AUTO_VALIDATION_COMPLETE', 'AUTO_ROLL_FORWARD', 'AUTO_REQUEST_CANCELLED', 'SUPERSEDED')",
            name="check_cleared_type_valid"
        ),
        CheckConstraint(
            "override_date < original_calculated_date",
            name="check_override_earlier_than_calculated"
        ),
    )

    def __repr__(self):
        return f"<ModelDueDateOverride(id={self.override_id}, model_id={self.model_id}, type={self.override_type}, scope={self.target_scope}, active={self.is_active})>"
