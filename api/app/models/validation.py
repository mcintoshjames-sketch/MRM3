"""Validation workflow models."""
from __future__ import annotations

from datetime import datetime, date, timedelta
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Date, Boolean, Float, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.core.time import utc_now

if TYPE_CHECKING:
    from app.models.model import Model
    from app.models.overdue_comment import OverdueRevalidationComment
    from app.models.region import Region
    from app.models.scorecard import ValidationScorecardRating, ValidationScorecardResult


# Association class for validation request models with version tracking
class ValidationRequestModelVersion(Base):
    """Association object for validation request models with specific versions."""
    __tablename__ = "validation_request_models"

    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validation_requests.request_id", ondelete="CASCADE"), primary_key=True
    )
    model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), primary_key=True
    )
    version_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("model_versions.version_id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    request = relationship("ValidationRequest",
                           back_populates="model_versions_assoc")
    model = relationship("Model")
    version = relationship("ModelVersion")


# Backward compatibility: make table accessible for filtering
validation_request_models = ValidationRequestModelVersion.__table__

# Association table for validation request regions (many-to-many)
validation_request_regions = Table(
    "validation_request_regions",
    Base.metadata,
    Column("request_id", Integer, ForeignKey(
        "validation_requests.request_id", ondelete="CASCADE"), primary_key=True),
    Column("region_id", Integer, ForeignKey(
        "regions.region_id", ondelete="CASCADE"), primary_key=True),
)


class ValidationPolicy(Base):
    """Validation policy configuration by risk tier."""
    __tablename__ = "validation_policies"

    policy_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    risk_tier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False, unique=True
    )
    frequency_months: Mapped[int] = mapped_column(
        Integer, nullable=False, default=12)
    grace_period_months: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3,
        comment="Grace period in months after submission due date before item is considered overdue"
    )
    model_change_lead_time_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=90,
        comment="Lead time in days before model change implementation date to trigger interim validation"
    )
    # Performance monitoring plan review requirements
    monitoring_plan_review_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="If true, component 9b (Performance Monitoring Plan Review) requires Planned or comment"
    )
    monitoring_plan_review_description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    risk_tier = relationship("TaxonomyValue", foreign_keys=[risk_tier_id])


class ValidationWorkflowSLA(Base):
    """SLA configuration for validation workflow phases."""
    __tablename__ = "validation_workflow_slas"

    sla_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workflow_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="Validation")
    assignment_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10)
    begin_work_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5)
    # NOTE: complete_work_days AND model_change_lead_time_days were removed.
    # Work completion lead time is now calculated per-request based on the model's
    # risk tier policy (ValidationPolicy.model_change_lead_time_days)
    approval_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )


class ValidationRequest(Base):
    """Main validation request entity - workflow-based."""
    __tablename__ = "validation_requests"

    request_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_date: Mapped[date] = mapped_column(
        Date, nullable=False, default=date.today)
    requestor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    validation_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    priority_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    target_completion_date: Mapped[date] = mapped_column(Date, nullable=False)
    trigger_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_status_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )

    # Admin decline fields
    declined_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=True
    )
    decline_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    declined_at: Mapped[Optional[datetime]
                        ] = mapped_column(DateTime, nullable=True)

    # Revalidation Lifecycle Fields
    prior_validation_request_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("validation_requests.request_id", ondelete="SET NULL"),
        nullable=True,
        comment="Link to the previous validation that this revalidation follows"
    )
    prior_full_validation_request_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("validation_requests.request_id", ondelete="SET NULL"),
        nullable=True,
        comment="Link to the most recent INITIAL or COMPREHENSIVE validation"
    )
    submission_due_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Date by which model owner must submit documentation (locked at request creation)"
    )
    submission_received_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Date model owner actually submitted documentation"
    )

    # Submission metadata fields - captured when marking submission received
    confirmed_model_version_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("model_versions.version_id", ondelete="SET NULL"),
        nullable=True,
        comment="Confirmed model version at time of submission (may differ from originally associated version)"
    )
    model_documentation_version: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Version identifier for the model documentation submitted"
    )
    model_submission_version: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Version identifier for the model code/artifacts submitted"
    )
    model_documentation_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="External ID or reference for the model documentation (e.g., document management system ID)"
    )

    # Version source tracking (for ready-to-deploy surfacing)
    version_source: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        default="explicit",
        comment="How version was linked: 'explicit' (user selected) or 'inferred' (system auto-suggested)"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )
    completion_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when validation was completed (latest approval date)"
    )

    # Risk tier snapshot at validation approval
    validated_risk_tier_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("taxonomy_values.value_id", ondelete="SET NULL"),
        nullable=True,
        comment="Snapshot of model's risk tier at the moment of validation approval"
    )

    # Relationships
    # Association object for model-version tracking
    model_versions_assoc: Mapped[List["ValidationRequestModelVersion"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )
    # Backward compatibility: simple list of models
    models: Mapped[List["Model"]] = relationship(
        "Model", secondary="validation_request_models", viewonly=True
    )
    regions: Mapped[List["Region"]] = relationship(
        "Region", secondary=validation_request_regions
    )
    requestor = relationship("User", foreign_keys=[requestor_id])
    declined_by = relationship("User", foreign_keys=[declined_by_id])
    validation_type = relationship(
        "TaxonomyValue", foreign_keys=[validation_type_id])
    priority = relationship("TaxonomyValue", foreign_keys=[priority_id])
    current_status = relationship(
        "TaxonomyValue", foreign_keys=[current_status_id])
    confirmed_model_version = relationship(
        "ModelVersion", foreign_keys=[confirmed_model_version_id])
    validated_risk_tier = relationship(
        "TaxonomyValue", foreign_keys=[validated_risk_tier_id])

    # Self-referential relationship for revalidation chain
    prior_validation_request = relationship(
        "ValidationRequest",
        foreign_keys=[prior_validation_request_id],
        remote_side=[request_id]
    )
    prior_full_validation_request = relationship(
        "ValidationRequest",
        foreign_keys=[prior_full_validation_request_id],
        remote_side=[request_id]
    )

    # One-to-many relationships
    status_history: Mapped[List["ValidationStatusHistory"]] = relationship(
        back_populates="request", cascade="all, delete-orphan", order_by="desc(ValidationStatusHistory.changed_at)"
    )
    assignments: Mapped[List["ValidationAssignment"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )
    work_components: Mapped[List["ValidationWorkComponent"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )
    approvals: Mapped[List["ValidationApproval"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )

    # One-to-one relationship with outcome
    outcome: Mapped[Optional["ValidationOutcome"]] = relationship(
        back_populates="request", uselist=False, cascade="all, delete-orphan"
    )

    # One-to-one relationship with review outcome
    review_outcome: Mapped[Optional["ValidationReviewOutcome"]] = relationship(
        back_populates="request", uselist=False, cascade="all, delete-orphan"
    )

    # One-to-one relationship with validation plan
    validation_plan: Mapped[Optional["ValidationPlan"]] = relationship(
        back_populates="request", uselist=False, cascade="all, delete-orphan"
    )

    # One-to-many relationship with overdue comments
    overdue_comments: Mapped[List["OverdueRevalidationComment"]] = relationship(
        back_populates="validation_request", cascade="all, delete-orphan",
        order_by="desc(OverdueRevalidationComment.created_at)"
    )

    # Scorecard relationships (ratings and computed result)
    scorecard_ratings: Mapped[List["ValidationScorecardRating"]] = relationship(
        "ValidationScorecardRating",
        back_populates="request",
        cascade="all, delete-orphan"
    )
    scorecard_result: Mapped[Optional["ValidationScorecardResult"]] = relationship(
        "ValidationScorecardResult",
        back_populates="request",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # Computed properties for revalidation lifecycle
    @property
    def is_periodic_revalidation(self) -> bool:
        """Determine if this is a periodic revalidation based on validation type."""
        if not self.validation_type:
            return False
        return self.validation_type.code == "COMPREHENSIVE"

    def _calculate_submission_due_date(self) -> Optional[date]:
        """Calculate submission due date from prior validation + frequency."""
        if not self.is_periodic_revalidation or not self.prior_validation_request_id:
            return None

        # Get prior validation
        prior = self.prior_validation_request
        if not prior or prior.current_status.code != "APPROVED":
            return None

        # Find when prior was approved (use completion_date or updated_at as proxy)
        prior_completed = prior.completion_date.date() if prior.completion_date else prior.updated_at.date()

        # Get model to find risk tier
        if not self.model_versions_assoc or len(self.model_versions_assoc) == 0:
            return None
        model = self.model_versions_assoc[0].model

        # Get policy for this risk tier
        from sqlalchemy.orm import Session
        session = Session.object_session(self)
        if not session:
            return None

        policy = session.query(ValidationPolicy).filter(
            ValidationPolicy.risk_tier_id == model.risk_tier_id
        ).first()

        if not policy:
            return None

        # Calculate: prior_completed + frequency_months
        from dateutil.relativedelta import relativedelta
        return prior_completed + relativedelta(months=policy.frequency_months)

    def get_submission_due_date(self) -> Optional[date]:
        """
        Get submission due date.
        Uses stored value if available, otherwise calculates it.
        This method should be used when you need the value and want to ensure it's calculated.
        """
        # Return stored value if it exists (note: this is now a column, not a property)
        # The column is accessed via self.__dict__ to avoid infinite recursion
        stored_value = self.__dict__.get('submission_due_date')
        if stored_value is not None:
            return stored_value

        # Otherwise calculate it
        return self._calculate_submission_due_date()

    def _get_policy_for_request(self) -> Optional["ValidationPolicy"]:
        """Get the validation policy based on the model's risk tier."""
        if not self.model_versions_assoc or len(self.model_versions_assoc) == 0:
            return None
        model = self.model_versions_assoc[0].model
        if not model or not model.risk_tier_id:
            return None

        from sqlalchemy.orm import Session
        session = Session.object_session(self)
        if not session:
            return None

        return session.query(ValidationPolicy).filter(
            ValidationPolicy.risk_tier_id == model.risk_tier_id
        ).first()

    @property
    def applicable_lead_time_days(self) -> int:
        """
        Get the maximum completion lead time across all models in this request.

        For multi-model validation requests, uses the MAXIMUM lead time from all
        associated models' risk tier policies (most conservative approach for
        compliance). This ensures adequate time for the highest-risk model.

        This is the risk-tier-specific lead time that replaces the fixed global
        'complete_work_days' in ValidationWorkflowSLA. Higher risk tiers have
        longer lead times to allow for more thorough validation work.

        Returns:
            Maximum lead time in days from all models' validation policies.
            Defaults to 90 days if no policies are found.
        """
        if not self.model_versions_assoc or len(self.model_versions_assoc) == 0:
            return 90  # Default fallback

        from sqlalchemy.orm import Session
        session = Session.object_session(self)
        if not session:
            return 90  # Default fallback

        # Collect lead times from all models' policies
        lead_times = []
        for assoc in self.model_versions_assoc:
            model = assoc.model
            if model and model.risk_tier_id:
                policy = session.query(ValidationPolicy).filter(
                    ValidationPolicy.risk_tier_id == model.risk_tier_id
                ).first()
                if policy:
                    lead_times.append(policy.model_change_lead_time_days)

        # Return maximum (most conservative) or default
        return max(lead_times) if lead_times else 90

    @property
    def submission_grace_period_end(self) -> Optional[date]:
        """Calculate grace period end (submission_due + grace_period_months from policy)."""
        due_date = self.get_submission_due_date()
        if not due_date:
            return None

        from dateutil.relativedelta import relativedelta

        # Get grace period from policy (defaults to 3 months if no policy found)
        policy = self._get_policy_for_request()
        grace_months = policy.grace_period_months if policy else 3

        return due_date + relativedelta(months=grace_months)

    @property
    def model_validation_due_date(self) -> Optional[date]:
        """
        Model compliance due date (fixed based on policy).
        = Submission Due + grace_period_months + Lead Time
        Model is "overdue" if not validated by this date.
        """
        if not self.submission_grace_period_end:
            return None

        policy = self._get_policy_for_request()
        if not policy:
            return None

        from datetime import timedelta
        return self.submission_grace_period_end + timedelta(days=policy.model_change_lead_time_days)

    @property
    def validation_team_sla_due_date(self) -> Optional[date]:
        """
        Validation team SLA due date (based on actual submission).
        = Submission Received + Lead Time
        Measures team performance independent of submission timing.
        """
        if not self.submission_received_date:
            return None  # SLA doesn't start until submission received

        # Get model to find risk tier
        if not self.model_versions_assoc or len(self.model_versions_assoc) == 0:
            return None
        model = self.model_versions_assoc[0].model

        # Get policy for this risk tier
        from sqlalchemy.orm import Session
        session = Session.object_session(self)
        if not session:
            return None

        policy = session.query(ValidationPolicy).filter(
            ValidationPolicy.risk_tier_id == model.risk_tier_id
        ).first()

        if not policy:
            return None

        from datetime import timedelta
        return self.submission_received_date + timedelta(days=policy.model_change_lead_time_days)

    @property
    def submission_status(self) -> str:
        """Calculate current submission status."""
        if not self.is_periodic_revalidation:
            return "N/A"

        due_date = self.get_submission_due_date()
        if self.submission_received_date:
            if due_date and self.submission_received_date <= due_date:
                return "Submitted On Time"
            elif self.submission_grace_period_end and self.submission_received_date <= self.submission_grace_period_end:
                return "Submitted In Grace Period"
            else:
                return "Submitted Late"

        today = date.today()
        if not due_date:
            return "Unknown"
        if today < due_date:
            return "Not Yet Due"
        elif self.submission_grace_period_end and today <= self.submission_grace_period_end:
            return "Due (In Grace Period)"
        else:
            return "Overdue"

    @property
    def model_compliance_status(self) -> str:
        """
        Is the MODEL overdue for validation (regardless of team performance)?
        Based on model_validation_due_date.
        """
        if not self.is_periodic_revalidation:
            return "N/A"

        if self.current_status.code == "APPROVED":
            # Check if completed on time
            completed_date = self.updated_at.date()
            if not self.model_validation_due_date:
                return "Unknown"  # Can't determine if on time without a due date
            if completed_date <= self.model_validation_due_date:
                return "Validated On Time"
            else:
                return "Validated Late"

        today = date.today()
        if not self.model_validation_due_date:
            return "Unknown"

        due_date = self.get_submission_due_date()
        if due_date and today <= due_date:
            return "On Track"
        elif self.submission_grace_period_end and today <= self.submission_grace_period_end:
            return "In Grace Period"
        elif today <= self.model_validation_due_date:
            return "At Risk"
        else:
            return "Overdue"

    @property
    def validation_team_sla_status(self) -> str:
        """
        Is the validation TEAM behind on their SLA?
        Based on validation_team_sla_due_date (from submission received).

        IMPORTANT: Uses adjusted_validation_team_sla_due_date which excludes hold time.
        Team should not be penalized for periods when work was paused.
        """
        if not self.is_periodic_revalidation:
            return "N/A"

        if not self.submission_received_date:
            return "Awaiting Submission"

        # Use adjusted due date that accounts for hold time
        adjusted_due = self.adjusted_validation_team_sla_due_date

        if self.current_status.code == "APPROVED":
            # Check if completed within SLA (adjusted for hold time)
            completed_date = self.updated_at.date()
            if adjusted_due and completed_date <= adjusted_due:
                return "Completed Within SLA"
            else:
                return "Completed Past SLA"

        today = date.today()
        if not adjusted_due:
            return "Unknown"

        if today <= adjusted_due:
            return "In Progress (On Time)"
        else:
            return "In Progress (Past SLA)"

    @property
    def days_until_submission_due(self) -> Optional[int]:
        """Days until submission due (negative if past)."""
        due_date = self.get_submission_due_date()
        if not due_date:
            return None
        return (due_date - date.today()).days

    @property
    def days_until_model_validation_due(self) -> Optional[int]:
        """Days until model validation due (negative if overdue)."""
        if not self.model_validation_due_date:
            return None
        return (self.model_validation_due_date - date.today()).days

    @property
    def days_until_team_sla_due(self) -> Optional[int]:
        """
        Days until validation team SLA expires (negative if past).

        Uses adjusted due date that accounts for hold time.
        """
        adjusted_due = self.adjusted_validation_team_sla_due_date
        if not adjusted_due:
            return None
        return (adjusted_due - date.today()).days

    @property
    def total_hold_days(self) -> int:
        """
        Calculate total days this request has spent in ON_HOLD status.

        Computed from status history by summing durations of all ON_HOLD periods.
        Requires status_history to be eager-loaded for accuracy.
        """
        hold_days = 0
        hold_start = None

        # Sort by changed_at ascending to process chronologically
        sorted_history = sorted(self.status_history, key=lambda x: x.changed_at)

        for entry in sorted_history:
            if entry.new_status and entry.new_status.code == "ON_HOLD":
                # Started a hold period
                hold_start = entry.changed_at
            elif hold_start is not None:
                # Ended a hold period (transitioned away from ON_HOLD)
                delta = entry.changed_at - hold_start
                hold_days += delta.days
                hold_start = None

        # If currently on hold, add time from last hold start to now
        if hold_start is not None:
            delta = utc_now() - hold_start
            hold_days += delta.days

        return hold_days

    @property
    def previous_status_before_hold(self) -> Optional[str]:
        """
        Get the status code before the most recent ON_HOLD transition.

        Used for "Resume" functionality to return to the appropriate status.
        Returns None if not currently on hold or no history available.
        """
        if not self.current_status or self.current_status.code != "ON_HOLD":
            return None

        # Find the history entry that transitioned TO ON_HOLD (most recent)
        sorted_history = sorted(self.status_history, key=lambda x: x.changed_at, reverse=True)

        for entry in sorted_history:
            if entry.new_status and entry.new_status.code == "ON_HOLD":
                if entry.old_status:
                    return entry.old_status.code
                break

        return None

    @property
    def adjusted_validation_team_sla_due_date(self) -> Optional[date]:
        """
        Validation team SLA due date adjusted for hold time.

        Extends the deadline by the total number of days the request was on hold.
        This ensures the team isn't penalized for hold periods outside their control.
        """
        base_due = self.validation_team_sla_due_date
        if not base_due:
            return None

        return base_due + timedelta(days=self.total_hold_days)

    @property
    def scorecard_overall_rating(self) -> Optional[str]:
        """Get the overall scorecard rating from the computed result."""
        if self.scorecard_result:
            return self.scorecard_result.overall_rating
        return None

    @property
    def residual_risk(self) -> Optional[str]:
        """
        Compute the residual risk based on validated_risk_tier and scorecard_overall_rating.

        Uses the active ResidualRiskMapConfig to look up the mapping.
        Returns None if either input is missing or no mapping exists.
        """
        # Need both inputs to compute residual risk
        if not self.validated_risk_tier or not self.scorecard_overall_rating:
            return None

        # Get the risk tier label and normalize it to match residual risk map keys
        # Taxonomy labels: "High Inherent Risk", "Medium Inherent Risk", etc.
        # Map keys: "High", "Medium", "Low", "Very Low"
        risk_tier_label = self.validated_risk_tier.label
        tier_mapping = {
            "High Inherent Risk": "High",
            "Medium Inherent Risk": "Medium",
            "Low Inherent Risk": "Low",
            "Very Low Inherent Risk": "Very Low",
            # Also support direct labels in case taxonomy is updated
            "High": "High",
            "Medium": "Medium",
            "Low": "Low",
            "Very Low": "Very Low",
        }
        normalized_tier = tier_mapping.get(risk_tier_label)
        if not normalized_tier:
            return None

        # Get the scorecard outcome (e.g., "Green", "Yellow", "Red")
        scorecard_outcome = self.scorecard_overall_rating

        # Look up residual risk from the active configuration
        from sqlalchemy.orm import Session
        session = Session.object_session(self)
        if not session:
            return None

        from app.models.residual_risk_map import ResidualRiskMapConfig
        config = session.query(ResidualRiskMapConfig).filter(
            ResidualRiskMapConfig.is_active == True
        ).first()

        if not config or not config.matrix_config:
            return None

        matrix = config.matrix_config.get("matrix", {})

        # Look up the residual risk: matrix[risk_tier][scorecard_outcome]
        tier_row = matrix.get(normalized_tier)
        if not tier_row:
            return None

        return tier_row.get(scorecard_outcome)


class ValidationStatusHistory(Base):
    """Audit trail for validation status changes."""
    __tablename__ = "validation_status_history"

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validation_requests.request_id", ondelete="CASCADE"), nullable=False
    )
    old_status_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=True
    )
    new_status_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    changed_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    additional_context: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="JSON storing action-specific details (e.g., revision snapshots for send-back)"
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )

    # Relationships
    request = relationship("ValidationRequest",
                           back_populates="status_history")
    old_status = relationship("TaxonomyValue", foreign_keys=[old_status_id])
    new_status = relationship("TaxonomyValue", foreign_keys=[new_status_id])
    changed_by = relationship("User", foreign_keys=[changed_by_id])


class ValidationAssignment(Base):
    """Validator assignment to a validation request."""
    __tablename__ = "validation_assignments"

    assignment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validation_requests.request_id", ondelete="CASCADE"), nullable=False
    )
    validator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    is_reviewer: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    assignment_date: Mapped[date] = mapped_column(
        Date, nullable=False, default=date.today)
    estimated_hours: Mapped[Optional[float]
                            ] = mapped_column(Float, nullable=True)
    actual_hours: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, default=0.0)
    independence_attestation: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    # Reviewer sign-off fields
    reviewer_signed_off: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)
    reviewer_signed_off_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)
    reviewer_sign_off_comments: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )

    # Relationships
    request = relationship("ValidationRequest", back_populates="assignments")
    validator = relationship("User", foreign_keys=[validator_id])


class ValidationWorkComponent(Base):
    """Individual work component tracking for a validation."""
    __tablename__ = "validation_work_components"

    component_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validation_requests.request_id", ondelete="CASCADE"), nullable=False
    )
    component_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    status_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    request = relationship("ValidationRequest",
                           back_populates="work_components")
    component_type = relationship(
        "TaxonomyValue", foreign_keys=[component_type_id])
    status = relationship("TaxonomyValue", foreign_keys=[status_id])


class ValidationOutcome(Base):
    """Validation outcome - only created after work is complete."""
    __tablename__ = "validation_outcomes"

    outcome_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validation_requests.request_id", ondelete="CASCADE"), nullable=False, unique=True
    )
    overall_rating_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id"), nullable=False
    )
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiration_date: Mapped[Optional[date]
                            ] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    request = relationship("ValidationRequest", back_populates="outcome")
    overall_rating = relationship(
        "TaxonomyValue", foreign_keys=[overall_rating_id])


class ValidationReviewOutcome(Base):
    """Review outcome - created by reviewer when reviewing validation outcome."""
    __tablename__ = "validation_review_outcomes"

    review_outcome_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validation_requests.request_id", ondelete="CASCADE"), nullable=False, unique=True
    )
    reviewer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    decision: Mapped[str] = mapped_column(
        String(50), nullable=False)  # 'AGREE' or 'SEND_BACK'
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agrees_with_rating: Mapped[Optional[bool]
                               ] = mapped_column(Boolean, nullable=True)
    review_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    request = relationship("ValidationRequest",
                           back_populates="review_outcome")
    reviewer = relationship("User", foreign_keys=[reviewer_id])


class ValidationApproval(Base):
    """Approval record for a validation request."""
    __tablename__ = "validation_approvals"

    approval_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validation_requests.request_id", ondelete="CASCADE"), nullable=False
    )
    approver_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=True
    )
    # Validator, Validation Head, Model Owner, Risk Officer
    approver_role: Mapped[str] = mapped_column(String(100), nullable=False)

    # Approval type and region tracking
    approval_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="Global"
    )  # 'Global' or 'Regional'
    region_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("regions.region_id"), nullable=True
    )  # Required if approval_type='Regional', NULL for Global

    # Historical context: What role did the approver represent at approval time?
    # This preserves history even if the user's role changes later
    represented_region_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("regions.region_id", ondelete="SET NULL"), nullable=True, index=True,
        comment="Region the approver was representing at approval time (NULL for Global Approver)"
    )

    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True)
    approval_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Pending")  # Pending, Approved, Rejected
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at: Mapped[Optional[datetime]
                        ] = mapped_column(DateTime, nullable=True)

    # Admin unlink fields
    unlinked_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=True
    )
    unlink_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unlinked_at: Mapped[Optional[datetime]
                        ] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )

    # Conditional model use approval fields
    approver_role_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("approver_roles.role_id", ondelete="SET NULL"), nullable=True, index=True,
        comment="FK to approver_roles (for conditional approvals); NULL for traditional approvals"
    )
    approval_evidence: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Description of approval evidence (meeting minutes, email, etc.)"
    )

    # Voiding fields (Admin can void approval requirements)
    voided_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    void_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Reason why this approval requirement was voided by Admin"
    )
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    request = relationship("ValidationRequest", back_populates="approvals")
    approver = relationship("User", foreign_keys=[approver_id])
    unlinked_by = relationship("User", foreign_keys=[unlinked_by_id])
    voided_by = relationship("User", foreign_keys=[voided_by_id])
    region = relationship("Region", foreign_keys=[region_id])  # Region for regional approvals
    represented_region = relationship("Region", foreign_keys=[represented_region_id])  # Historical role context
    approver_role_ref = relationship("ApproverRole", foreign_keys=[approver_role_id])  # Conditional approval role


class ValidationComponentDefinition(Base):
    """Master list of validation components (sections/subsections from bank standard)."""
    __tablename__ = "validation_component_definitions"

    component_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_number: Mapped[str] = mapped_column(String(10), nullable=False)
    section_title: Mapped[str] = mapped_column(String(200), nullable=False)
    component_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True,
                                                  comment="Stable identifier like '1.1', '3.4'")
    component_title: Mapped[str] = mapped_column(String(200), nullable=False)
    is_test_or_analysis: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False,
                                                        comment="True if test/analysis, False if report section")

    # Figure 3 matrix: expectation per risk tier (Required, IfApplicable, NotExpected)
    expectation_high: Mapped[str] = mapped_column(String(20), nullable=False, default="Required")
    expectation_medium: Mapped[str] = mapped_column(String(20), nullable=False, default="Required")
    expectation_low: Mapped[str] = mapped_column(String(20), nullable=False, default="Required")
    expectation_very_low: Mapped[str] = mapped_column(String(20), nullable=False, default="Required")

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    plan_components: Mapped[List["ValidationPlanComponent"]] = relationship(
        back_populates="component_definition", cascade="all, delete-orphan"
    )


class ValidationPlan(Base):
    """Validation plan header - linked to a validation request."""
    __tablename__ = "validation_plans"

    plan_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validation_requests.request_id", ondelete="CASCADE"), nullable=False, unique=True
    )
    overall_scope_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    material_deviation_from_standard: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    overall_deviation_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Configuration versioning (grandfathering support)
    config_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("component_definition_configurations.config_id", ondelete="SET NULL"), nullable=True,
        comment="Configuration version this plan is linked to (locked when plan submitted for review)"
    )
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True,
                                                            comment="When plan was locked (moved to Review/Pending Approval)")
    locked_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True,
        comment="User who triggered the lock (via status transition)"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    request = relationship("ValidationRequest", back_populates="validation_plan")
    components: Mapped[List["ValidationPlanComponent"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )
    configuration = relationship("ComponentDefinitionConfiguration", back_populates="validation_plans")
    locked_by = relationship("User", foreign_keys=[locked_by_user_id])


class ValidationPlanComponent(Base):
    """Per-component entry in a validation plan."""
    __tablename__ = "validation_plan_components"

    plan_component_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validation_plans.plan_id", ondelete="CASCADE"), nullable=False
    )
    component_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validation_component_definitions.component_id"), nullable=False
    )

    # Copied from master definition at plan creation (for this model's tier)
    default_expectation: Mapped[str] = mapped_column(String(20), nullable=False,
                                                       comment="Required, IfApplicable, or NotExpected")
    # Validator's choice
    planned_treatment: Mapped[str] = mapped_column(String(20), nullable=False, default="Planned",
                                                     comment="Planned, NotPlanned, or NotApplicable")
    # Computed: true when planned_treatment conflicts with default_expectation
    is_deviation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Required when is_deviation=true, optional otherwise
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    additional_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Component 9b: Performance Monitoring Plan Review
    monitoring_plan_version_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("monitoring_plan_versions.version_id", ondelete="SET NULL"), nullable=True,
        comment="For component 9b: which monitoring plan version was reviewed"
    )
    monitoring_review_notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="For component 9b: notes about the monitoring plan review"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    plan = relationship("ValidationPlan", back_populates="components")
    component_definition = relationship("ValidationComponentDefinition", back_populates="plan_components")
    monitoring_plan_version = relationship("MonitoringPlanVersion")


class ComponentDefinitionConfiguration(Base):
    """
    Configuration version tracking for component definitions.
    Each version represents a snapshot of validation standards at a point in time.
    Enables grandfathering: locked plans reference the config that existed when they were submitted.
    """
    __tablename__ = "component_definition_configurations"

    config_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_name: Mapped[str] = mapped_column(String(200), nullable=False,
                                               comment="e.g., '2025-11-22 Initial Configuration', 'Q2 2026 SR 11-7 Update'")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True,
                                                         comment="Details about this configuration version")
    effective_date: Mapped[date] = mapped_column(Date, nullable=False,
                                                   comment="When this configuration took effect")
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True,
                                              comment="Only one configuration is active at a time")

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    config_items: Mapped[List["ComponentDefinitionConfigItem"]] = relationship(
        back_populates="configuration", cascade="all, delete-orphan"
    )
    validation_plans: Mapped[List["ValidationPlan"]] = relationship(
        back_populates="configuration"
    )


class ComponentDefinitionConfigItem(Base):
    """
    Snapshot of a specific component's expectations at a given configuration version.
    Preserves historical standards for compliance auditing.
    """
    __tablename__ = "component_definition_config_items"

    config_item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("component_definition_configurations.config_id", ondelete="CASCADE"), nullable=False
    )
    component_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validation_component_definitions.component_id"), nullable=False
    )

    # Snapshot of expectations (Figure 3 matrix values at this version)
    expectation_high: Mapped[str] = mapped_column(String(20), nullable=False)
    expectation_medium: Mapped[str] = mapped_column(String(20), nullable=False)
    expectation_low: Mapped[str] = mapped_column(String(20), nullable=False)
    expectation_very_low: Mapped[str] = mapped_column(String(20), nullable=False)

    # Metadata snapshot (preserves component info in case it changes)
    section_number: Mapped[str] = mapped_column(String(10), nullable=False)
    section_title: Mapped[str] = mapped_column(String(200), nullable=False)
    component_code: Mapped[str] = mapped_column(String(20), nullable=False)
    component_title: Mapped[str] = mapped_column(String(200), nullable=False)
    is_test_or_analysis: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    configuration = relationship("ComponentDefinitionConfiguration", back_populates="config_items")
    component_definition = relationship("ValidationComponentDefinition")


class ValidationFinding(Base):
    """
    Findings identified during a validation.
    Findings track specific issues discovered during validation work and must be
    resolved before transitioning to certain workflow states.
    """
    __tablename__ = "validation_findings"

    finding_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("validation_requests.request_id", ondelete="CASCADE"), nullable=False
    )
    finding_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Category of finding: DATA_QUALITY, METHODOLOGY, IMPLEMENTATION, etc."
    )
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="Severity level: HIGH, MEDIUM, LOW"
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="OPEN",
        comment="Finding status: OPEN or RESOLVED"
    )
    identified_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=True
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    request = relationship("ValidationRequest", backref="findings")
    identified_by = relationship("User", foreign_keys=[identified_by_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])
