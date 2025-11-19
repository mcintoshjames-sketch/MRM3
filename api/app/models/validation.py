"""Validation workflow models."""
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Date, Boolean, Float, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


# Association table for validation request models (many-to-many)
validation_request_models = Table(
    "validation_request_models",
    Base.metadata,
    Column("request_id", Integer, ForeignKey("validation_requests.request_id", ondelete="CASCADE"), primary_key=True),
    Column("model_id", Integer, ForeignKey("models.model_id", ondelete="CASCADE"), primary_key=True),
)


class ValidationPolicy(Base):
    """Validation policy configuration by risk tier."""
    __tablename__ = "validation_policies"

    policy_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    risk_tier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False, unique=True
    )
    frequency_months: Mapped[int] = mapped_column(
        Integer, nullable=False, default=12)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    risk_tier = relationship("TaxonomyValue", foreign_keys=[risk_tier_id])


class ValidationWorkflowSLA(Base):
    """SLA configuration for validation workflow phases."""
    __tablename__ = "validation_workflow_slas"

    sla_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workflow_type: Mapped[str] = mapped_column(String(100), nullable=False, default="Validation")
    assignment_days: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    begin_work_days: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    complete_work_days: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    approval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    model_change_lead_time_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=90,
        comment="Lead time in days before model change implementation date to trigger interim validation"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ValidationRequest(Base):
    """Main validation request entity - workflow-based."""
    __tablename__ = "validation_requests"

    request_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    requestor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    validation_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    priority_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    target_completion_date: Mapped[date] = mapped_column(Date, nullable=False)
    trigger_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_status_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    region_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("regions.region_id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Admin decline fields
    declined_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=True
    )
    decline_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    declined_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    models: Mapped[List["Model"]] = relationship(
        "Model", secondary=validation_request_models, back_populates="validation_requests"
    )
    region = relationship("Region")
    requestor = relationship("User", foreign_keys=[requestor_id])
    declined_by = relationship("User", foreign_keys=[declined_by_id])
    validation_type = relationship("TaxonomyValue", foreign_keys=[validation_type_id])
    priority = relationship("TaxonomyValue", foreign_keys=[priority_id])
    current_status = relationship("TaxonomyValue", foreign_keys=[current_status_id])

    # One-to-many relationships
    status_history: Mapped[List["ValidationStatusHistory"]] = relationship(
        back_populates="request", cascade="all, delete-orphan", order_by="desc(ValidationStatusHistory.changed_at)"
    )
    assignments: Mapped[List["ValidationAssignment"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )
    work_components: Mapped[List["ValidationWorkComponent"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )
    approvals: Mapped[List["ValidationApproval"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )

    # One-to-one relationship with outcome
    outcome: Mapped[Optional["ValidationOutcome"]] = relationship(
        back_populates="request", uselist=False, cascade="all, delete-orphan"
    )

    # One-to-one relationship with review outcome
    review_outcome: Mapped[Optional["ValidationReviewOutcome"]] = relationship(
        back_populates="request", uselist=False, cascade="all, delete-orphan"
    )


class ValidationStatusHistory(Base):
    """Audit trail for validation status changes."""
    __tablename__ = "validation_status_history"

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validation_requests.request_id", ondelete="CASCADE"), nullable=False
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
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    request = relationship("ValidationRequest", back_populates="status_history")
    old_status = relationship("TaxonomyValue", foreign_keys=[old_status_id])
    new_status = relationship("TaxonomyValue", foreign_keys=[new_status_id])
    changed_by = relationship("User", foreign_keys=[changed_by_id])


class ValidationAssignment(Base):
    """Validator assignment to a validation request."""
    __tablename__ = "validation_assignments"

    assignment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validation_requests.request_id", ondelete="CASCADE"), nullable=False
    )
    validator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_reviewer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    assignment_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0)
    independence_attestation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Reviewer sign-off fields
    reviewer_signed_off: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewer_signed_off_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reviewer_sign_off_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    request = relationship("ValidationRequest", back_populates="assignments")
    validator = relationship("User", foreign_keys=[validator_id])


class ValidationWorkComponent(Base):
    """Individual work component tracking for a validation."""
    __tablename__ = "validation_work_components"

    component_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validation_requests.request_id", ondelete="CASCADE"), nullable=False
    )
    component_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    status_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    request = relationship("ValidationRequest", back_populates="work_components")
    component_type = relationship("TaxonomyValue", foreign_keys=[component_type_id])
    status = relationship("TaxonomyValue", foreign_keys=[status_id])


class ValidationOutcome(Base):
    """Validation outcome - only created after work is complete."""
    __tablename__ = "validation_outcomes"

    outcome_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validation_requests.request_id", ondelete="CASCADE"), nullable=False, unique=True
    )
    overall_rating_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_review_frequency: Mapped[int] = mapped_column(Integer, nullable=False)  # in months
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiration_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    request = relationship("ValidationRequest", back_populates="outcome")
    overall_rating = relationship("TaxonomyValue", foreign_keys=[overall_rating_id])


class ValidationReviewOutcome(Base):
    """Review outcome - created by reviewer when reviewing validation outcome."""
    __tablename__ = "validation_review_outcomes"

    review_outcome_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validation_requests.request_id", ondelete="CASCADE"), nullable=False, unique=True
    )
    reviewer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(50), nullable=False)  # 'AGREE' or 'SEND_BACK'
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agrees_with_rating: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    review_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    request = relationship("ValidationRequest", back_populates="review_outcome")
    reviewer = relationship("User", foreign_keys=[reviewer_id])


class ValidationApproval(Base):
    """Approval record for a validation request."""
    __tablename__ = "validation_approvals"

    approval_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validation_requests.request_id", ondelete="CASCADE"), nullable=False
    )
    approver_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    approver_role: Mapped[str] = mapped_column(String(100), nullable=False)  # Validator, Validation Head, Model Owner, Risk Officer
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    approval_status: Mapped[str] = mapped_column(String(50), nullable=False, default="Pending")  # Pending, Approved, Rejected
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Admin unlink fields
    unlinked_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=True
    )
    unlink_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unlinked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    request = relationship("ValidationRequest", back_populates="approvals")
    approver = relationship("User", foreign_keys=[approver_id])
    unlinked_by = relationship("User", foreign_keys=[unlinked_by_id])


# Keep old Validation model for backwards compatibility during migration
# This will be removed after migration is complete
class Validation(Base):
    """DEPRECATED: Legacy validation record. Use ValidationRequest instead."""
    __tablename__ = "validations"

    validation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), nullable=False
    )
    validation_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    validator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    validation_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    outcome_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    scope_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=True
    )
    region_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("regions.region_id", ondelete="SET NULL"), nullable=True, index=True
    )
    findings_summary: Mapped[str] = mapped_column(Text, nullable=True)
    report_reference: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    model = relationship("Model", back_populates="validations")
    validator = relationship("User", foreign_keys=[validator_id])
    region = relationship("Region")
    validation_type = relationship(
        "TaxonomyValue", foreign_keys=[validation_type_id])
    outcome = relationship("TaxonomyValue", foreign_keys=[outcome_id])
    scope = relationship("TaxonomyValue", foreign_keys=[scope_id])
