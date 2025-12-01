"""Validation Scorecard Models.

This module defines the database models for the validation scorecard system:
- ScorecardSection: User-configurable sections (loaded from SCORE_CRITERIA.json)
- ScorecardCriterion: User-configurable criteria within sections
- ValidationScorecardRating: Per-criterion ratings entered by validators
- ValidationScorecardResult: Computed scorecard results with configuration snapshot
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    Integer, String, Text, Boolean, Numeric, DateTime, ForeignKey, JSON,
    UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.core.time import utc_now

if TYPE_CHECKING:
    from app.models.validation import ValidationRequest


# Valid rating values for check constraint
VALID_RATINGS = ['Green', 'Green-', 'Yellow+', 'Yellow', 'Yellow-', 'Red', 'N/A']


class ScorecardSection(Base):
    """Scorecard sections - user configurable via taxonomy UI.

    Loaded initially from SCORE_CRITERIA.json sections array.
    Admins can add/modify sections through the taxonomy interface.
    """
    __tablename__ = "scorecard_sections"

    section_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        comment="Section code (e.g., '1', '2', '3')"
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display name (e.g., 'Evaluation of Conceptual Soundness')"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description of this section"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Display order in UI"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Inactive sections are hidden from new scorecards"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    criteria: Mapped[list["ScorecardCriterion"]] = relationship(
        "ScorecardCriterion",
        back_populates="section",
        order_by="ScorecardCriterion.sort_order"
    )


class ScorecardCriterion(Base):
    """Scorecard criteria - user configurable via taxonomy UI.

    Loaded initially from SCORE_CRITERIA.json criteria array.
    Each criterion belongs to a section and has prompts for validators.
    """
    __tablename__ = "scorecard_criteria"

    criterion_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        comment="Criterion code (e.g., '1.1', '2.3', '3.5')"
    )
    section_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("scorecard_sections.section_id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to parent section"
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display name (e.g., 'Model Development Documentation')"
    )
    description_prompt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Prompt guiding validator's description entry"
    )
    comments_prompt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Prompt guiding validator's comments entry"
    )
    include_in_summary: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether to include in section summary calculation"
    )
    allow_zero: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether N/A rating is allowed for this criterion"
    )
    weight: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=1.0,
        nullable=False,
        comment="Weight for weighted average calculation"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Display order within section"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Inactive criteria are hidden from new scorecards"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    section: Mapped["ScorecardSection"] = relationship(
        "ScorecardSection",
        back_populates="criteria"
    )

    __table_args__ = (
        # Index for efficient lookups by section
        # Note: sort_order handled by relationship ordering
    )


class ValidationScorecardRating(Base):
    """Per-criterion ratings entered by validators.

    Each rating is keyed by criterion_code (not criterion_id) for resilience
    to criteria additions/removals. Orphaned codes are preserved but
    excluded from new computations.

    Linked to ValidationRequest (not Outcome) so scorecard can be completed
    before the final outcome determination.
    """
    __tablename__ = "validation_scorecard_ratings"

    rating_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("validation_requests.request_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to validation request"
    )
    criterion_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Criterion code (e.g., '1.1') - keyed by code for resilience"
    )
    rating: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Rating: Green, Green-, Yellow+, Yellow, Yellow-, Red, N/A, or NULL"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Validator's description response"
    )
    comments: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Validator's comments"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    request: Mapped["ValidationRequest"] = relationship(
        "ValidationRequest",
        back_populates="scorecard_ratings"
    )

    __table_args__ = (
        UniqueConstraint('request_id', 'criterion_code', name='uq_request_criterion'),
        CheckConstraint(
            f"rating IS NULL OR rating IN ({', '.join(repr(r) for r in VALID_RATINGS)})",
            name='chk_valid_rating'
        ),
    )


class ValidationScorecardResult(Base):
    """Computed scorecard results with configuration snapshot.

    Stores the computed section summaries and overall assessment.
    The config_snapshot preserves the configuration state at computation time
    for historical accuracy even if criteria change later.

    Linked to ValidationRequest (not Outcome) so scorecard can be completed
    before the final outcome determination.
    """
    __tablename__ = "validation_scorecard_results"

    result_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("validation_requests.request_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="FK to validation request (ONE result per request)"
    )

    # Overall Assessment
    overall_numeric_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Overall numeric score (0-6)"
    )
    overall_rating: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Overall rating string (Green, Green-, etc.)"
    )

    # Section Summaries (JSON for flexibility)
    section_summaries: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON object with per-section summaries"
    )
    # Structure: {
    #   "1": {"section_name": "...", "numeric_score": 4, "rating": "Yellow+",
    #         "criteria_count": 5, "rated_count": 4, "unrated_count": 1},
    #   ...
    # }

    # Configuration snapshot for historical preservation
    config_snapshot: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Snapshot of scorecard configuration at computation time"
    )
    # Structure: {
    #   "sections": [...],
    #   "criteria": [...],
    #   "snapshot_timestamp": "2025-01-15T10:30:00"
    # }

    computed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
        comment="When the scorecard was computed"
    )

    # Relationships
    request: Mapped["ValidationRequest"] = relationship(
        "ValidationRequest",
        back_populates="scorecard_result"
    )
