"""Model Risk Assessment - Inherent risk rating derived from qualitative and quantitative factors.

Implements:
- Admin-customizable qualitative factors with guidance
- Per-model and per-region risk assessments
- Three override opportunities (quantitative, qualitative, final tier)
- Weight snapshots for historical accuracy
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Text, Boolean, ForeignKey, DateTime, Numeric,
    UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now


class QualitativeRiskFactor(Base):
    """
    Admin-customizable risk assessment factor.

    Examples: Reputation/Legal Risk, Complexity, Usage/Dependency, Stability

    Factors can be added/modified by admins. Soft-delete (is_active=False)
    is used when a factor is referenced by existing assessments.
    """
    __tablename__ = "qualitative_risk_factors"

    factor_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True,
        comment="Unique code identifier (e.g., REPUTATION_LEGAL)"
    )
    name: Mapped[str] = mapped_column(
        String(200), nullable=False,
        comment="Display name for the factor"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Full description of what this factor measures"
    )
    weight: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False,
        comment="Weight for weighted average calculation (e.g., 0.3000 for 30%)"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Display order in the assessment form"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="Active factors appear in new assessments"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    guidance: Mapped[List["QualitativeFactorGuidance"]] = relationship(
        back_populates="factor", cascade="all, delete-orphan",
        order_by="QualitativeFactorGuidance.sort_order"
    )
    factor_assessments: Mapped[List["QualitativeFactorAssessment"]] = relationship(
        back_populates="factor"
    )


class QualitativeFactorGuidance(Base):
    """
    Rating guidance for a qualitative factor.

    Provides HIGH/MEDIUM/LOW rating descriptions to help assessors
    make consistent ratings.
    """
    __tablename__ = "qualitative_factor_guidance"

    guidance_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    factor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("qualitative_risk_factors.factor_id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="FK to qualitative_risk_factors"
    )
    rating: Mapped[str] = mapped_column(
        String(10), nullable=False,
        comment="Rating level: HIGH, MEDIUM, or LOW"
    )
    points: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Points for this rating: 3 (HIGH), 2 (MEDIUM), 1 (LOW)"
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Guidance text explaining when this rating applies"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Display order within the factor"
    )

    # Relationships
    factor = relationship("QualitativeRiskFactor", back_populates="guidance")

    __table_args__ = (
        UniqueConstraint('factor_id', 'rating', name='uq_factor_rating'),
        CheckConstraint("rating IN ('HIGH', 'MEDIUM', 'LOW')", name='chk_guidance_rating'),
    )


class ModelRiskAssessment(Base):
    """
    Risk assessment for a model (global or regional).

    Contains:
    - Quantitative assessment (direct HIGH/MEDIUM/LOW rating)
    - Qualitative assessment (calculated from weighted factors)
    - Derived inherent risk tier (from matrix lookup)
    - Three override opportunities at each stage

    One assessment per model per region (region_id=NULL for global).
    """
    __tablename__ = "model_risk_assessments"

    assessment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="FK to models table"
    )
    region_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("regions.region_id", ondelete="CASCADE"),
        nullable=True, index=True,
        comment="FK to regions table. NULL = Global assessment"
    )

    # Quantitative Assessment (direct rating)
    quantitative_rating: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True,
        comment="Direct quantitative rating: HIGH, MEDIUM, LOW"
    )
    quantitative_comment: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Justification for quantitative rating"
    )
    quantitative_override: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True,
        comment="Override for quantitative: HIGH, MEDIUM, LOW"
    )
    quantitative_override_comment: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Justification for quantitative override"
    )

    # Qualitative Assessment (calculated from factors)
    qualitative_calculated_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True,
        comment="Weighted score from factor assessments (e.g., 2.30)"
    )
    qualitative_calculated_level: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True,
        comment="Level derived from score: HIGH (>=2.1), MEDIUM (>=1.6), LOW (<1.6)"
    )
    qualitative_override: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True,
        comment="Override for qualitative: HIGH, MEDIUM, LOW"
    )
    qualitative_override_comment: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Justification for qualitative override"
    )

    # Derived Inherent Risk (from matrix lookup)
    derived_risk_tier: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True,
        comment="Matrix lookup result: HIGH, MEDIUM, LOW, VERY_LOW"
    )
    derived_risk_tier_override: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True,
        comment="Override for final tier: HIGH, MEDIUM, LOW, VERY_LOW"
    )
    derived_risk_tier_override_comment: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Justification for final tier override"
    )

    # Final tier (mapped to taxonomy)
    final_tier_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"),
        nullable=True,
        comment="FK to taxonomy_values for Model Risk Tier (TIER_1, TIER_2, TIER_3, TIER_4)"
    )

    # Metadata
    assessed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id"),
        nullable=True,
        comment="FK to users who performed the assessment"
    )
    assessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True,
        comment="Timestamp when assessment was finalized"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    model = relationship("Model", back_populates="risk_assessments")
    region = relationship("Region")
    final_tier = relationship("TaxonomyValue", foreign_keys=[final_tier_id])
    assessed_by = relationship("User", foreign_keys=[assessed_by_id])

    factor_assessments: Mapped[List["QualitativeFactorAssessment"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan",
        order_by="QualitativeFactorAssessment.factor_assessment_id"
    )

    __table_args__ = (
        UniqueConstraint('model_id', 'region_id', name='uq_model_region_assessment'),
        CheckConstraint(
            "quantitative_rating IN ('HIGH', 'MEDIUM', 'LOW') OR quantitative_rating IS NULL",
            name='chk_quantitative_rating'
        ),
        CheckConstraint(
            "quantitative_override IN ('HIGH', 'MEDIUM', 'LOW') OR quantitative_override IS NULL",
            name='chk_quantitative_override'
        ),
        CheckConstraint(
            "qualitative_calculated_level IN ('HIGH', 'MEDIUM', 'LOW') OR qualitative_calculated_level IS NULL",
            name='chk_qualitative_level'
        ),
        CheckConstraint(
            "qualitative_override IN ('HIGH', 'MEDIUM', 'LOW') OR qualitative_override IS NULL",
            name='chk_qualitative_override'
        ),
        CheckConstraint(
            "derived_risk_tier IN ('HIGH', 'MEDIUM', 'LOW', 'VERY_LOW') OR derived_risk_tier IS NULL",
            name='chk_derived_tier'
        ),
        CheckConstraint(
            "derived_risk_tier_override IN ('HIGH', 'MEDIUM', 'LOW', 'VERY_LOW') OR derived_risk_tier_override IS NULL",
            name='chk_derived_tier_override'
        ),
    )


class QualitativeFactorAssessment(Base):
    """
    Individual factor rating within a risk assessment.

    Captures:
    - The rating (HIGH/MEDIUM/LOW) for this factor
    - Optional comment/justification
    - Weight snapshot at time of assessment (for historical accuracy)
    - Calculated score (weight * points)

    Rating is nullable to support partial saves.
    """
    __tablename__ = "qualitative_factor_assessments"

    factor_assessment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_risk_assessments.assessment_id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="FK to model_risk_assessments"
    )
    factor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("qualitative_risk_factors.factor_id"),
        nullable=False, index=True,
        comment="FK to qualitative_risk_factors"
    )
    rating: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True,
        comment="Rating for this factor: HIGH, MEDIUM, LOW (nullable for partial saves)"
    )
    comment: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Optional justification for this factor rating"
    )
    weight_at_assessment: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False,
        comment="Snapshot of factor weight at time of assessment"
    )
    score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True,
        comment="Calculated score: weight * points (e.g., 0.30 * 3 = 0.90)"
    )

    # Relationships
    assessment = relationship("ModelRiskAssessment", back_populates="factor_assessments")
    factor = relationship("QualitativeRiskFactor", back_populates="factor_assessments")

    __table_args__ = (
        UniqueConstraint('assessment_id', 'factor_id', name='uq_assessment_factor'),
        CheckConstraint(
            "rating IN ('HIGH', 'MEDIUM', 'LOW') OR rating IS NULL",
            name='chk_factor_rating'
        ),
    )
