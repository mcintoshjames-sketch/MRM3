"""Model Risk Attestation entities."""
import enum
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Text, Boolean, ForeignKey, DateTime, Date,
    UniqueConstraint, Index, JSON, DECIMAL
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now


# ============================================================================
# Enums
# ============================================================================

class AttestationCycleStatus(str, enum.Enum):
    """Attestation cycle status workflow states."""
    PENDING = "PENDING"
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    CLOSED = "CLOSED"


class AttestationFrequency(str, enum.Enum):
    """Attestation frequency options."""
    ANNUAL = "ANNUAL"
    QUARTERLY = "QUARTERLY"


class AttestationDecision(str, enum.Enum):
    """Attestation decision types."""
    I_ATTEST = "I_ATTEST"
    I_ATTEST_WITH_UPDATES = "I_ATTEST_WITH_UPDATES"
    OTHER = "OTHER"


class AttestationRecordStatus(str, enum.Enum):
    """Attestation record status."""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    ADMIN_REVIEW = "ADMIN_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class AttestationSchedulingRuleType(str, enum.Enum):
    """Types of scheduling rules."""
    GLOBAL_DEFAULT = "GLOBAL_DEFAULT"
    OWNER_THRESHOLD = "OWNER_THRESHOLD"
    MODEL_OVERRIDE = "MODEL_OVERRIDE"
    REGIONAL_OVERRIDE = "REGIONAL_OVERRIDE"


class AttestationChangeType(str, enum.Enum):
    """Types of inventory changes linked to attestation."""
    MODEL_EDIT = "MODEL_EDIT"
    MODEL_VERSION = "MODEL_VERSION"  # New version of a model (via Submit Model Change)
    NEW_MODEL = "NEW_MODEL"
    DECOMMISSION = "DECOMMISSION"


class AttestationEvidenceType(str, enum.Enum):
    """Types of evidence URLs."""
    MONITORING_REPORT = "MONITORING_REPORT"
    VALIDATION_REPORT = "VALIDATION_REPORT"
    POLICY_DOC = "POLICY_DOC"
    EXCEPTION_DOC = "EXCEPTION_DOC"
    OTHER = "OTHER"


class AttestationQuestionFrequency(str, enum.Enum):
    """Frequency scope for attestation questions."""
    ANNUAL = "ANNUAL"
    QUARTERLY = "QUARTERLY"
    BOTH = "BOTH"


class AttestationBulkSubmissionStatus(str, enum.Enum):
    """Status of bulk attestation submission."""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"


# ============================================================================
# AttestationCycle - represents a scheduled attestation period
# ============================================================================

class AttestationCycle(Base):
    """
    Attestation cycle representing a scheduled attestation period.
    Follows MonitoringCycle pattern. Multiple cycles can be OPEN simultaneously.
    """
    __tablename__ = "attestation_cycles"

    cycle_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Period definition
    period_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    submission_due_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Workflow status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AttestationCycleStatus.PENDING.value
    )

    # Open tracking
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    opened_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )

    # Close tracking
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    opened_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[opened_by_user_id]
    )
    closed_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[closed_by_user_id]
    )
    records: Mapped[List["AttestationRecord"]] = relationship(
        "AttestationRecord", back_populates="cycle", cascade="all, delete-orphan"
    )
    bulk_submissions: Mapped[List["AttestationBulkSubmission"]] = relationship(
        "AttestationBulkSubmission", back_populates="cycle", cascade="all, delete-orphan"
    )


# ============================================================================
# AttestationRecord - one per model per cycle
# ============================================================================

class AttestationRecord(Base):
    """
    Attestation record for a single model within a cycle.
    One record per model per cycle.
    """
    __tablename__ = "attestation_records"

    attestation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("attestation_cycles.cycle_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    attesting_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False, index=True
    )

    # Due date (calculated when cycle opens based on scheduling rules)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Submission status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AttestationRecordStatus.PENDING.value
    )
    attested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Decision
    decision: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    decision_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Admin review
    reviewed_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Bulk attestation support
    bulk_submission_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("attestation_bulk_submissions.bulk_submission_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    is_excluded: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="True if model was excluded from bulk attestation"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    # Unique constraint: one attestation per model per cycle
    __table_args__ = (
        UniqueConstraint('cycle_id', 'model_id', name='uq_attestation_cycle_model'),
        Index('ix_attestation_records_status', 'status'),
        Index('ix_attestation_records_due_date', 'due_date'),
    )

    # Relationships
    cycle: Mapped["AttestationCycle"] = relationship(
        "AttestationCycle", back_populates="records"
    )
    model: Mapped["Model"] = relationship("Model")
    attesting_user: Mapped["User"] = relationship(
        "User", foreign_keys=[attesting_user_id]
    )
    reviewed_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[reviewed_by_user_id]
    )
    bulk_submission: Mapped[Optional["AttestationBulkSubmission"]] = relationship(
        "AttestationBulkSubmission", back_populates="attestation_records"
    )
    responses: Mapped[List["AttestationResponse"]] = relationship(
        "AttestationResponse", back_populates="attestation", cascade="all, delete-orphan"
    )
    evidence: Mapped[List["AttestationEvidence"]] = relationship(
        "AttestationEvidence", back_populates="attestation", cascade="all, delete-orphan"
    )
    change_links: Mapped[List["AttestationChangeLink"]] = relationship(
        "AttestationChangeLink", back_populates="attestation", cascade="all, delete-orphan"
    )


# ============================================================================
# AttestationResponse - answers to configurable questions
# ============================================================================

class AttestationResponse(Base):
    """
    Individual question response for an attestation.
    Links to TaxonomyValue for the question.
    """
    __tablename__ = "attestation_responses"

    response_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attestation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("attestation_records.attestation_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id", ondelete="RESTRICT"),
        nullable=False
    )

    # Answer (boolean: Yes/No)
    answer: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Comment (required if answer=false and question.requires_comment_if_no)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )

    # Unique constraint: one response per question per attestation
    __table_args__ = (
        UniqueConstraint('attestation_id', 'question_id', name='uq_response_attestation_question'),
    )

    # Relationships
    attestation: Mapped["AttestationRecord"] = relationship(
        "AttestationRecord", back_populates="responses"
    )
    question: Mapped["TaxonomyValue"] = relationship("TaxonomyValue")


# ============================================================================
# AttestationEvidence - URL attachments (optional)
# ============================================================================

class AttestationEvidence(Base):
    """
    Evidence URL attached to an attestation.
    Evidence is entirely optional.
    """
    __tablename__ = "attestation_evidence"

    evidence_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attestation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("attestation_records.attestation_id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Evidence type
    evidence_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default=AttestationEvidenceType.OTHER.value
    )

    # URL (validated as URL format on API layer)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)

    # Description
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Audit
    added_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )

    # Relationships
    attestation: Mapped["AttestationRecord"] = relationship(
        "AttestationRecord", back_populates="evidence"
    )
    added_by: Mapped["User"] = relationship("User")


# ============================================================================
# AttestationSchedulingRule - Admin-configurable rules engine
# ============================================================================

class AttestationSchedulingRule(Base):
    """
    Scheduling rule for attestation frequency.
    Risk tier does NOT affect frequency - only coverage targets.
    """
    __tablename__ = "attestation_scheduling_rules"

    rule_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Rule type
    rule_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default=AttestationSchedulingRuleType.GLOBAL_DEFAULT.value
    )

    # Frequency
    frequency: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AttestationFrequency.ANNUAL.value
    )

    # Priority (higher wins)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    # Active status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # OWNER_THRESHOLD conditions
    owner_model_count_min: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="Minimum model count for owner to trigger this rule"
    )
    owner_high_fluctuation_flag: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True,
        comment="If true, applies to owners with high_fluctuation_flag set"
    )

    # MODEL_OVERRIDE condition
    model_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), nullable=True
    )

    # REGIONAL_OVERRIDE condition
    region_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("regions.region_id", ondelete="CASCADE"), nullable=True
    )

    # Effective dates
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Audit
    created_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False
    )
    updated_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    model: Mapped[Optional["Model"]] = relationship("Model")
    region: Mapped[Optional["Region"]] = relationship("Region")
    created_by: Mapped["User"] = relationship(
        "User", foreign_keys=[created_by_user_id]
    )
    updated_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[updated_by_user_id]
    )


# ============================================================================
# AttestationChangeLink - lightweight tracking table for inventory changes
# ============================================================================

class AttestationChangeLink(Base):
    """
    Lightweight link between attestations and inventory changes made through
    existing workflows (Model Edit, Model Create, Decommissioning).

    Design Philosophy: No duplicate data storage - just foreign key references.
    All approval workflows remain in their existing pages.
    """
    __tablename__ = "attestation_change_links"

    link_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attestation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("attestation_records.attestation_id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Change type
    change_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    # Link to ModelPendingEdit (for MODEL_EDIT and NEW_MODEL)
    pending_edit_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("model_pending_edits.pending_edit_id", ondelete="SET NULL"),
        nullable=True
    )

    # Link to Model (for tracking which model was created/edited)
    model_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="SET NULL"), nullable=True
    )

    # Link to DecommissioningRequest (for DECOMMISSION)
    decommissioning_request_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("decommissioning_requests.request_id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )

    # Relationships
    attestation: Mapped["AttestationRecord"] = relationship(
        "AttestationRecord", back_populates="change_links"
    )
    pending_edit: Mapped[Optional["ModelPendingEdit"]] = relationship("ModelPendingEdit")
    model: Mapped[Optional["Model"]] = relationship("Model")
    decommissioning_request: Mapped[Optional["DecommissioningRequest"]] = relationship("DecommissioningRequest")


# ============================================================================
# CoverageTarget - Admin-configurable per risk tier (GLOBAL)
# ============================================================================

class CoverageTarget(Base):
    """
    Coverage target by risk tier. Targets are global (not cycle-specific).
    is_blocking determines if cycle can close without meeting target.
    """
    __tablename__ = "attestation_coverage_targets"

    target_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Risk tier (links to taxonomy value)
    risk_tier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id", ondelete="RESTRICT"),
        nullable=False, index=True
    )

    # Target percentage (e.g., 100.00 for 100%)
    target_percentage: Mapped[float] = mapped_column(
        DECIMAL(5, 2), nullable=False
    )

    # If true, cycle cannot close until target is met
    is_blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Effective dates
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Audit
    created_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    risk_tier: Mapped["TaxonomyValue"] = relationship("TaxonomyValue")
    created_by: Mapped["User"] = relationship("User")


# ============================================================================
# AttestationQuestionConfig - Extended config for attestation questions
# ============================================================================

class AttestationQuestionConfig(Base):
    """
    Extended configuration for attestation questions stored in TaxonomyValue.
    Links to a TaxonomyValue in the 'Attestation Questions' taxonomy.
    """
    __tablename__ = "attestation_question_configs"

    config_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_value_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id", ondelete="CASCADE"),
        nullable=False, unique=True
    )

    # Frequency scope determines when question appears
    frequency_scope: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AttestationQuestionFrequency.BOTH.value
    )

    # If true, comment required when answer is No
    requires_comment_if_no: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Relationships
    question_value: Mapped["TaxonomyValue"] = relationship("TaxonomyValue")


# ============================================================================
# AttestationBulkSubmission - Bulk attestation sessions and drafts
# ============================================================================

class AttestationBulkSubmission(Base):
    """
    Tracks bulk attestation submission sessions and draft state.
    One bulk submission per user per cycle.
    """
    __tablename__ = "attestation_bulk_submissions"

    bulk_submission_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("attestation_cycles.cycle_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Draft state: DRAFT or SUBMITTED
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AttestationBulkSubmissionStatus.DRAFT.value
    )

    # Snapshot of selections (for draft persistence) - stored as JSONB
    selected_model_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    excluded_model_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    draft_responses: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    draft_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Submission tracking
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    attestation_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    # Unique constraint: one bulk submission per user per cycle
    __table_args__ = (
        UniqueConstraint('cycle_id', 'user_id', name='uq_bulk_submission_cycle_user'),
        Index('ix_bulk_submissions_status', 'status'),
    )

    # Relationships
    cycle: Mapped["AttestationCycle"] = relationship(
        "AttestationCycle", back_populates="bulk_submissions"
    )
    user: Mapped["User"] = relationship("User")
    attestation_records: Mapped[List["AttestationRecord"]] = relationship(
        "AttestationRecord", back_populates="bulk_submission"
    )
