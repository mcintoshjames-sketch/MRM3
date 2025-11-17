"""Taxonomy models for configurable choices."""
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Taxonomy(Base):
    """A taxonomy represents a category of configurable choices."""
    __tablename__ = "taxonomies"

    taxonomy_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)  # System taxonomies can't be deleted
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship to values
    values: Mapped[list["TaxonomyValue"]] = relationship(
        "TaxonomyValue", back_populates="taxonomy", cascade="all, delete-orphan"
    )


class TaxonomyValue(Base):
    """A value within a taxonomy."""
    __tablename__ = "taxonomy_values"

    value_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    taxonomy_id: Mapped[int] = mapped_column(Integer, ForeignKey("taxonomies.taxonomy_id"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)  # Short code for the value
    label: Mapped[str] = mapped_column(String(255), nullable=False)  # Display label
    description: Mapped[str] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship back to taxonomy
    taxonomy: Mapped["Taxonomy"] = relationship("Taxonomy", back_populates="values")
