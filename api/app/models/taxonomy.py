"""Taxonomy models for configurable choices."""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now


class Taxonomy(Base):
    """A taxonomy represents a category of configurable choices."""
    __tablename__ = "taxonomies"

    taxonomy_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False)  # System taxonomies can't be deleted
    # Taxonomy type: 'standard' (default) or 'bucket' (uses min_days/max_days ranges)
    taxonomy_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default='standard',
        comment="Type of taxonomy: 'standard' or 'bucket' (range-based)"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # Relationship to values (ordered by sort_order)
    values: Mapped[list["TaxonomyValue"]] = relationship(
        "TaxonomyValue", back_populates="taxonomy", cascade="all, delete-orphan",
        order_by="TaxonomyValue.sort_order"
    )


class TaxonomyValue(Base):
    """A value within a taxonomy."""
    __tablename__ = "taxonomy_values"

    value_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True)
    taxonomy_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomies.taxonomy_id"), nullable=False)
    code: Mapped[str] = mapped_column(
        String(50), nullable=False)  # Short code for the value
    label: Mapped[str] = mapped_column(
        String(255), nullable=False)  # Display label
    description: Mapped[str] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Range-based bucket fields (used when taxonomy.taxonomy_type = 'bucket')
    min_days: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="Minimum days (inclusive) for bucket. NULL means unbounded (negative infinity)."
    )
    max_days: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="Maximum days (inclusive) for bucket. NULL means unbounded (positive infinity)."
    )
    # Downgrade notches for Final Model Risk Ranking calculation
    # Used by bucket taxonomies (e.g., Past Due Level) to specify scorecard penalty
    downgrade_notches: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="Number of scorecard notches to downgrade for this past-due bucket (0-5)"
    )
    # MRSA Risk Level flag - indicates if IRP coverage is required for this risk level
    requires_irp: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True,
        comment="For MRSA Risk Level taxonomy: True if this risk level requires IRP coverage"
    )
    # System-protected flag - prevents deletion/deactivation of system-critical values
    is_system_protected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="If True, this value cannot be deleted or deactivated (used for exception detection questions)"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # Relationship back to taxonomy
    taxonomy: Mapped["Taxonomy"] = relationship(
        "Taxonomy", back_populates="values")
