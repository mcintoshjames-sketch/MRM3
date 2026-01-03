"""Model Exceptions tracking for compliance and risk management."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    String, Integer, Text, DateTime, Boolean, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now

if TYPE_CHECKING:
    from app.models.attestation import AttestationResponse
    from app.models.model import Model
    from app.models.monitoring import MonitoringResult
    from app.models.taxonomy import TaxonomyValue
    from app.models.user import User
    from app.models.version_deployment_task import VersionDeploymentTask


class ModelException(Base):
    """
    Tracks model exceptions that require acknowledgment and resolution.

    Exception Types:
    - UNMITIGATED_PERFORMANCE: RED monitoring result persisting or without linked recommendation
    - OUTSIDE_INTENDED_PURPOSE: ATT_Q10_USE_RESTRICTIONS attestation answered "No"
    - USE_PRIOR_TO_VALIDATION: Model version deployed before validation approval

    Lifecycle: OPEN -> ACKNOWLEDGED -> CLOSED
    """
    __tablename__ = "model_exceptions"

    exception_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Unique exception code: EXC-YYYY-NNNNN
    exception_code: Mapped[str] = mapped_column(
        String(16), unique=True, nullable=False, index=True
    )

    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Exception type enumeration stored as string
    exception_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="UNMITIGATED_PERFORMANCE | OUTSIDE_INTENDED_PURPOSE | USE_PRIOR_TO_VALIDATION"
    )

    # Source entity tracking - exactly ONE should be non-null per exception type
    # Type 1: Unmitigated Performance
    monitoring_result_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("monitoring_results.result_id", ondelete="SET NULL"),
        nullable=True
    )
    # Type 2: Outside Intended Purpose
    attestation_response_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("attestation_responses.response_id", ondelete="SET NULL"),
        nullable=True
    )
    # Type 3: Use Prior to Validation
    deployment_task_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("version_deployment_tasks.task_id", ondelete="SET NULL"),
        nullable=True
    )

    # Status: OPEN | ACKNOWLEDGED | CLOSED
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="OPEN", index=True
    )

    # Auto-generated description based on exception type
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Detection timestamp
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )

    # Whether closed by system (auto-close) vs admin (manual)
    auto_closed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True if closed automatically by system, False if closed manually by Admin"
    )

    # Acknowledgment fields
    acknowledged_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    acknowledgment_notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )

    # Closure fields
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    closed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL for auto-closed exceptions"
    )
    closure_narrative: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Required when closing (min 10 chars)"
    )
    closure_reason_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id", ondelete="RESTRICT"),
        nullable=True,
        comment="FK to Exception Closure Reason taxonomy, required when closing"
    )

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    model: Mapped["Model"] = relationship("Model", foreign_keys=[model_id])
    monitoring_result: Mapped[Optional["MonitoringResult"]] = relationship(
        "MonitoringResult", foreign_keys=[monitoring_result_id]
    )
    attestation_response: Mapped[Optional["AttestationResponse"]] = relationship(
        "AttestationResponse", foreign_keys=[attestation_response_id]
    )
    deployment_task: Mapped[Optional["VersionDeploymentTask"]] = relationship(
        "VersionDeploymentTask", foreign_keys=[deployment_task_id]
    )
    acknowledged_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[acknowledged_by_id]
    )
    closed_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[closed_by_id]
    )
    closure_reason: Mapped[Optional["TaxonomyValue"]] = relationship(
        "TaxonomyValue", foreign_keys=[closure_reason_id]
    )

    # Status history relationship
    status_history: Mapped[list["ModelExceptionStatusHistory"]] = relationship(
        "ModelExceptionStatusHistory",
        back_populates="exception",
        cascade="all, delete-orphan",
        order_by="ModelExceptionStatusHistory.changed_at.desc()"
    )

    __table_args__ = (
        # Ensure exactly one source FK is set (partial unique constraint per source type)
        # These ensure no duplicate exceptions for the same source entity
        Index(
            "ix_model_exceptions_monitoring_result_unique",
            "monitoring_result_id",
            unique=True,
            postgresql_where=(monitoring_result_id.isnot(None))
        ),
        Index(
            "ix_model_exceptions_attestation_response_unique",
            "attestation_response_id",
            unique=True,
            postgresql_where=(attestation_response_id.isnot(None))
        ),
        Index(
            "ix_model_exceptions_deployment_task_unique",
            "deployment_task_id",
            unique=True,
            postgresql_where=(deployment_task_id.isnot(None))
        ),
        # Check constraint for valid exception types
        CheckConstraint(
            "exception_type IN ('UNMITIGATED_PERFORMANCE', 'OUTSIDE_INTENDED_PURPOSE', 'USE_PRIOR_TO_VALIDATION')",
            name="ck_model_exceptions_type"
        ),
        # Check constraint for valid status values
        CheckConstraint(
            "status IN ('OPEN', 'ACKNOWLEDGED', 'CLOSED')",
            name="ck_model_exceptions_status"
        ),
        # Check constraint for closure requirements: when CLOSED, must have reason and narrative
        CheckConstraint(
            "status != 'CLOSED' OR (closure_reason_id IS NOT NULL AND closure_narrative IS NOT NULL)",
            name="ck_model_exceptions_closure_requirements"
        ),
    )


class ModelExceptionStatusHistory(Base):
    """Audit trail of exception status changes."""
    __tablename__ = "model_exception_status_history"

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    exception_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_exceptions.exception_id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    old_status: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        comment="NULL for initial creation"
    )
    new_status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    changed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL for system-initiated changes"
    )

    changed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )

    # Relationships
    exception: Mapped["ModelException"] = relationship(
        "ModelException", back_populates="status_history"
    )
    changed_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[changed_by_id]
    )
