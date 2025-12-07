"""Methodology library - categorized collection of modeling methodologies."""
from typing import Optional, List
from sqlalchemy import String, Integer, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class MethodologyCategory(Base):
    """Category for grouping related methodologies (e.g., Credit Risk, Market Risk)."""
    __tablename__ = "methodology_categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_aiml: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    methodologies: Mapped[List["Methodology"]] = relationship(
        "Methodology", back_populates="category", cascade="all, delete-orphan",
        order_by="Methodology.sort_order"
    )


class Methodology(Base):
    """Individual methodology entry within a category."""
    __tablename__ = "methodologies"

    methodology_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("methodology_categories.category_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    variants: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    category: Mapped["MethodologyCategory"] = relationship(
        "MethodologyCategory", back_populates="methodologies"
    )
