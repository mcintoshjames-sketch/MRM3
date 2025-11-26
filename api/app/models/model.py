"""Model model - minimal schema."""
import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Table, Column, Boolean
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
    Column("model_id", Integer, ForeignKey(
        "models.model_id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey(
        "users.user_id", ondelete="CASCADE"), primary_key=True),
)

# Association table for model regulatory categories (many-to-many)
model_regulatory_categories = Table(
    "model_regulatory_categories",
    Base.metadata,
    Column("model_id", Integer, ForeignKey(
        "models.model_id", ondelete="CASCADE"), primary_key=True),
    Column("value_id", Integer, ForeignKey(
        "taxonomy_values.value_id", ondelete="CASCADE"), primary_key=True),
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
        Integer, ForeignKey("model_types.type_id"), nullable=True)
    ownership_type_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=True)
    status_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=True)
    wholly_owned_region_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("regions.region_id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Row-level approval workflow fields
    row_approval_status: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        comment="Status of this record in the approval workflow: pending, needs_revision, rejected, or NULL (approved)")
    submitted_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True,
        comment="User who submitted this model for approval")
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True,
        comment="Timestamp when model was first submitted")

    # Conditional model use approval tracking
    use_approval_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True,
        comment="Timestamp when model was approved for use (last required approval granted)")

    # Model vs Non-Model classification
    is_model: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="True for actual models, False for non-model tools/applications")

    # Relationships
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])
    developer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[developer_id])
    submitted_by_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[submitted_by_user_id])
    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor")
    users: Mapped[List["User"]] = relationship(
        "User", secondary=model_users, backref="models_used")
    risk_tier: Mapped[Optional["TaxonomyValue"]] = relationship(
        "TaxonomyValue", foreign_keys=[risk_tier_id])
    validation_type: Mapped[Optional["TaxonomyValue"]] = relationship(
        "TaxonomyValue", foreign_keys=[validation_type_id])
    model_type: Mapped[Optional["ModelType"]] = relationship(
        "ModelType", foreign_keys=[model_type_id])
    ownership_type: Mapped[Optional["TaxonomyValue"]] = relationship(
        "TaxonomyValue", foreign_keys=[ownership_type_id])
    status_value: Mapped[Optional["TaxonomyValue"]] = relationship(
        "TaxonomyValue", foreign_keys=[status_id])
    wholly_owned_region: Mapped[Optional["Region"]] = relationship(
        "Region", foreign_keys=[wholly_owned_region_id])
    regulatory_categories: Mapped[List["TaxonomyValue"]] = relationship(
        "TaxonomyValue", secondary=model_regulatory_categories)
    # Regional metadata links
    model_regions: Mapped[List["ModelRegion"]] = relationship(
        "ModelRegion", back_populates="model", cascade="all, delete-orphan"
    )

    @property
    def regions(self):
        """Compute regions list from model_regions for API responses."""
        return [
            {
                'region_id': mr.region.region_id,
                'region_code': mr.region.code,
                'region_name': mr.region.name
            }
            for mr in self.model_regions
        ]

    # Model versions
    versions: Mapped[List["ModelVersion"]] = relationship(
        "ModelVersion", back_populates="model", cascade="all, delete-orphan", order_by="desc(ModelVersion.created_at)"
    )
    # Model delegates
    delegates: Mapped[List["ModelDelegate"]] = relationship(
        "ModelDelegate", back_populates="model", cascade="all, delete-orphan"
    )
    # Model submission comments
    submission_comments: Mapped[List["ModelSubmissionComment"]] = relationship(
        "ModelSubmissionComment", back_populates="model", cascade="all, delete-orphan", order_by="ModelSubmissionComment.created_at"
    )

    # Model hierarchy relationships
    child_relationships: Mapped[List["ModelHierarchy"]] = relationship(
        "ModelHierarchy", foreign_keys="ModelHierarchy.parent_model_id",
        back_populates="parent_model", cascade="all, delete-orphan"
    )
    parent_relationships: Mapped[List["ModelHierarchy"]] = relationship(
        "ModelHierarchy", foreign_keys="ModelHierarchy.child_model_id",
        back_populates="child_model", cascade="all, delete-orphan"
    )

    # Model dependency relationships
    outbound_dependencies: Mapped[List["ModelFeedDependency"]] = relationship(
        "ModelFeedDependency", foreign_keys="ModelFeedDependency.feeder_model_id",
        back_populates="feeder_model", cascade="all, delete-orphan"
    )
    inbound_dependencies: Mapped[List["ModelFeedDependency"]] = relationship(
        "ModelFeedDependency", foreign_keys="ModelFeedDependency.consumer_model_id",
        back_populates="consumer_model", cascade="all, delete-orphan"
    )

    # Supporting applications from MAP
    applications: Mapped[List["ModelApplication"]] = relationship(
        "ModelApplication", back_populates="model", cascade="all, delete-orphan"
    )
