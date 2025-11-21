"""Export View models for saved CSV export configurations."""
from datetime import datetime
from typing import List
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ExportView(Base):
    """User-defined export view configurations."""
    __tablename__ = "export_views"

    view_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Entity type (e.g., 'models', 'validations')"
    )
    view_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_public: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="If true, all users can see this view"
    )
    columns: Mapped[List[str]] = mapped_column(
        JSON, nullable=False,
        comment="Array of column keys to include in export"
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=True,
        comment="Optional description of what this view is for"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<ExportView(id={self.view_id}, name='{self.view_name}', entity='{self.entity_type}', public={self.is_public})>"
