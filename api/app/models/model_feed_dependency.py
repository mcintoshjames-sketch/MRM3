"""Model feed dependency model - feeder-consumer relationships between models."""
from datetime import date
from typing import Optional
from sqlalchemy import Integer, String, Boolean, Date, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ModelFeedDependency(Base):
    """Model feed dependency - represents feeder-consumer data flow relationships."""
    __tablename__ = "model_feed_dependencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feeder_model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), nullable=False, index=True
    )
    consumer_model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), nullable=False, index=True
    )
    dependency_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Constraints
    __table_args__ = (
        # Prevent duplicate feeder-consumer-type combinations (multiple types per pair allowed)
        UniqueConstraint(
            'feeder_model_id', 'consumer_model_id', 'dependency_type_id',
            name='uq_model_dependency'
        ),
        # Prevent self-reference
        CheckConstraint('feeder_model_id != consumer_model_id', name='ck_dependency_no_self_ref'),
        # Ensure end_date >= effective_date when both are set
        CheckConstraint('end_date IS NULL OR effective_date IS NULL OR end_date >= effective_date',
                       name='ck_dependency_date_range'),
    )

    # Relationships
    feeder_model = relationship("Model", foreign_keys=[feeder_model_id], back_populates="outbound_dependencies")
    consumer_model = relationship("Model", foreign_keys=[consumer_model_id], back_populates="inbound_dependencies")
    dependency_type = relationship("TaxonomyValue", foreign_keys=[dependency_type_id])

    # One-to-one relationship with metadata (renamed to avoid SQLAlchemy reserved word)
    dependency_metadata = relationship("ModelDependencyMetadata", back_populates="dependency", uselist=False, cascade="all, delete-orphan")
