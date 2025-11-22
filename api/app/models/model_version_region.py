"""Model Version Region association model."""
from datetime import datetime
from sqlalchemy import Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ModelVersionRegion(Base):
    """Association between model versions and regions they affect."""
    __tablename__ = "model_version_regions"
    __table_args__ = (
        UniqueConstraint('version_id', 'region_id', name='uq_version_region'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_versions.version_id", ondelete="CASCADE"), nullable=False, index=True
    )
    region_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("regions.region_id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    version = relationship("ModelVersion", back_populates="affected_regions_assoc")
    region = relationship("Region")
