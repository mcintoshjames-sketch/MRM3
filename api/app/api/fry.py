"""
FRY 14 Reporting API endpoints.

Provides CRUD operations for managing FRY 14 reporting structure.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.core.roles import is_admin
from app.models.fry import FryReport, FrySchedule, FryMetricGroup, FryLineItem
from app.schemas.fry import (
    FryReportResponse,
    FryReportCreate,
    FryReportUpdate,
    FryReportWithSchedules,
    FryScheduleResponse,
    FryScheduleCreate,
    FryScheduleUpdate,
    FryScheduleWithMetricGroups,
    FryMetricGroupResponse,
    FryMetricGroupCreate,
    FryMetricGroupUpdate,
    FryMetricGroupWithLineItems,
    FryLineItemResponse,
    FryLineItemCreate,
    FryLineItemUpdate,
)

router = APIRouter(prefix="/fry", tags=["FRY 14 Reporting"])


# ============================================================================
# FRY Reports
# ============================================================================

@router.get("/reports", response_model=List[FryReportResponse])
def list_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all FRY reports."""
    reports = db.query(FryReport).order_by(FryReport.report_code).all()
    return reports


@router.get("/reports/{report_id}", response_model=FryReportWithSchedules)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific FRY report with all schedules, metric groups, and line items."""
    report = db.query(FryReport).options(
        joinedload(FryReport.schedules).joinedload(FrySchedule.metric_groups).joinedload(FryMetricGroup.line_items)
    ).filter(FryReport.report_id == report_id).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FRY report with ID {report_id} not found"
        )

    return report


@router.post("/reports", response_model=FryReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    report_data: FryReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new FRY report (Admin only)."""
    # Check admin role
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create FRY reports"
        )

    # Check if report code already exists
    existing = db.query(FryReport).filter(FryReport.report_code == report_data.report_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"FRY report with code '{report_data.report_code}' already exists"
        )

    report = FryReport(**report_data.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.patch("/reports/{report_id}", response_model=FryReportResponse)
def update_report(
    report_id: int,
    report_data: FryReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a FRY report (Admin only)."""
    report = db.query(FryReport).filter(FryReport.report_id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FRY report with ID {report_id} not found"
        )

    # Update fields
    for field, value in report_data.model_dump(exclude_unset=True).items():
        setattr(report, field, value)

    db.commit()
    db.refresh(report)
    return report


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a FRY report (Admin only). Cascades to all schedules, metric groups, and line items."""
    report = db.query(FryReport).filter(FryReport.report_id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FRY report with ID {report_id} not found"
        )

    db.delete(report)
    db.commit()
    return None


# ============================================================================
# FRY Schedules
# ============================================================================

@router.get("/reports/{report_id}/schedules", response_model=List[FryScheduleResponse])
def list_schedules(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all schedules for a specific FRY report."""
    # Verify report exists
    report = db.query(FryReport).filter(FryReport.report_id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FRY report with ID {report_id} not found"
        )

    schedules = db.query(FrySchedule).filter(
        FrySchedule.report_id == report_id
    ).order_by(FrySchedule.schedule_code).all()
    return schedules


@router.get("/schedules/{schedule_id}", response_model=FryScheduleWithMetricGroups)
def get_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific FRY schedule with all metric groups and line items."""
    schedule = db.query(FrySchedule).options(
        joinedload(FrySchedule.metric_groups).joinedload(FryMetricGroup.line_items)
    ).filter(FrySchedule.schedule_id == schedule_id).first()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FRY schedule with ID {schedule_id} not found"
        )

    return schedule


@router.post("/reports/{report_id}/schedules", response_model=FryScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(
    report_id: int,
    schedule_data: FryScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new FRY schedule (Admin only)."""
    # Verify report exists
    report = db.query(FryReport).filter(FryReport.report_id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FRY report with ID {report_id} not found"
        )

    schedule = FrySchedule(report_id=report_id, **schedule_data.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.patch("/schedules/{schedule_id}", response_model=FryScheduleResponse)
def update_schedule(
    schedule_id: int,
    schedule_data: FryScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a FRY schedule (Admin only)."""
    schedule = db.query(FrySchedule).filter(FrySchedule.schedule_id == schedule_id).first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FRY schedule with ID {schedule_id} not found"
        )

    for field, value in schedule_data.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)

    db.commit()
    db.refresh(schedule)
    return schedule


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a FRY schedule (Admin only). Cascades to metric groups and line items."""
    schedule = db.query(FrySchedule).filter(FrySchedule.schedule_id == schedule_id).first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FRY schedule with ID {schedule_id} not found"
        )

    db.delete(schedule)
    db.commit()
    return None


# ============================================================================
# FRY Metric Groups
# ============================================================================

@router.get("/schedules/{schedule_id}/metric-groups", response_model=List[FryMetricGroupResponse])
def list_metric_groups(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all metric groups for a specific FRY schedule."""
    # Verify schedule exists
    schedule = db.query(FrySchedule).filter(FrySchedule.schedule_id == schedule_id).first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FRY schedule with ID {schedule_id} not found"
        )

    metric_groups = db.query(FryMetricGroup).filter(
        FryMetricGroup.schedule_id == schedule_id
    ).order_by(FryMetricGroup.metric_group_name).all()
    return metric_groups


@router.get("/metric-groups/{metric_group_id}", response_model=FryMetricGroupWithLineItems)
def get_metric_group(
    metric_group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific FRY metric group with all line items."""
    metric_group = db.query(FryMetricGroup).options(
        joinedload(FryMetricGroup.line_items)
    ).filter(FryMetricGroup.metric_group_id == metric_group_id).first()

    if not metric_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FRY metric group with ID {metric_group_id} not found"
        )

    return metric_group


@router.post("/schedules/{schedule_id}/metric-groups", response_model=FryMetricGroupResponse, status_code=status.HTTP_201_CREATED)
def create_metric_group(
    schedule_id: int,
    metric_group_data: FryMetricGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new FRY metric group (Admin only)."""
    # Verify schedule exists
    schedule = db.query(FrySchedule).filter(FrySchedule.schedule_id == schedule_id).first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FRY schedule with ID {schedule_id} not found"
        )

    metric_group = FryMetricGroup(schedule_id=schedule_id, **metric_group_data.model_dump())
    db.add(metric_group)
    db.commit()
    db.refresh(metric_group)
    return metric_group


@router.patch("/metric-groups/{metric_group_id}", response_model=FryMetricGroupResponse)
def update_metric_group(
    metric_group_id: int,
    metric_group_data: FryMetricGroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a FRY metric group (Admin only)."""
    metric_group = db.query(FryMetricGroup).filter(FryMetricGroup.metric_group_id == metric_group_id).first()
    if not metric_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FRY metric group with ID {metric_group_id} not found"
        )

    for field, value in metric_group_data.model_dump(exclude_unset=True).items():
        setattr(metric_group, field, value)

    db.commit()
    db.refresh(metric_group)
    return metric_group


@router.delete("/metric-groups/{metric_group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_metric_group(
    metric_group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a FRY metric group (Admin only). Cascades to line items."""
    metric_group = db.query(FryMetricGroup).filter(FryMetricGroup.metric_group_id == metric_group_id).first()
    if not metric_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FRY metric group with ID {metric_group_id} not found"
        )

    db.delete(metric_group)
    db.commit()
    return None


# ============================================================================
# FRY Line Items
# ============================================================================

@router.get("/metric-groups/{metric_group_id}/line-items", response_model=List[FryLineItemResponse])
def list_line_items(
    metric_group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all line items for a specific FRY metric group."""
    # Verify metric group exists
    metric_group = db.query(FryMetricGroup).filter(FryMetricGroup.metric_group_id == metric_group_id).first()
    if not metric_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FRY metric group with ID {metric_group_id} not found"
        )

    line_items = db.query(FryLineItem).filter(
        FryLineItem.metric_group_id == metric_group_id
    ).order_by(FryLineItem.sort_order, FryLineItem.line_item_id).all()
    return line_items


@router.get("/line-items/{line_item_id}", response_model=FryLineItemResponse)
def get_line_item(
    line_item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific FRY line item."""
    line_item = db.query(FryLineItem).filter(FryLineItem.line_item_id == line_item_id).first()

    if not line_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FRY line item with ID {line_item_id} not found"
        )

    return line_item


@router.post("/metric-groups/{metric_group_id}/line-items", response_model=FryLineItemResponse, status_code=status.HTTP_201_CREATED)
def create_line_item(
    metric_group_id: int,
    line_item_data: FryLineItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new FRY line item (Admin only)."""
    # Verify metric group exists
    metric_group = db.query(FryMetricGroup).filter(FryMetricGroup.metric_group_id == metric_group_id).first()
    if not metric_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FRY metric group with ID {metric_group_id} not found"
        )

    line_item = FryLineItem(metric_group_id=metric_group_id, **line_item_data.model_dump())
    db.add(line_item)
    db.commit()
    db.refresh(line_item)
    return line_item


@router.patch("/line-items/{line_item_id}", response_model=FryLineItemResponse)
def update_line_item(
    line_item_id: int,
    line_item_data: FryLineItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a FRY line item (Admin only)."""
    line_item = db.query(FryLineItem).filter(FryLineItem.line_item_id == line_item_id).first()
    if not line_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FRY line item with ID {line_item_id} not found"
        )

    for field, value in line_item_data.model_dump(exclude_unset=True).items():
        setattr(line_item, field, value)

    db.commit()
    db.refresh(line_item)
    return line_item


@router.delete("/line-items/{line_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_line_item(
    line_item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a FRY line item (Admin only)."""
    line_item = db.query(FryLineItem).filter(FryLineItem.line_item_id == line_item_id).first()
    if not line_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FRY line item with ID {line_item_id} not found"
        )

    db.delete(line_item)
    db.commit()
    return None
