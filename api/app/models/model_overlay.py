"""Model Overlays - tracking underperformance overlays and management judgements."""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    String, Integer, Text, Boolean, ForeignKey, DateTime, Date,
    CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now


class ModelOverlay(Base):
    """Tracks model overlays and significant management judgements."""
    __tablename__ = "model_overlays"

    overlay_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="The model this overlay applies to"
    )

    overlay_kind: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="OVERLAY or MANAGEMENT_JUDGEMENT"
    )
    is_underperformance_related: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="Explicitly mark as underperformance-related for regulatory reporting"
    )

    description: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="What overlay or judgement is applied"
    )
    rationale: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Why this overlay/judgement is applied"
    )

    effective_from: Mapped[date] = mapped_column(
        Date, nullable=False,
        comment="Start date for the overlay effectiveness window"
    )
    effective_to: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True,
        comment="Optional end date for the overlay effectiveness window"
    )

    region_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("regions.region_id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Optional region scope (NULL = global)"
    )

    trigger_monitoring_result_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("monitoring_results.result_id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Monitoring result that triggered the overlay (optional)"
    )
    trigger_monitoring_cycle_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("monitoring_cycles.cycle_id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Monitoring cycle that triggered the overlay (optional)"
    )

    related_recommendation_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("recommendations.recommendation_id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Related recommendation (optional)"
    )
    related_limitation_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("model_limitations.limitation_id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Related limitation (optional)"
    )

    evidence_description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Evidence description supporting the overlay (optional)"
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
    model = relationship("Model", back_populates="overlays")
    region = relationship("Region")
    trigger_monitoring_result = relationship(
        "MonitoringResult", foreign_keys=[trigger_monitoring_result_id]
    )
    trigger_monitoring_cycle = relationship(
        "MonitoringCycle", foreign_keys=[trigger_monitoring_cycle_id]
    )
    related_recommendation = relationship(
        "Recommendation", foreign_keys=[related_recommendation_id]
    )
    related_limitation = relationship(
        "ModelLimitation",
        foreign_keys=[related_limitation_id],
        back_populates="related_overlays"
    )
    created_by = relationship("User", foreign_keys=[created_by_id])
    retired_by = relationship("User", foreign_keys=[retired_by_id])

    __table_args__ = (
        CheckConstraint(
            "overlay_kind IN ('OVERLAY', 'MANAGEMENT_JUDGEMENT')",
            name="chk_overlay_kind"
        ),
        CheckConstraint(
            "(effective_to IS NULL OR effective_to >= effective_from)",
            name="chk_overlay_effective_window"
        ),
        CheckConstraint(
            "(is_retired = FALSE AND retirement_date IS NULL AND retirement_reason IS NULL AND retired_by_id IS NULL) OR "
            "(is_retired = TRUE AND retirement_date IS NOT NULL AND retirement_reason IS NOT NULL AND retired_by_id IS NOT NULL)",
            name="chk_overlay_retirement_fields_consistency"
        ),
    )
