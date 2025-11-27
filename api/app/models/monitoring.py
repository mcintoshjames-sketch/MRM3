"""Monitoring Plans and Teams - ongoing performance monitoring."""
import enum
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import String, Integer, Text, Boolean, ForeignKey, Table, Column, DateTime, Date, Enum as SQLEnum
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
