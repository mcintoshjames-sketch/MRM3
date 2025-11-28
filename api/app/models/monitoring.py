"""Monitoring Plans and Teams - ongoing performance monitoring."""
import enum
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import String, Integer, Text, Boolean, ForeignKey, Table, Column, DateTime, Date, Enum as SQLEnum, JSON, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class MonitoringFrequency(str, enum.Enum):
    """Monitoring plan frequency."""
    MONTHLY = "Monthly"
    QUARTERLY = "Quarterly"
    SEMI_ANNUAL = "Semi-Annual"
    ANNUAL = "Annual"


# Association table for monitoring team members (many-to-many)
monitoring_team_members = Table(
    "monitoring_team_members",
    Base.metadata,
    Column("team_id", Integer, ForeignKey(
        "monitoring_teams.team_id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey(
        "users.user_id", ondelete="CASCADE"), primary_key=True),
)


# Association table for monitoring plan models (many-to-many scope)
monitoring_plan_models = Table(
    "monitoring_plan_models",
    Base.metadata,
    Column("plan_id", Integer, ForeignKey(
        "monitoring_plans.plan_id", ondelete="CASCADE"), primary_key=True),
    Column("model_id", Integer, ForeignKey(
        "models.model_id", ondelete="CASCADE"), primary_key=True),
)


class MonitoringTeam(Base):
    """Monitoring team for ongoing performance monitoring."""
    __tablename__ = "monitoring_teams"

    team_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    members: Mapped[List["User"]] = relationship(
        "User", secondary=monitoring_team_members, backref="monitoring_teams"
    )
    plans: Mapped[List["MonitoringPlan"]] = relationship(
        "MonitoringPlan", back_populates="team", cascade="all, delete-orphan"
    )


class MonitoringPlan(Base):
    """Monitoring plan defining scope, frequency, and metrics for ongoing monitoring."""
    __tablename__ = "monitoring_plans"

    plan_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Frequency configuration
    frequency: Mapped[MonitoringFrequency] = mapped_column(
        String(50), nullable=False, default=MonitoringFrequency.QUARTERLY
    )

    # Team assignment
    monitoring_team_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("monitoring_teams.team_id", ondelete="SET NULL"), nullable=True
    )

    # Data provider (user responsible for providing monitoring data)
    data_provider_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )

    # Reporting lead days - days between submission and report due date
    reporting_lead_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30,
        comment="Days between data submission due date and report due date"
    )

    # Calculated due dates (updated when cycle completes or plan is created)
    next_submission_due_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True,
        comment="Next due date for data submission"
    )
    next_report_due_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True,
        comment="Next due date for monitoring report"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    team: Mapped[Optional["MonitoringTeam"]] = relationship(
        "MonitoringTeam", back_populates="plans"
    )
    data_provider: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[data_provider_user_id]
    )
    models: Mapped[List["Model"]] = relationship(
        "Model", secondary=monitoring_plan_models, backref="monitoring_plans"
    )
    metrics: Mapped[List["MonitoringPlanMetric"]] = relationship(
        "MonitoringPlanMetric", back_populates="plan", cascade="all, delete-orphan"
    )
    cycles: Mapped[List["MonitoringCycle"]] = relationship(
        "MonitoringCycle", back_populates="plan", cascade="all, delete-orphan",
        order_by="desc(MonitoringCycle.period_end_date)"
    )
    versions: Mapped[List["MonitoringPlanVersion"]] = relationship(
        "MonitoringPlanVersion", back_populates="plan",
        cascade="all, delete-orphan",
        order_by="desc(MonitoringPlanVersion.version_number)"
    )


class MonitoringPlanMetric(Base):
    """Links monitoring plans to KPM metrics with threshold configuration."""
    __tablename__ = "monitoring_plan_metrics"

    metric_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("monitoring_plans.plan_id", ondelete="CASCADE"), nullable=False, index=True
    )
    kpm_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("kpms.kpm_id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Threshold configuration (for quantitative metrics)
    # Yellow thresholds (warning zone)
    yellow_min: Mapped[Optional[float]] = mapped_column(
        nullable=True, comment="Minimum value for yellow/warning status"
    )
    yellow_max: Mapped[Optional[float]] = mapped_column(
        nullable=True, comment="Maximum value for yellow/warning status"
    )

    # Red thresholds (critical zone)
    red_min: Mapped[Optional[float]] = mapped_column(
        nullable=True, comment="Minimum value for red/critical status"
    )
    red_max: Mapped[Optional[float]] = mapped_column(
        nullable=True, comment="Maximum value for red/critical status"
    )

    # Qualitative guidance (for non-numeric metrics)
    qualitative_guidance: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Qualitative guidance for interpreting this metric in the plan context"
    )

    # Sort order for display
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Active status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    plan: Mapped["MonitoringPlan"] = relationship(
        "MonitoringPlan", back_populates="metrics"
    )
    kpm: Mapped["Kpm"] = relationship("Kpm")
    results: Mapped[List["MonitoringResult"]] = relationship(
        "MonitoringResult", back_populates="plan_metric", cascade="all, delete-orphan"
    )


class MonitoringPlanVersion(Base):
    """Version snapshot of a monitoring plan's metric configuration."""
    __tablename__ = "monitoring_plan_versions"

    version_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("monitoring_plans.plan_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    published_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint('plan_id', 'version_number', name='uq_monitoring_plan_version'),
    )

    # Relationships
    plan: Mapped["MonitoringPlan"] = relationship(
        "MonitoringPlan", back_populates="versions"
    )
    published_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[published_by_user_id]
    )
    metric_snapshots: Mapped[List["MonitoringPlanMetricSnapshot"]] = relationship(
        "MonitoringPlanMetricSnapshot", back_populates="version",
        cascade="all, delete-orphan"
    )
    cycles: Mapped[List["MonitoringCycle"]] = relationship(
        "MonitoringCycle", back_populates="plan_version"
    )


class MonitoringPlanMetricSnapshot(Base):
    """Snapshot of a metric's configuration at a specific plan version."""
    __tablename__ = "monitoring_plan_metric_snapshots"

    snapshot_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("monitoring_plan_versions.version_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    original_metric_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    kpm_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("kpms.kpm_id", ondelete="CASCADE"), nullable=False
    )

    # Threshold snapshot
    yellow_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    yellow_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    red_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    red_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    qualitative_guidance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # KPM metadata snapshot
    kpm_name: Mapped[str] = mapped_column(String(200), nullable=False)
    kpm_category_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    evaluation_type: Mapped[str] = mapped_column(String(50), nullable=False, default="Quantitative")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint('version_id', 'kpm_id', name='uq_version_kpm'),
    )

    # Relationships
    version: Mapped["MonitoringPlanVersion"] = relationship(
        "MonitoringPlanVersion", back_populates="metric_snapshots"
    )
    kpm: Mapped["Kpm"] = relationship("Kpm")


class MonitoringCycleStatus(str, enum.Enum):
    """Monitoring cycle status workflow states."""
    PENDING = "PENDING"
    DATA_COLLECTION = "DATA_COLLECTION"
    UNDER_REVIEW = "UNDER_REVIEW"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    CANCELLED = "CANCELLED"


class MonitoringCycle(Base):
    """Monitoring cycle representing one monitoring period for a plan."""
    __tablename__ = "monitoring_cycles"

    cycle_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("monitoring_plans.plan_id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Period definition
    period_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    submission_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    report_due_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Workflow status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=MonitoringCycleStatus.PENDING.value
    )

    # Assignment (optional override of plan's data_provider)
    assigned_to_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )

    # Submission tracking
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    submitted_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )

    # Completion tracking
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Version tracking (locked at DATA_COLLECTION start)
    plan_version_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("monitoring_plan_versions.version_id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Version of monitoring plan this cycle is bound to (locked at DATA_COLLECTION start)"
    )
    version_locked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True,
        comment="When the version was locked for this cycle"
    )
    version_locked_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    plan: Mapped["MonitoringPlan"] = relationship(
        "MonitoringPlan", back_populates="cycles"
    )
    plan_version: Mapped[Optional["MonitoringPlanVersion"]] = relationship(
        "MonitoringPlanVersion", back_populates="cycles"
    )
    assigned_to: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assigned_to_user_id]
    )
    submitted_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[submitted_by_user_id]
    )
    completed_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[completed_by_user_id]
    )
    version_locked_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[version_locked_by_user_id]
    )
    results: Mapped[List["MonitoringResult"]] = relationship(
        "MonitoringResult", back_populates="cycle", cascade="all, delete-orphan"
    )
    approvals: Mapped[List["MonitoringCycleApproval"]] = relationship(
        "MonitoringCycleApproval", back_populates="cycle", cascade="all, delete-orphan"
    )


class MonitoringCycleApproval(Base):
    """Approval record for a monitoring cycle."""
    __tablename__ = "monitoring_cycle_approvals"

    approval_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("monitoring_cycles.cycle_id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Approver info
    approver_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )

    # Approval type: 'Global' or 'Regional'
    approval_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="Global"
    )

    # Region for regional approvals (NULL for Global)
    region_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("regions.region_id", ondelete="SET NULL"), nullable=True
    )

    # Historical context: which region did approver represent at approval time
    represented_region_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("regions.region_id", ondelete="SET NULL"), nullable=True
    )

    # Approval status
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    approval_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Pending"
    )  # Pending, Approved, Rejected
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Admin proxy approval evidence (when Admin approves on behalf of approver)
    approval_evidence: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Evidence description for Admin proxy approvals (meeting minutes, email, etc.)"
    )

    # Voiding (Admin can void approval requirements)
    voided_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    void_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    cycle: Mapped["MonitoringCycle"] = relationship(
        "MonitoringCycle", back_populates="approvals"
    )
    approver: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[approver_id]
    )
    region: Mapped[Optional["Region"]] = relationship(
        "Region", foreign_keys=[region_id]
    )
    represented_region: Mapped[Optional["Region"]] = relationship(
        "Region", foreign_keys=[represented_region_id]
    )
    voided_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[voided_by_id]
    )


class MonitoringResult(Base):
    """Individual metric result for a monitoring cycle."""
    __tablename__ = "monitoring_results"

    result_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("monitoring_cycles.cycle_id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_metric_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("monitoring_plan_metrics.metric_id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Optional model-specific result (when plan covers multiple models)
    model_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("models.model_id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Quantitative data
    numeric_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Qualitative/Outcome data (taxonomy value for R/Y/G)
    outcome_value_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_values.value_id", ondelete="SET NULL"), nullable=True
    )

    # Calculated outcome (GREEN, YELLOW, RED, N/A)
    calculated_outcome: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, index=True
    )

    # Supporting narrative (required for qualitative, optional for quantitative)
    narrative: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Additional structured data (JSON for flexibility)
    supporting_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Audit fields
    entered_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )
    entered_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    cycle: Mapped["MonitoringCycle"] = relationship(
        "MonitoringCycle", back_populates="results"
    )
    plan_metric: Mapped["MonitoringPlanMetric"] = relationship(
        "MonitoringPlanMetric", back_populates="results"
    )
    model: Mapped[Optional["Model"]] = relationship("Model")
    outcome_value: Mapped[Optional["TaxonomyValue"]] = relationship("TaxonomyValue")
    entered_by: Mapped["User"] = relationship("User", foreign_keys=[entered_by_user_id])
