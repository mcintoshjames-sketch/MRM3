"""Model delegate model - permissions for non-owner users to manage models."""
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now


class ModelDelegate(Base):
    """Model delegate - grants permissions to users for model management."""
    __tablename__ = "model_delegates"
    __allow_unmapped__ = True

    delegate_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    can_submit_changes: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    can_manage_regional: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    can_attest: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Can submit attestations on behalf of model owner"
    )
    delegated_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False
    )
    delegated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now)

    # Runtime-only attributes populated in API responses.
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    delegated_by_name: Optional[str] = None
    revoked_by_name: Optional[str] = None

    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)
    revoked_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )

    # Unique constraint: one delegation per model-user pair (active or revoked)
    __table_args__ = (
        UniqueConstraint('model_id', 'user_id', name='uq_model_delegate'),
    )

    # Relationships
    model = relationship("Model", back_populates="delegates")
    user = relationship("User", foreign_keys=[user_id])
    delegated_by = relationship("User", foreign_keys=[delegated_by_id])
    revoked_by = relationship("User", foreign_keys=[revoked_by_id])
