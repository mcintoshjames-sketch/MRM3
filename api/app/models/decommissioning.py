"""Decommissioning models for tracking model retirement workflow."""
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import String, Integer, Text, DateTime, Date, ForeignKey, Boolean, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class DecommissioningRequest(Base):
    """Request to decommission/retire a model."""
    __tablename__ = "decommissioning_requests"

    request_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING"
    )  # PENDING, VALIDATOR_APPROVED, APPROVED, REJECTED, WITHDRAWN
    reason_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    replacement_model_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="SET NULL"), nullable=True
    )
    last_production_date: Mapped[date] = mapped_column(Date, nullable=False)
    gap_justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    archive_location: Mapped[str] = mapped_column(Text, nullable=False)
    downstream_impact_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Creation
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    created_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )

    # Validator review (Stage 1)
    validator_reviewed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    validator_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    validator_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Owner review (Stage 1 - parallel with validator if owner != requestor)
    owner_approval_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    owner_reviewed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    owner_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    owner_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Final status tracking
    final_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    model: Mapped["Model"] = relationship(
        "Model", foreign_keys=[model_id], backref="decommissioning_requests"
    )
    replacement_model: Mapped[Optional["Model"]] = relationship(
        "Model", foreign_keys=[replacement_model_id]
    )
    reason: Mapped["TaxonomyValue"] = relationship(
        "TaxonomyValue", foreign_keys=[reason_id]
    )
    created_by: Mapped["User"] = relationship(
        "User", foreign_keys=[created_by_id]
    )
    validator_reviewed_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[validator_reviewed_by_id]
    )
    owner_reviewed_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[owner_reviewed_by_id]
    )
    status_history: Mapped[List["DecommissioningStatusHistory"]] = relationship(
        "DecommissioningStatusHistory", back_populates="request",
        cascade="all, delete-orphan", order_by="DecommissioningStatusHistory.changed_at"
    )
    approvals: Mapped[List["DecommissioningApproval"]] = relationship(
        "DecommissioningApproval", back_populates="request",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint('model_id != replacement_model_id', name='chk_different_models'),
    )


class DecommissioningStatusHistory(Base):
    """Audit trail for decommissioning request status changes."""
    __tablename__ = "decommissioning_status_history"

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("decommissioning_requests.request_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    old_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    request: Mapped["DecommissioningRequest"] = relationship(
        "DecommissioningRequest", back_populates="status_history"
    )
    changed_by: Mapped["User"] = relationship("User", foreign_keys=[changed_by_id])


class DecommissioningApproval(Base):
    """Approval records for Global/Regional approvers (Stage 2)."""
    __tablename__ = "decommissioning_approvals"

    approval_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("decommissioning_requests.request_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    approver_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # GLOBAL, REGIONAL
    region_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("regions.region_id", ondelete="CASCADE"), nullable=True
    )  # NULL for GLOBAL
    approved_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_approved: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True
    )  # NULL=pending, TRUE=approved, FALSE=rejected
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    request: Mapped["DecommissioningRequest"] = relationship(
        "DecommissioningRequest", back_populates="approvals"
    )
    region: Mapped[Optional["Region"]] = relationship("Region", foreign_keys=[region_id])
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id])

    __table_args__ = (
        UniqueConstraint('request_id', 'approver_type', 'region_id', name='uq_decom_approval_type_region'),
    )
