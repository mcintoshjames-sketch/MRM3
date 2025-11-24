"""Conditional approval models for model use approvals."""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ApproverRole(Base):
    """Catalog of approver roles/committees that can approve model use."""
    __tablename__ = "approver_roles"

    role_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Examples: "US Model Risk Management Committee", "Risk Committee", "Board of Directors"

    # Relationships
    rule_associations: Mapped[List["RuleRequiredApprover"]] = relationship(
        back_populates="approver_role", cascade="all, delete-orphan"
    )


class ConditionalApprovalRule(Base):
    """Rules that determine when additional approvals are required for model use.

    Logic: All non-empty condition fields must match (AND across dimensions).
    Within each field, values are OR'd (any match satisfies that dimension).
    Empty/null field = no constraint on that dimension (matches ANY value).

    Example: validation_type_ids="1,2" AND risk_tier_ids="3" means:
    - Validation type must be 1 OR 2, AND
    - Risk tier must be 3
    """
    __tablename__ = "conditional_approval_rules"

    rule_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Condition fields - store as comma-separated IDs (empty/null = ANY)
    validation_type_ids: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Comma-separated validation type IDs (empty = any validation type)"
    )
    risk_tier_ids: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Comma-separated risk tier IDs (empty = any risk tier)"
    )
    governance_region_ids: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Comma-separated governance region IDs (empty = any governance region)"
    )
    deployed_region_ids: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Comma-separated deployed region IDs (empty = any deployed region)"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    required_approvers: Mapped[List["RuleRequiredApprover"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )

    def parse_id_list(self, field_value: Optional[str]) -> List[int]:
        """Parse comma-separated ID string into list of integers."""
        if not field_value or not field_value.strip():
            return []
        return [int(id_str.strip()) for id_str in field_value.split(',') if id_str.strip()]

    def get_validation_type_ids(self) -> List[int]:
        """Get parsed validation type IDs."""
        return self.parse_id_list(self.validation_type_ids)

    def get_risk_tier_ids(self) -> List[int]:
        """Get parsed risk tier IDs."""
        return self.parse_id_list(self.risk_tier_ids)

    def get_governance_region_ids(self) -> List[int]:
        """Get parsed governance region IDs."""
        return self.parse_id_list(self.governance_region_ids)

    def get_deployed_region_ids(self) -> List[int]:
        """Get parsed deployed region IDs."""
        return self.parse_id_list(self.deployed_region_ids)


class RuleRequiredApprover(Base):
    """Many-to-many: which approver roles are required by each rule."""
    __tablename__ = "rule_required_approvers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conditional_approval_rules.rule_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    approver_role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("approver_roles.role_id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Relationships
    rule: Mapped["ConditionalApprovalRule"] = relationship(back_populates="required_approvers")
    approver_role: Mapped["ApproverRole"] = relationship(back_populates="rule_associations")
