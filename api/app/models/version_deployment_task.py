"""Version Deployment Task model for tracking deployment confirmations."""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, Date, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now


class VersionDeploymentTask(Base):
    """Tracks Model Owner confirmation of version deployments."""
    __tablename__ = "version_deployment_tasks"

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("model_versions.version_id", ondelete="CASCADE"),
        nullable=False
    )
    model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("models.model_id", ondelete="CASCADE"),
        nullable=False
    )
    region_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("regions.region_id", ondelete="CASCADE"),
        nullable=True,
        comment="NULL for global deployment"
    )

    # Task details
    planned_production_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_production_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Assignment
    assigned_to_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False,
        comment="Model Owner or delegate"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING"
    )  # PENDING | CONFIRMED | ADJUSTED | CANCELLED
    confirmation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    confirmed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=True
    )

    # Validation override tracking
    deployed_before_validation_approved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if deployed before validation was approved"
    )
    validation_override_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Justification for deploying before validation approval"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now
    )

    # Relationships
    version: Mapped["ModelVersion"] = relationship("ModelVersion", foreign_keys=[version_id])
    model: Mapped["Model"] = relationship("Model", foreign_keys=[model_id])
    region: Mapped[Optional["Region"]] = relationship("Region", foreign_keys=[region_id])
    assigned_to: Mapped["User"] = relationship("User", foreign_keys=[assigned_to_id])
    confirmed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[confirmed_by_id])
