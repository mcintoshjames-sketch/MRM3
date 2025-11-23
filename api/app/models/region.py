"""Region model for geographic organization."""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, TYPE_CHECKING
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Region(Base):
    """Geographic region for model governance and validation context."""
    __tablename__ = "regions"

    region_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    requires_regional_approval: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    enforce_validation_plan: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
        comment="When true, validation plans are required for requests scoped to this region"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Users who can approve validations in this region
    approvers: Mapped[List["User"]] = relationship(
        "User", secondary="user_regions", back_populates="regions"
    )
