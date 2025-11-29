"""
FRY 14 Reporting Schema Models.

Represents the Federal Reserve Board FR Y-14 reporting structure:
- Reports (e.g., FR Y-14A, FR Y-14Q, FR Y-14M)
- Schedules within each report
- Metric Groups within each schedule
- Line Items within each metric group
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.core.time import utc_now


class FryReport(Base):
    """FRY Report (e.g., FR Y-14A, FR Y-14Q, FR Y-14M)."""
    __tablename__ = "fry_reports"

    report_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    schedules: Mapped[List["FrySchedule"]] = relationship(
        "FrySchedule", back_populates="report", cascade="all, delete-orphan"
    )


class FrySchedule(Base):
    """FRY Schedule within a report."""
    __tablename__ = "fry_schedules"

    schedule_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("fry_reports.report_id", ondelete="CASCADE"), nullable=False, index=True
    )
    schedule_code: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    report: Mapped["FryReport"] = relationship("FryReport", back_populates="schedules")
    metric_groups: Mapped[List["FryMetricGroup"]] = relationship(
        "FryMetricGroup", back_populates="schedule", cascade="all, delete-orphan"
    )


class FryMetricGroup(Base):
    """FRY Metric Group within a schedule."""
    __tablename__ = "fry_metric_groups"

    metric_group_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schedule_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("fry_schedules.schedule_id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric_group_name: Mapped[str] = mapped_column(String(200), nullable=False)
    model_driven: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    schedule: Mapped["FrySchedule"] = relationship("FrySchedule", back_populates="metric_groups")
    line_items: Mapped[List["FryLineItem"]] = relationship(
        "FryLineItem", back_populates="metric_group", cascade="all, delete-orphan"
    )


class FryLineItem(Base):
    """FRY Line Item within a metric group (model-estimated line items)."""
    __tablename__ = "fry_line_items"

    line_item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric_group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("fry_metric_groups.metric_group_id", ondelete="CASCADE"), nullable=False, index=True
    )
    line_item_text: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    # Relationships
    metric_group: Mapped["FryMetricGroup"] = relationship("FryMetricGroup", back_populates="line_items")
