"""LOB (Line of Business) unit model for organizational hierarchy."""
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Index, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, TYPE_CHECKING
from app.models.base import Base
from app.core.time import utc_now

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.team import Team


class LOBUnit(Base):
    """LOB Unit model for organizational hierarchy.

    Represents a node in the organizational hierarchy (SBU → LOB1 → LOB2 → etc.).
    Uses self-referential foreign key to support unlimited depth.
    """
    __tablename__ = "lob_units"

    lob_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("lob_units.lob_id", ondelete="RESTRICT"),
        nullable=True,
        index=True
    )
    team_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("teams.team_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Hierarchy depth: 1=SBU, 2=LOB1, 3=LOB2, etc."
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # External org unit identifier (5 characters: digits for real, S#### for synthetic)
    org_unit: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        unique=True,
        index=True,
        comment="External org unit identifier (5 chars, e.g., 12345 or S0001)"
    )

    # Description (from Lob*Description columns in CSV import)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Org Unit metadata (populated on leaf nodes from CSV import)
    contact_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    org_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    legal_entity_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    legal_entity_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    short_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tier: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Self-referential relationships
    parent: Mapped[Optional["LOBUnit"]] = relationship(
        "LOBUnit",
        back_populates="children",
        remote_side="LOBUnit.lob_id"
    )
    children: Mapped[List["LOBUnit"]] = relationship(
        "LOBUnit",
        back_populates="parent",
        order_by="LOBUnit.sort_order, LOBUnit.name"
    )

    # Users in this LOB unit
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="lob",
        foreign_keys="User.lob_id"
    )

    # Direct team assignment (optional)
    team: Mapped[Optional["Team"]] = relationship(
        "Team",
        back_populates="lob_units"
    )

    __table_args__ = (
        # Unique constraint on (parent_id, code) to prevent duplicate codes within same parent
        UniqueConstraint("parent_id", "code", name="uq_lob_parent_code"),
        # Index on is_active for filtered queries
        Index("ix_lob_units_is_active", "is_active"),
    )

    @property
    def full_path(self) -> str:
        """Compute full path from root to this node (e.g., 'SBU > LOB1 > LOB2')."""
        path_parts = []
        current = self
        while current:
            path_parts.insert(0, current.name)
            current = current.parent
        return " > ".join(path_parts)

    def __repr__(self) -> str:
        return f"<LOBUnit(lob_id={self.lob_id}, code={self.code}, name={self.name}, level={self.level})>"
