"""Model Limitations - tracking inherent constraints and weaknesses of models.

Limitations are discovered during validation and persist at the model level.
They capture classification, impact assessment, and conclusions about mitigation.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Text, Boolean, ForeignKey, DateTime,
    CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now


class ModelLimitation(Base):
    """
    Tracks model limitations - inherent constraints, weaknesses, or boundaries
    that users and stakeholders need to be aware of.

    Limitations are discovered during validation but persist at the model level.
    Critical limitations require documentation of how users are made aware.
    """
    __tablename__ = "model_limitations"

    limitation_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Core relationships
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="The model this limitation applies to"
    )

    # Traceability - optional links to originating validation and version
    validation_request_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("validation_requests.request_id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Validation request that originally identified this limitation"
    )
    model_version_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("model_versions.version_id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Model version under review when limitation was discovered"
    )

    # Optional link to recommendation for mitigation
    recommendation_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("recommendations.recommendation_id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Linked recommendation for mitigation (optional)"
    )

    # Classification
    significance: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="Critical or Non-Critical"
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"),
        nullable=False, index=True,
        comment="Limitation category from taxonomy (Data, Implementation, Methodology, etc.)"
    )

    # Narrative content
    description: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Narrative description of the nature of the limitation"
    )
    impact_assessment: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Narrative assessment of the limitation's impact"
    )

    # Conclusion
    conclusion: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="Mitigate or Accept"
    )
    conclusion_rationale: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Explanation for the mitigate/accept decision"
    )

    # User awareness (required for Critical limitations)
    user_awareness_description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="How users are made aware of this limitation (required if Critical)"
    )

    # Retirement
    is_retired: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    retirement_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    retirement_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    retired_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True
    )

    # Audit fields
    created_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    model = relationship("Model", back_populates="limitations")
    validation_request = relationship("ValidationRequest")
    model_version = relationship("ModelVersion")
    recommendation = relationship("Recommendation")
    category = relationship("TaxonomyValue", foreign_keys=[category_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    retired_by = relationship("User", foreign_keys=[retired_by_id])
    related_overlays: Mapped[List["ModelOverlay"]] = relationship(
        "ModelOverlay", back_populates="related_limitation"
    )

    __table_args__ = (
        CheckConstraint(
            "significance IN ('Critical', 'Non-Critical')",
            name='chk_limitation_significance'
        ),
        CheckConstraint(
            "conclusion IN ('Mitigate', 'Accept')",
            name='chk_limitation_conclusion'
        ),
        CheckConstraint(
            "significance != 'Critical' OR user_awareness_description IS NOT NULL",
            name='chk_critical_requires_awareness'
        ),
        CheckConstraint(
            "(is_retired = FALSE AND retirement_date IS NULL AND retirement_reason IS NULL AND retired_by_id IS NULL) OR "
            "(is_retired = TRUE AND retirement_date IS NOT NULL AND retirement_reason IS NOT NULL AND retired_by_id IS NOT NULL)",
            name='chk_retirement_fields_consistency'
        ),
    )
