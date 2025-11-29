"""Mock Microsoft Entra (Azure AD) user model."""
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base
from app.core.time import utc_now


class EntraUser(Base):
    """
    Mock Microsoft Entra directory user.

    This simulates an organizational directory that would normally be
    accessed via Microsoft Graph API. In production, this would be
    replaced with actual Entra ID integration.
    """
    __tablename__ = "entra_users"

    entra_id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID format
    user_principal_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    given_name: Mapped[str] = mapped_column(String(100), nullable=True)
    surname: Mapped[str] = mapped_column(String(100), nullable=True)
    mail: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=True)
    department: Mapped[str] = mapped_column(String(255), nullable=True)
    office_location: Mapped[str] = mapped_column(String(255), nullable=True)
    mobile_phone: Mapped[str] = mapped_column(String(50), nullable=True)
    account_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
