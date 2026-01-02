"""Model-Application relationship model."""
from datetime import datetime, date
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Integer, Text, DateTime, Date, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now

if TYPE_CHECKING:
    from app.models.model import Model
    from app.models.map_application import MapApplication
    from app.models.taxonomy import TaxonomyValue
    from app.models.user import User


class ModelApplication(Base):
    """
    Junction table linking models to supporting applications from MAP.
    Tracks which applications are integral to a model's end-to-end process.
    """
    __tablename__ = "model_applications"

    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"),
        primary_key=True
    )
    application_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("map_applications.application_id", ondelete="CASCADE"),
        primary_key=True
    )
    relationship_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"),
        nullable=False,
        comment="Type of relationship (Data Source, Execution Platform, etc.)"
    )
    relationship_direction: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        default="UNKNOWN",
        comment="Direction relative to model: UPSTREAM, DOWNSTREAM, or UNKNOWN"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Notes about this specific relationship"
    )
    effective_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True,
        comment="When this relationship became effective"
    )
    end_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True,
        comment="When this relationship ended (soft delete)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    model: Mapped["Model"] = relationship("Model", back_populates="applications")
    application: Mapped["MapApplication"] = relationship("MapApplication")
    relationship_type: Mapped["TaxonomyValue"] = relationship("TaxonomyValue")
    created_by_user: Mapped[Optional["User"]] = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "relationship_direction IN ('UPSTREAM', 'DOWNSTREAM', 'UNKNOWN') OR relationship_direction IS NULL",
            name="chk_model_application_direction"
        ),
    )
