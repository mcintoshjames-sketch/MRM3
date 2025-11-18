"""Model model - minimal schema."""
import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ModelStatus(str, enum.Enum):
    """Model status."""
    ACTIVE = "Active"
    IN_DEVELOPMENT = "In Development"
    RETIRED = "Retired"


class DevelopmentType(str, enum.Enum):
    """Model development type."""
    IN_HOUSE = "In-House"
    THIRD_PARTY = "Third-Party"


# Association table for model users (many-to-many)
model_users = Table(
    "model_users",
    Base.metadata,
    Column("model_id", Integer, ForeignKey("models.model_id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True),
)

# Association table for model regulatory categories (many-to-many)
model_regulatory_categories = Table(
    "model_regulatory_categories",
    Base.metadata,
    Column("model_id", Integer, ForeignKey("models.model_id", ondelete="CASCADE"), primary_key=True),
    Column("value_id", Integer, ForeignKey("taxonomy_values.value_id", ondelete="CASCADE"), primary_key=True),
)


class Model(Base):
    """Model table - minimal schema."""
    __tablename__ = "models"

    model_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    development_type: Mapped[DevelopmentType] = mapped_column(
        String(50), nullable=False, default=DevelopmentType.IN_HOUSE)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False)
    developer_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=True)
    vendor_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("vendors.vendor_id"), nullable=True)
    status: Mapped[ModelStatus] = mapped_column(
        String(50), nullable=False, default=ModelStatus.IN_DEVELOPMENT)
    risk_tier_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=True)
    validation_type_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=True)
    model_type_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=True)
    ownership_type_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])
    developer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[developer_id])
    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor")
    users: Mapped[List["User"]] = relationship("User", secondary=model_users, backref="models_used")
    risk_tier: Mapped[Optional["TaxonomyValue"]] = relationship("TaxonomyValue", foreign_keys=[risk_tier_id])
    validation_type: Mapped[Optional["TaxonomyValue"]] = relationship("TaxonomyValue", foreign_keys=[validation_type_id])
    model_type: Mapped[Optional["TaxonomyValue"]] = relationship("TaxonomyValue", foreign_keys=[model_type_id])
    ownership_type: Mapped[Optional["TaxonomyValue"]] = relationship("TaxonomyValue", foreign_keys=[ownership_type_id])
    regulatory_categories: Mapped[List["TaxonomyValue"]] = relationship(
        "TaxonomyValue", secondary=model_regulatory_categories)
    # Legacy validations - kept for backwards compatibility
    validations: Mapped[List["Validation"]] = relationship(
        "Validation", back_populates="model", cascade="all, delete-orphan", order_by="desc(Validation.validation_date)"
    )
    # New workflow-based validation requests
    validation_requests: Mapped[List["ValidationRequest"]] = relationship(
        "ValidationRequest", back_populates="model", cascade="all, delete-orphan", order_by="desc(ValidationRequest.request_date)"
    )
    # Regional metadata links
    model_regions: Mapped[List["ModelRegion"]] = relationship(
        "ModelRegion", back_populates="model", cascade="all, delete-orphan"
    )
