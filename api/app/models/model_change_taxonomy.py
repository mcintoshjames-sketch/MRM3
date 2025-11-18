"""Model change taxonomy - hierarchical change classification system."""
from typing import Optional, List
from sqlalchemy import String, Integer, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ModelChangeCategory(Base):
    """L1 - Model change category (e.g., New Model, Change to Model)."""
    __tablename__ = "model_change_categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    change_types: Mapped[List["ModelChangeType"]] = relationship(
        "ModelChangeType", back_populates="category", cascade="all, delete-orphan", order_by="ModelChangeType.sort_order"
    )


class ModelChangeType(Base):
    """L2 - Specific model change type within a category."""
    __tablename__ = "model_change_types"

    change_type_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_change_categories.category_id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mv_activity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    requires_mv_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    category: Mapped["ModelChangeCategory"] = relationship("ModelChangeCategory", back_populates="change_types")
