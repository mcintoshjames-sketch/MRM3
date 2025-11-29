"""Model Pending Edit - stores proposed changes to approved models awaiting admin approval."""
from datetime import datetime, UTC
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base


class ModelPendingEdit(Base):
    """
    Stores pending edits to approved models that require admin approval.

    When a non-admin user edits an approved model (row_approval_status=None),
    instead of applying the changes directly, they are stored here for admin review.
    """
    __tablename__ = "model_pending_edits"

    pending_edit_id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("models.model_id", ondelete="CASCADE"), nullable=False)
    requested_by_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    requested_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    proposed_changes = Column(JSON, nullable=False)  # Dict of field_name -> new_value
    original_values = Column(JSON, nullable=False)  # Dict of field_name -> old_value (for comparison)
    status = Column(String(20), default="pending", nullable=False)  # pending, approved, rejected
    reviewed_by_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_comment = Column(Text, nullable=True)

    # Relationships
    model = relationship("Model", back_populates="pending_edits")
    requested_by = relationship("User", foreign_keys=[requested_by_id], backref="requested_model_edits")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id], backref="reviewed_model_edits")

    def __repr__(self):
        return f"<ModelPendingEdit(id={self.pending_edit_id}, model_id={self.model_id}, status={self.status})>"
