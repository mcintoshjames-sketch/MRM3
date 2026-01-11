"""User model."""
from sqlalchemy import String, Integer, Table, Column, ForeignKey, Boolean, select
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from typing import List, Optional, TYPE_CHECKING
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.entra_user import EntraUser
    from app.models.lob import LOBUnit
    from app.models.region import Region
    from app.models.role import Role


# Association table for user-region many-to-many relationship
user_regions = Table(
    'user_regions',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True),
    Column('region_id', Integer, ForeignKey('regions.region_id', ondelete='CASCADE'), primary_key=True)
)


class User(Base):
    """User model."""
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("roles.role_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    entra_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("entra_users.entra_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
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

    # Role relationship
    role_ref: Mapped["Role"] = relationship(
        "Role",
        back_populates="users",
        foreign_keys=[role_id]
    )

    # Regions relationship (for Regional Approvers)
    regions: Mapped[List["Region"]] = relationship(
        "Region", secondary=user_regions, back_populates="approvers"
    )
    entra_user: Mapped[Optional["EntraUser"]] = relationship(
        "EntraUser",
        foreign_keys=[entra_id]
    )

    @hybrid_property
    def role_code(self) -> Optional[str]:
        if not self.role_ref:
            return None
        return self.role_ref.code

    @role_code.expression
    def role_code(cls):
        from app.models.role import Role
        return select(Role.code).where(Role.role_id == cls.role_id).scalar_subquery()

    @property
    def role_display(self) -> Optional[str]:
        if not self.role_ref:
            return None
        return self.role_ref.display_name

    @property
    def role(self) -> Optional[str]:
        return self.role_display
