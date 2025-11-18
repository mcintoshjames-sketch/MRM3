"""Region model for geographic organization."""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Region(Base):
    """Geographic region for model governance and validation context."""
    __tablename__ = "regions"

    region_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
