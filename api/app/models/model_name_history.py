"""Model Name History - tracks changes to model names over time."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now

if TYPE_CHECKING:
    from app.models.model import Model
    from app.models.user import User


class ModelNameHistory(Base):
    """Tracks historical changes to model names for audit and reporting."""
    __tablename__ = "model_name_history"

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), nullable=False, index=True
    )
    old_name: Mapped[str] = mapped_column(String(255), nullable=False)
    new_name: Mapped[str] = mapped_column(String(255), nullable=False)
    changed_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False, index=True
    )
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    model: Mapped["Model"] = relationship("Model", back_populates="name_history")
    changed_by: Mapped["User"] = relationship("User")
