"""Model hierarchy model - parent-child relationships between models."""
from datetime import date
from typing import Optional
from sqlalchemy import Integer, String, Date, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ModelHierarchy(Base):
    """Model hierarchy - represents parent-child relationships (e.g., sub-models)."""
    __tablename__ = "model_hierarchy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), nullable=False, index=True
    )
    child_model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Constraints
    __table_args__ = (
        # Prevent duplicate parent-child-type-date combinations
        UniqueConstraint(
            'parent_model_id', 'child_model_id', 'relation_type_id', 'effective_date',
            name='uq_model_hierarchy'
        ),
        # Prevent self-reference
        CheckConstraint('parent_model_id != child_model_id', name='ck_hierarchy_no_self_ref'),
        # Ensure end_date >= effective_date when both are set
        CheckConstraint('end_date IS NULL OR effective_date IS NULL OR end_date >= effective_date',
                       name='ck_hierarchy_date_range'),
    )

    # Relationships
    parent_model = relationship("Model", foreign_keys=[parent_model_id], back_populates="child_relationships")
    child_model = relationship("Model", foreign_keys=[child_model_id], back_populates="parent_relationships")
    relation_type = relationship("TaxonomyValue", foreign_keys=[relation_type_id])
