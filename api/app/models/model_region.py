"""Model-Region link model for regional metadata."""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ModelRegion(Base):
    """Light metadata link between models and regions."""
    __tablename__ = "model_regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), nullable=False, index=True)
    region_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("regions.region_id", ondelete="CASCADE"), nullable=False, index=True)
    shared_model_owner_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    regional_risk_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Unique constraint: one model-region link per combination
    __table_args__ = (
        UniqueConstraint('model_id', 'region_id', name='uq_model_region'),
    )

    # Relationships
    model: Mapped["Model"] = relationship("Model", back_populates="model_regions")
    region: Mapped["Region"] = relationship("Region")
    shared_model_owner: Mapped[Optional["User"]] = relationship("User")
