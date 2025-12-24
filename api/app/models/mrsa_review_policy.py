"""MRSA Review Policy models for periodic review scheduling and exception tracking."""
from datetime import datetime, date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Text, DateTime, Date, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.model import Model
    from app.models.taxonomy import TaxonomyValue


class MRSAReviewPolicy(Base):
    """Periodic review scheduling policy per MRSA risk level.

    Defines review frequencies and alerting thresholds for MRSAs based on
    their risk classification (High-Risk vs Low-Risk).
    """
    __tablename__ = "mrsa_review_policies"

    policy_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mrsa_risk_level_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False, unique=True,
        comment="MRSA Risk Level taxonomy value (High-Risk or Low-Risk)"
    )
    frequency_months: Mapped[int] = mapped_column(
        Integer, nullable=False, default=24,
        comment="Review frequency in months (default: 24 months / 2 years)"
    )
    initial_review_months: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3,
        comment="Initial review due within N months of MRSA designation"
    )
    warning_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=90,
        comment="Number of days before due date to trigger warning alerts"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="Whether this policy is currently active"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    mrsa_risk_level: Mapped["TaxonomyValue"] = relationship(
        "TaxonomyValue", foreign_keys=[mrsa_risk_level_id]
    )


class MRSAReviewException(Base):
    """Exception/extension for MRSA review due dates.

    Allows administrators to grant extensions to review due dates with
    proper justification and approval tracking.
    """
    __tablename__ = "mrsa_review_exceptions"

    exception_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mrsa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), nullable=False, index=True,
        comment="MRSA model receiving the exception"
    )
    override_due_date: Mapped[date] = mapped_column(
        Date, nullable=False,
        comment="Extended review due date"
    )
    reason: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Justification for granting the exception"
    )
    approved_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False,
        comment="Administrator who approved the exception"
    )
    approved_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False,
        comment="Timestamp when exception was approved"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="Whether this exception is currently active"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    mrsa: Mapped["Model"] = relationship("Model", foreign_keys=[mrsa_id])
    approved_by: Mapped["User"] = relationship("User", foreign_keys=[approved_by_id])
