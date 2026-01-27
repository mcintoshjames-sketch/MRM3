"""IRP (Independent Review Process) models for MRSA oversight."""
from datetime import datetime, date
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Integer, Text, DateTime, Date, ForeignKey, Table, Column, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.model import Model
    from app.models.taxonomy import TaxonomyValue


# Association table for MRSA-IRP many-to-many relationship
mrsa_irp = Table(
    "mrsa_irp",
    Base.metadata,
    Column("model_id", Integer, ForeignKey("models.model_id", ondelete="CASCADE"), primary_key=True),
    Column("irp_id", Integer, ForeignKey("irps.irp_id", ondelete="CASCADE"), primary_key=True),
)


class IRP(Base):
    """Independent Review Process - oversight mechanism for MRSAs.

    An IRP is an independent review process that provides oversight for
    Model Risk-Sensitive Applications (MRSAs). One IRP can cover multiple MRSAs.
    """
    __tablename__ = "irps"

    irp_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    process_name: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Name of the Independent Review Process"
    )
    contact_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False,
        comment="Primary contact person responsible for this IRP"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Description of the IRP scope and purpose"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="Whether this IRP is currently active"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    contact_user: Mapped["User"] = relationship(
        "User", foreign_keys=[contact_user_id]
    )
    covered_mrsas: Mapped[List["Model"]] = relationship(
        "Model", secondary=mrsa_irp, back_populates="irps"
    )
    reviews: Mapped[List["IRPReview"]] = relationship(
        "IRPReview", back_populates="irp", cascade="all, delete-orphan",
        order_by="desc(IRPReview.review_date)"
    )
    certifications: Mapped[List["IRPCertification"]] = relationship(
        "IRPCertification", back_populates="irp", cascade="all, delete-orphan",
        order_by="desc(IRPCertification.certification_date)"
    )

    @property
    def covered_mrsa_count(self) -> int:
        """Count of MRSAs covered by this IRP."""
        return len(self.covered_mrsas) if self.covered_mrsas else 0

    @property
    def latest_review(self) -> Optional["IRPReview"]:
        """Most recent review for this IRP."""
        return self.reviews[0] if self.reviews else None

    @property
    def latest_certification(self) -> Optional["IRPCertification"]:
        """Most recent certification for this IRP."""
        return self.certifications[0] if self.certifications else None


class IRPReview(Base):
    """Periodic assessment of MRSAs covered by an IRP.

    IRP Reviews are performed periodically to assess whether the MRSAs
    covered by the IRP continue to meet requirements. Each review has
    an outcome (Satisfactory, Conditionally Satisfactory, Not Satisfactory).
    """
    __tablename__ = "irp_reviews"

    review_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    irp_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("irps.irp_id", ondelete="CASCADE"), nullable=False, index=True,
        comment="IRP being reviewed"
    )
    review_date: Mapped[date] = mapped_column(
        Date, nullable=False,
        comment="Date the review was completed"
    )
    outcome_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False,
        comment="IRP Review Outcome taxonomy value (Satisfactory, etc.)"
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Notes and observations from the review"
    )
    reviewed_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False,
        comment="User who performed the review"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    irp: Mapped["IRP"] = relationship("IRP", back_populates="reviews")
    outcome: Mapped["TaxonomyValue"] = relationship("TaxonomyValue", foreign_keys=[outcome_id])
    reviewed_by: Mapped["User"] = relationship("User", foreign_keys=[reviewed_by_user_id])


class IRPCertification(Base):
    """MRM certification that an IRP is adequately designed.

    IRP Certifications are performed by MRM to validate that the IRP itself
    is adequately designed to detect and manage MRSA risk. This is separate
    from the periodic reviews which assess the MRSAs themselves.
    """
    __tablename__ = "irp_certifications"

    certification_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    irp_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("irps.irp_id", ondelete="CASCADE"), nullable=False, index=True,
        comment="IRP being certified"
    )
    certification_date: Mapped[date] = mapped_column(
        Date, nullable=False,
        comment="Date the certification was completed"
    )
    certified_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False,
        comment="MRM person who performed the certification"
    )
    certified_by_email: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Email address of the individual who performed the certification"
    )
    conclusion_summary: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Narrative summary of the certification conclusion"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    irp: Mapped["IRP"] = relationship("IRP", back_populates="certifications")
    certified_by_user: Mapped["User"] = relationship("User", foreign_keys=[certified_by_user_id])
