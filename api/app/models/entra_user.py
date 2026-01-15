"""Mock Microsoft Entra (Azure AD) user model."""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from app.core.time import utc_now


class EntraUser(Base):
    """
    Mock Microsoft Entra directory user.

    This simulates an organizational directory that would normally be
    accessed via Microsoft Graph API. In production, this would be
    replaced with actual Entra ID integration.

    Lifecycle states:
    - Active: in_recycle_bin=False, account_enabled=True
    - IT Lockout: in_recycle_bin=False, account_enabled=False
    - Soft Deleted: in_recycle_bin=True (in Azure AD recycle bin)
    - Hard Deleted: Record removed from this table
    """
    __tablename__ = "entra_users"

    object_id: Mapped[str] = mapped_column(String(36), primary_key=True)  # Azure AD Object ID (UUID)
    user_principal_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    given_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    surname: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mail: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    office_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mobile_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    account_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    in_recycle_bin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
