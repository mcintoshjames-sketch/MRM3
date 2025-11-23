"""Model dependency metadata - extended metadata for feed dependencies (not exposed in UI yet)."""
from typing import Optional
from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ModelDependencyMetadata(Base):
    """Extended metadata for model feed dependencies - used for detailed governance tracking."""
    __tablename__ = "model_dependency_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dependency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_feed_dependencies.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )

    # Taxonomy-based metadata fields (for future use)
    feed_frequency_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=True
    )
    interface_type_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=True
    )
    criticality_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=True
    )

    # Free-text fields
    data_fields_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Placeholder for future data contract integration
    data_contract_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    dependency = relationship("ModelFeedDependency", back_populates="dependency_metadata")
    feed_frequency = relationship("TaxonomyValue", foreign_keys=[feed_frequency_id])
    interface_type = relationship("TaxonomyValue", foreign_keys=[interface_type_id])
    criticality = relationship("TaxonomyValue", foreign_keys=[criticality_id])
