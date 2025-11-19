"""Validation grouping memory model."""
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ValidationGroupingMemory(Base):
    """Tracks the most recent multi-model validation for each model.

    Only updated for regular validations (Annual Review, Comprehensive, etc.),
    NOT for targeted validations (change-driven, targeted reviews).

    Used to suggest previously validated model groupings when creating new validations.
    """
    __tablename__ = "validation_grouping_memory"

    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("models.model_id", ondelete="CASCADE"),
        primary_key=True
    )
    last_validation_request_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("validation_requests.request_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    grouped_model_ids: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )  # JSON array: [2, 5, 8] - other models validated together
    is_regular_validation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )  # True for regular revalidations, False for targeted/change-driven
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    model = relationship("Model")
    last_validation = relationship("ValidationRequest")

    def __repr__(self):
        return f"<ValidationGroupingMemory(model_id={self.model_id}, last_validation_request_id={self.last_validation_request_id})>"
