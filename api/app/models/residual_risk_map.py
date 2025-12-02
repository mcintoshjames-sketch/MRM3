"""Residual Risk Map Configuration Model.

This module defines the database model for the residual risk map configuration,
which maps the combination of Inherent Risk Tier and Scorecard Outcome to a
Residual (Final) Risk Rating.

The matrix is stored as JSON for flexibility and allows admin configuration
through the UI/API.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.core.time import utc_now


class ResidualRiskMapConfig(Base):
    """Residual Risk Map Configuration.

    Stores the 2D matrix that maps (Inherent Risk Tier, Scorecard Outcome)
    to Residual Risk Rating.

    Only one configuration should be active at a time. Historical configurations
    are preserved for audit purposes.

    Matrix Structure (JSON):
    {
        "row_axis_label": "Inherent Risk Tier",
        "column_axis_label": "Scorecard Outcome",
        "row_values": ["High", "Medium", "Low", "Very Low"],
        "column_values": ["Red", "Yellow-", "Yellow", "Yellow+", "Green-", "Green"],
        "result_values": ["High", "Medium", "Low"],
        "matrix": {
            "High": {
                "Red": "High",
                "Yellow-": "High",
                "Yellow": "High",
                "Yellow+": "Medium",
                "Green-": "Medium",
                "Green": "Low"
            },
            ...
        }
    }
    """
    __tablename__ = "residual_risk_map_configs"

    config_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Configuration version tracking
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Sequential version number for tracking changes"
    )
    version_name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Optional display name for this version"
    )

    # The actual matrix configuration stored as JSON
    matrix_config: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        comment="The residual risk matrix configuration"
    )

    # Metadata
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Description or changelog for this version"
    )

    # Active flag - only one config should be active
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Only one configuration should be active at a time"
    )

    # Audit fields
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False
    )

    # Relationship to user who created this config
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_user_id]
    )


# Import User type for relationship typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.user import User
