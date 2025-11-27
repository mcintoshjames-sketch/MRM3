"""KPM (Key Performance Metrics) taxonomy - ongoing monitoring metrics library."""
import enum
from typing import Optional, List
from sqlalchemy import String, Integer, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class KpmEvaluationType(str, enum.Enum):
    """KPM evaluation type determining how the metric is assessed."""
    QUANTITATIVE = "Quantitative"      # Numerical results with thresholds
    QUALITATIVE = "Qualitative"        # Judgment/rules-based, outcome selected from taxonomy
    OUTCOME_ONLY = "Outcome Only"      # Direct R/Y/G selection with notes only


class KpmCategoryType(str, enum.Enum):
    """KPM category type - determines the section where the category appears."""
    QUANTITATIVE = "Quantitative"
    QUALITATIVE = "Qualitative"


class KpmCategory(Base):
    """KPM category (e.g., Model Calibration, Model Performance)."""
    __tablename__ = "kpm_categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    category_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default=KpmCategoryType.QUANTITATIVE.value,
        comment="Category type: Quantitative or Qualitative"
    )

    # Relationships
    kpms: Mapped[List["Kpm"]] = relationship(
        "Kpm", back_populates="category", cascade="all, delete-orphan", order_by="Kpm.sort_order"
    )


class Kpm(Base):
    """Individual KPM (Key Performance Metric) within a category."""
    __tablename__ = "kpms"

    kpm_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("kpm_categories.category_id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    calculation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    interpretation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Evaluation type determines how this KPM is assessed
    evaluation_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default=KpmEvaluationType.QUANTITATIVE.value,
        comment="How this KPM is evaluated: Quantitative (thresholds), Qualitative (rules/judgment), Outcome Only (direct R/Y/G)"
    )

    # Relationships
    category: Mapped["KpmCategory"] = relationship(
        "KpmCategory", back_populates="kpms")
