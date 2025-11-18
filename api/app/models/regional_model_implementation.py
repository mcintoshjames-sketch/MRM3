"""Regional Model Implementation model."""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class RegionalModelImplementation(Base):
    """Regional implementation of a global or regionally-owned model."""
    __tablename__ = "regional_model_implementations"

    regional_model_impl_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), nullable=False, index=True)
    region_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("regions.region_id", ondelete="RESTRICT"), nullable=False, index=True)
    shared_model_owner_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    local_identifier: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    decommission_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    model: Mapped["Model"] = relationship("Model", back_populates="regional_implementations")
    region: Mapped["Region"] = relationship("Region")
    shared_model_owner: Mapped[Optional["User"]] = relationship("User")
