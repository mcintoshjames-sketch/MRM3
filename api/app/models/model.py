"""Model model - minimal schema."""
import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Table, Column, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now


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
    shared_owner_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True,
        comment="Optional co-owner for shared ownership scenarios")
    shared_developer_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True,
        comment="Optional co-developer for shared development scenarios")
    monitoring_manager_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True,
        comment="User responsible for ongoing model monitoring")
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
    methodology_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("methodologies.methodology_id", ondelete="SET NULL"), nullable=True)
    ownership_type_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=True)
    usage_frequency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False)
    status_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=True)
    wholly_owned_region_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("regions.region_id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Row-level approval workflow fields
    row_approval_status: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
        comment="Status of this record in the approval workflow: Draft, needs_revision, rejected, or NULL (approved)")
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

    # MRSA (Model Risk-Sensitive Application) classification
    is_mrsa: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True for Model Risk-Sensitive Applications (non-models requiring oversight)")
    mrsa_risk_level_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id", ondelete="SET NULL"), nullable=True,
        comment="MRSA risk classification (High-Risk or Low-Risk)")
    mrsa_risk_rationale: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Narrative explaining the MRSA risk level assignment")

    # Relationships
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])
    developer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[developer_id])
    shared_owner: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[shared_owner_id])
    shared_developer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[shared_developer_id])
    monitoring_manager: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[monitoring_manager_id])
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
    methodology: Mapped[Optional["Methodology"]] = relationship(
        "Methodology", foreign_keys=[methodology_id])
    ownership_type: Mapped[Optional["TaxonomyValue"]] = relationship(
        "TaxonomyValue", foreign_keys=[ownership_type_id])
    usage_frequency: Mapped["TaxonomyValue"] = relationship(
        "TaxonomyValue", foreign_keys=[usage_frequency_id])
    status_value: Mapped[Optional["TaxonomyValue"]] = relationship(
        "TaxonomyValue", foreign_keys=[status_id])
    wholly_owned_region: Mapped[Optional["Region"]] = relationship(
        "Region", foreign_keys=[wholly_owned_region_id])
    regulatory_categories: Mapped[List["TaxonomyValue"]] = relationship(
        "TaxonomyValue", secondary=model_regulatory_categories)
    # MRSA classification relationship
    mrsa_risk_level: Mapped[Optional["TaxonomyValue"]] = relationship(
        "TaxonomyValue", foreign_keys=[mrsa_risk_level_id])
    # IRP relationships (for MRSAs) - imported from irp.py
    irps: Mapped[List["IRP"]] = relationship(
        "IRP", secondary="mrsa_irp", back_populates="covered_mrsas")
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

    @property
    def is_aiml(self) -> Optional[bool]:
        """Compute AI/ML classification from methodology's category.

        Returns:
            True if methodology's category is flagged as AI/ML
            False if methodology's category is NOT flagged as AI/ML
            None if model has no methodology assigned (Undefined)
        """
        if self.methodology is None:
            return None
        if self.methodology.category is None:
            return None
        return self.methodology.category.is_aiml

    @property
    def business_line_name(self) -> Optional[str]:
        """Compute business line name from owner's LOB rolled up to LOB4 level.

        Returns:
            The owner's LOB name rolled up to LOB4 level, or the actual LOB
            name if the owner's LOB is at or above LOB4 level.
            None if the owner has no LOB assigned.
        """
        from app.core.lob_utils import get_user_lob_rollup_name
        return get_user_lob_rollup_name(self.owner)

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
    # Model name change history
    name_history: Mapped[List["ModelNameHistory"]] = relationship(
        "ModelNameHistory", back_populates="model", cascade="all, delete-orphan", order_by="ModelNameHistory.changed_at.desc()"
    )
    # Model approval status history
    approval_status_history: Mapped[List["ModelApprovalStatusHistory"]] = relationship(
        "ModelApprovalStatusHistory", back_populates="model", cascade="all, delete-orphan", order_by="ModelApprovalStatusHistory.changed_at.desc()"
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

    # Pending edits awaiting admin approval
    pending_edits: Mapped[List["ModelPendingEdit"]] = relationship(
        "ModelPendingEdit", back_populates="model", cascade="all, delete-orphan",
        order_by="desc(ModelPendingEdit.requested_at)"
    )

    # Recommendations (issues) identified during validation
    recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation", back_populates="model", cascade="all, delete-orphan",
        order_by="desc(Recommendation.created_at)"
    )

    # Risk assessments (global and regional)
    risk_assessments: Mapped[List["ModelRiskAssessment"]] = relationship(
        "ModelRiskAssessment", back_populates="model", cascade="all, delete-orphan"
    )

    # Model limitations
    limitations: Mapped[List["ModelLimitation"]] = relationship(
        "ModelLimitation", back_populates="model", cascade="all, delete-orphan",
        order_by="desc(ModelLimitation.created_at)"
    )
