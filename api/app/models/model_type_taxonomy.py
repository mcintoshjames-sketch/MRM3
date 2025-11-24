"""Model type taxonomy - hierarchical model classification system."""
from typing import Optional, List
from sqlalchemy import String, Integer, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ModelTypeCategory(Base):
    """L1 - Model type category (e.g., Capital, Liquidity Risk)."""
    __tablename__ = "model_type_categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    model_types: Mapped[List["ModelType"]] = relationship(
        "ModelType", back_populates="category", cascade="all, delete-orphan", order_by="ModelType.sort_order"
    )


class ModelType(Base):
    """L2 - Specific model type within a category."""
    __tablename__ = "model_types"

    type_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_type_categories.category_id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)

    # Relationships
    category: Mapped["ModelTypeCategory"] = relationship(
        "ModelTypeCategory", back_populates="model_types")
