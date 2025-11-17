"""Validation and ValidationPolicy models."""
from datetime import datetime
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ValidationPolicy(Base):
    """Validation policy configuration by risk tier."""
    __tablename__ = "validation_policies"

    policy_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    risk_tier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False, unique=True
    )
    frequency_months: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    risk_tier = relationship("TaxonomyValue", foreign_keys=[risk_tier_id])


class Validation(Base):
    """Model validation record."""
    __tablename__ = "validations"

    validation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), nullable=False
    )
    validation_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    validator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    validation_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    outcome_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    scope_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    findings_summary: Mapped[str] = mapped_column(Text, nullable=True)
    report_reference: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    model = relationship("Model", back_populates="validations")
    validator = relationship("User", foreign_keys=[validator_id])
    validation_type = relationship("TaxonomyValue", foreign_keys=[validation_type_id])
    outcome = relationship("TaxonomyValue", foreign_keys=[outcome_id])
    scope = relationship("TaxonomyValue", foreign_keys=[scope_id])
