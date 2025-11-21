"""Model Version model for tracking model changes and versioning."""
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import String, Integer, Text, DateTime, Date, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ModelVersion(Base):
    """Track model versions and changes over time."""
    __tablename__ = "model_versions"

    version_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[str] = mapped_column(String(50), nullable=False)
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)  # MINOR | MAJOR (legacy, kept for backward compat)
    change_type_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("model_change_types.change_type_id", ondelete="SET NULL"), nullable=True, index=True
    )
    change_description: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Regional scope tracking
    scope: Mapped[str] = mapped_column(
        String(20), nullable=False, default="GLOBAL", index=True
    )  # GLOBAL | REGIONAL
    affected_region_ids: Mapped[Optional[List[int]]] = mapped_column(
        JSON, nullable=True, comment="List of region IDs affected by this change (for REGIONAL scope)"
    )

    # Production dates
    planned_production_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="Planned/target production date"
    )
    actual_production_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="Actual date when deployed to production"
    )
    production_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="Legacy field - maps to planned_production_date"
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="DRAFT", index=True
    )  # DRAFT | IN_VALIDATION | APPROVED | ACTIVE | SUPERSEDED
    validation_request_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("validation_requests.request_id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    model = relationship("Model", back_populates="versions")
    created_by = relationship("User", foreign_keys=[created_by_id])
    validation_request = relationship("ValidationRequest", foreign_keys=[validation_request_id])
    change_type_detail = relationship("ModelChangeType", foreign_keys=[change_type_id])
