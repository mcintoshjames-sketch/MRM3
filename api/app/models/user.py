"""User model."""
import enum
from sqlalchemy import String, Integer, Table, Column, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, TYPE_CHECKING
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.lob import LOBUnit


# Association table for user-region many-to-many relationship
user_regions = Table(
    'user_regions',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True),
    Column('region_id', Integer, ForeignKey('regions.region_id', ondelete='CASCADE'), primary_key=True)
)


class UserRole(str, enum.Enum):
    """User roles."""
    ADMIN = "Admin"
    USER = "User"
    VALIDATOR = "Validator"
    GLOBAL_APPROVER = "Global Approver"
    REGIONAL_APPROVER = "Regional Approver"


class User(Base):
    """User model."""
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        String(50), nullable=False, default=UserRole.USER)
    # Attestation: high fluctuation flag for quarterly attestation requirement
    high_fluctuation_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Manual toggle by Admin; triggers quarterly attestations"
    )

    # LOB (Line of Business) assignment - required for all users
    lob_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lob_units.lob_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="User's assigned LOB unit (required)"
    )

    # LOB relationship
    lob: Mapped["LOBUnit"] = relationship(
        "LOBUnit",
        back_populates="users",
        foreign_keys=[lob_id]
    )

    # Regions relationship (for Regional Approvers)
    regions: Mapped[List["Region"]] = relationship(
        "Region", secondary=user_regions, back_populates="approvers"
    )
