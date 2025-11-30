"""Model Recommendations - tracking issues identified during validation.

Implements full lifecycle from draft through closure with action plan tracking,
rebuttal workflow, and multi-stakeholder approval process.
"""
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Text, Boolean, ForeignKey, DateTime, Date,
    UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now


class Recommendation(Base):
    """
    Core recommendation entity tracking issues identified during validation.
    Supports full lifecycle from draft through closure with action plan tracking.
    """
    __tablename__ = "recommendations"

    recommendation_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Auto-generated code (e.g., "REC-2025-00001")
    recommendation_code: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True, index=True
    )

    # Core identification
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    validation_request_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("validation_requests.request_id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Link to originating validation (if applicable)"
    )
    monitoring_cycle_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("monitoring_cycles.cycle_id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Link to originating monitoring cycle (if applicable)"
    )

    # Content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Classification
    priority_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False,
        comment="High/Medium/Low - determines closure approval requirements"
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=True,
        comment="e.g., Data Quality, Methodology, Implementation, Documentation"
    )

    # Workflow status
    current_status_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )

    # Actors
    created_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False,
        comment="Validator who identified the issue"
    )
    assigned_to_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False,
        comment="Developer/Owner responsible for remediation"
    )

    # Target dates
    original_target_date: Mapped[date] = mapped_column(Date, nullable=False)
    current_target_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Closure fields
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    closure_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Finalization tracking
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finalized_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    acknowledged_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    model = relationship("Model", back_populates="recommendations")
    validation_request = relationship("ValidationRequest")
    monitoring_cycle = relationship("MonitoringCycle")
    priority = relationship("TaxonomyValue", foreign_keys=[priority_id])
    category = relationship("TaxonomyValue", foreign_keys=[category_id])
    current_status = relationship("TaxonomyValue", foreign_keys=[current_status_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    closed_by = relationship("User", foreign_keys=[closed_by_id])
    finalized_by = relationship("User", foreign_keys=[finalized_by_id])
    acknowledged_by = relationship("User", foreign_keys=[acknowledged_by_id])

    # One-to-many
    action_plan_tasks: Mapped[List["ActionPlanTask"]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan",
        order_by="ActionPlanTask.task_order"
    )
    rebuttals: Mapped[List["RecommendationRebuttal"]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan",
        order_by="desc(RecommendationRebuttal.submitted_at)"
    )
    closure_evidence: Mapped[List["ClosureEvidence"]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan"
    )
    status_history: Mapped[List["RecommendationStatusHistory"]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan",
        order_by="desc(RecommendationStatusHistory.changed_at)"
    )
    approvals: Mapped[List["RecommendationApproval"]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan"
    )


class ActionPlanTask(Base):
    """Individual remediation task within an action plan."""
    __tablename__ = "action_plan_tasks"

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recommendations.recommendation_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    task_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    completion_status_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False,
        comment="NOT_STARTED, IN_PROGRESS, COMPLETED"
    )
    completion_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    recommendation = relationship("Recommendation", back_populates="action_plan_tasks")
    owner = relationship("User", foreign_keys=[owner_id])
    completion_status = relationship("TaxonomyValue", foreign_keys=[completion_status_id])

    __table_args__ = (
        UniqueConstraint('recommendation_id', 'task_order', name='uq_rec_task_order'),
    )


class RecommendationRebuttal(Base):
    """Tracks rebuttal submissions and their review outcomes."""
    __tablename__ = "recommendation_rebuttals"

    rebuttal_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recommendations.recommendation_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    submitted_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    # Review fields (populated when validator reviews)
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_decision: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        comment="ACCEPT (issue dropped) or OVERRIDE (action plan required)"
    )
    review_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Track which is the current/latest rebuttal
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    recommendation = relationship("Recommendation", back_populates="rebuttals")
    submitted_by = relationship("User", foreign_keys=[submitted_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])

    __table_args__ = (
        CheckConstraint(
            "review_decision IN ('ACCEPT', 'OVERRIDE') OR review_decision IS NULL",
            name='chk_rebuttal_decision'
        ),
    )


class ClosureEvidence(Base):
    """Evidence/documentation submitted to support recommendation closure."""
    __tablename__ = "closure_evidence"

    evidence_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recommendations.recommendation_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Storage path or URL to evidence document"
    )
    file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uploaded_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    # Relationships
    recommendation = relationship("Recommendation", back_populates="closure_evidence")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])


class RecommendationStatusHistory(Base):
    """Complete audit trail of all status changes."""
    __tablename__ = "recommendation_status_history"

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recommendations.recommendation_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    old_status_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=True
    )
    new_status_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    changed_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Store additional context as JSON (e.g., rebuttal_id, approval details)
    additional_context: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="JSON storing action-specific details"
    )

    # Relationships
    recommendation = relationship("Recommendation", back_populates="status_history")
    old_status = relationship("TaxonomyValue", foreign_keys=[old_status_id])
    new_status = relationship("TaxonomyValue", foreign_keys=[new_status_id])
    changed_by = relationship("User", foreign_keys=[changed_by_id])


class RecommendationApproval(Base):
    """
    Approval records for closure workflow.
    Follows the same pattern as MonitoringCycleApproval and ValidationApproval
    for Global/Regional approval requirements.
    """
    __tablename__ = "recommendation_approvals"

    approval_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recommendations.recommendation_id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Approval type and region tracking (mirrors MonitoringCycleApproval)
    approval_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="'GLOBAL' or 'REGIONAL'"
    )
    region_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("regions.region_id", ondelete="CASCADE"), nullable=True,
        comment="Required if approval_type='REGIONAL', NULL for GLOBAL"
    )

    # Historical context: What role did the approver represent at approval time?
    represented_region_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("regions.region_id", ondelete="SET NULL"), nullable=True, index=True,
        comment="Region the approver was representing at approval time (NULL for Global Approver)"
    )

    # Approver (populated when approval is submitted)
    approver_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    approval_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING",
        comment="PENDING, APPROVED, REJECTED, VOIDED"
    )
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Admin can approve on behalf with evidence (like MonitoringCycleApproval)
    approval_evidence: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Description of approval evidence (meeting minutes, email, etc.) - required for Admin proxy approvals"
    )

    # Voiding fields (Admin can void approval requirements)
    voided_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    void_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    # Relationships
    recommendation = relationship("Recommendation", back_populates="approvals")
    approver = relationship("User", foreign_keys=[approver_id])
    voided_by = relationship("User", foreign_keys=[voided_by_id])
    region = relationship("Region", foreign_keys=[region_id])
    represented_region = relationship("Region", foreign_keys=[represented_region_id])

    __table_args__ = (
        UniqueConstraint('recommendation_id', 'approval_type', 'region_id', name='uq_rec_approval_type_region'),
        CheckConstraint(
            "approval_type IN ('GLOBAL', 'REGIONAL')",
            name='chk_rec_approval_type'
        ),
        CheckConstraint(
            "approval_status IN ('PENDING', 'APPROVED', 'REJECTED', 'VOIDED')",
            name='chk_rec_approval_status'
        ),
    )


class RecommendationPriorityConfig(Base):
    """
    Admin-configurable approval requirements per priority level.
    Similar pattern to ValidationPolicy - allows admins to change which
    priority levels require Global/Regional approvals for closure.
    """
    __tablename__ = "recommendation_priority_configs"

    config_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    priority_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False, unique=True,
        comment="FK to priority taxonomy value (High/Medium/Low)"
    )
    requires_final_approval: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="If true, closure requires Global + Regional approvals after Validator approval"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Admin notes explaining the configuration"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    priority = relationship("TaxonomyValue", foreign_keys=[priority_id])
