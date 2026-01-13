"""Model tagging models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.model import Model


class TagCategory(Base):
    """Category for organizing tags (e.g., Regulatory, Project, Climate)."""
    __tablename__ = "tag_categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(
        String(7), nullable=False, default="#6B7280",
        comment="Hex color code (e.g., #DC2626)"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="System categories cannot be deleted"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    created_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    tags: Mapped[List["Tag"]] = relationship(
        "Tag", back_populates="category", cascade="all, delete-orphan",
        order_by="Tag.sort_order"
    )


class Tag(Base):
    """Tag for categorizing models."""
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("category_id", "name", name="uq_tag_category_name"),
    )

    tag_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tag_categories.category_id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(
        String(7), nullable=True,
        comment="Optional override color (hex code)"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    created_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    category: Mapped["TagCategory"] = relationship("TagCategory", back_populates="tags")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    model_tags: Mapped[List["ModelTag"]] = relationship(
        "ModelTag", back_populates="tag", cascade="all, delete-orphan"
    )

    @property
    def effective_color(self) -> str:
        """Return the tag's color, falling back to category color if not set."""
        return self.color if self.color else self.category.color

    @property
    def category_name(self) -> str:
        """Return the category name for serialization."""
        return self.category.name if self.category else ""

    @property
    def category_color(self) -> str:
        """Return the category color for serialization."""
        return self.category.color if self.category else "#6B7280"


class ModelTag(Base):
    """Association between models and tags (current state - hard delete)."""
    __tablename__ = "model_tags"

    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.tag_id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    added_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    model: Mapped["Model"] = relationship("Model", back_populates="model_tags")
    tag: Mapped["Tag"] = relationship("Tag", back_populates="model_tags")
    added_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[added_by_id])


class ModelTagHistory(Base):
    """Audit history for model tag changes."""
    __tablename__ = "model_tag_history"

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.tag_id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="Action type: 'ADDED' or 'REMOVED'"
    )
    performed_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    performed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    model: Mapped["Model"] = relationship("Model")
    tag: Mapped["Tag"] = relationship("Tag")
    performed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[performed_by_id])
