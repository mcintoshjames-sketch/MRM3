"""MAP Application model - Mock Managed Application Portfolio inventory."""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class MapApplication(Base):
    """
    Mock application inventory table simulating the organization's
    Managed Application Portfolio (MAP) system.

    In production, this would be replaced with a sync from or
    direct integration with the actual MAP system.
    """
    __tablename__ = "map_applications"

    application_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False,
        comment="Unique identifier from MAP system (e.g., APP-12345)"
    )
    application_name: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Display name of the application"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Description of the application's purpose"
    )
    owner_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
        comment="Application owner/steward name"
    )
    owner_email: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
        comment="Application owner email"
    )
    department: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
        comment="Department responsible for the application"
    )
    technology_stack: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
        comment="Technology stack (e.g., Python/AWS Lambda, Java/On-Prem)"
    )
    criticality_tier: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        comment="Application criticality: Critical, High, Medium, Low"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Active",
        comment="Application status: Active, Decommissioned, In Development"
    )
    external_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True,
        comment="Link to MAP system record for this application"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
