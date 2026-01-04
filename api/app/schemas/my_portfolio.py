"""My Portfolio Report schemas for model owner dashboard."""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


class PortfolioSummary(BaseModel):
    """Summary statistics for the portfolio."""
    total_models: int = Field(...,
                              description="Total number of models in portfolio")
    action_items_count: int = Field(...,
                                    description="Number of items requiring action")
    overdue_count: int = Field(..., description="Number of overdue items")
    compliant_percentage: float = Field(
        ..., description="Percentage of models that are compliant")
    models_compliant: int = Field(...,
                                  description="Number of compliant models")
    models_non_compliant: int = Field(...,
                                      description="Number of non-compliant models")
    yellow_alerts: int = Field(...,
                               description="Number of yellow monitoring alerts")
    red_alerts: int = Field(..., description="Number of red monitoring alerts")
    open_exceptions_count: int = Field(
        0, description="Number of open model exceptions")


class ActionItem(BaseModel):
    """An item requiring user action."""
    type: str = Field(...,
                      description="Type: attestation, recommendation, validation_submission")
    urgency: str = Field(...,
                         description="Urgency: overdue, in_grace_period, due_soon, upcoming")
    model_id: int = Field(..., description="ID of the related model")
    model_name: str = Field(..., description="Name of the related model")
    item_id: int = Field(..., description="ID of the specific item")
    item_code: Optional[str] = Field(
        None, description="Code/reference (e.g., REC-2025-00042)")
    title: str = Field(..., description="Brief title of the action needed")
    action_description: str = Field(...,
                                    description="Description of the action required")
    due_date: Optional[date] = Field(
        None, description="Due date for the action")
    days_until_due: Optional[int] = Field(
        None, description="Days until due (negative if overdue)")
    link: str = Field(..., description="Navigation path to the item")


class MonitoringAlert(BaseModel):
    """A monitoring result with yellow or red outcome."""
    model_id: int = Field(..., description="ID of the model")
    model_name: str = Field(..., description="Name of the model")
    metric_name: str = Field(..., description="Name of the KPM metric")
    metric_value: Optional[float] = Field(
        None, description="Numeric value (if quantitative)")
    qualitative_outcome: Optional[str] = Field(
        None, description="Qualitative outcome label")
    outcome: str = Field(..., description="Calculated outcome: YELLOW or RED")
    cycle_name: str = Field(..., description="Name of the monitoring cycle")
    cycle_id: int = Field(..., description="ID of the monitoring cycle")
    plan_id: int = Field(..., description="ID of the monitoring plan")
    result_date: date = Field(..., description="Date the result was recorded")


class ExceptionItem(BaseModel):
    """An open model exception requiring attention."""
    exception_id: int = Field(..., description="Exception ID")
    exception_code: str = Field(...,
                                description="Exception code (e.g., EXC-2025-00001)")
    exception_type: str = Field(
        ..., description="Type: UNMITIGATED_PERFORMANCE, OUTSIDE_INTENDED_PURPOSE, USE_PRIOR_TO_VALIDATION")
    exception_type_label: str = Field(...,
                                      description="Human-readable exception type")
    model_id: int = Field(..., description="ID of the model")
    model_name: str = Field(..., description="Name of the model")
    status: str = Field(..., description="Status: OPEN or ACKNOWLEDGED")
    description: str = Field(..., description="Exception description")
    detected_at: datetime = Field(...,
                                  description="When the exception was detected")
    acknowledged_at: Optional[datetime] = Field(
        None, description="When acknowledged (if applicable)")
    link: str = Field(..., description="Navigation path to the model")


class CalendarItem(BaseModel):
    """A deadline item for calendar view."""
    due_date: date = Field(..., description="Due date")
    type: str = Field(...,
                      description="Type: attestation, recommendation, validation_submission")
    model_id: int = Field(..., description="ID of the related model")
    model_name: str = Field(..., description="Name of the related model")
    item_id: int = Field(..., description="ID of the specific item")
    item_code: Optional[str] = Field(
        None, description="Code/reference if applicable")
    title: str = Field(..., description="Brief title")
    is_overdue: bool = Field(..., description="Whether the item is past due")


class PortfolioModel(BaseModel):
    """A model in the user's portfolio."""
    model_id: int = Field(..., description="Model ID")
    model_name: str = Field(..., description="Model name")
    risk_tier: Optional[str] = Field(
        None, description="Risk tier label (e.g., 'Tier 1')")
    risk_tier_code: Optional[str] = Field(None, description="Risk tier code")
    approval_status: Optional[str] = Field(
        None, description="Model approval status label (e.g., 'Approved', 'Expired')")
    approval_status_code: Optional[str] = Field(
        None, description="Model approval status code (e.g., 'APPROVED', 'EXPIRED')")
    last_validation_date: Optional[date] = Field(
        None, description="Date of last validation")
    next_submission_due: Optional[date] = Field(
        None, description="Next submission due date")
    next_validation_due: Optional[date] = Field(
        None, description="Next validation due date")
    days_until_submission_due: Optional[int] = Field(
        None, description="Days until next submission due")
    days_until_validation_due: Optional[int] = Field(
        None, description="Days until next validation due")
    open_recommendations: int = Field(
        0, description="Count of open recommendations")
    attestation_status: Optional[str] = Field(
        None, description="Current attestation status")
    yellow_alerts: int = Field(
        0, description="Count of yellow monitoring alerts")
    red_alerts: int = Field(0, description="Count of red monitoring alerts")
    open_exceptions: int = Field(
        0, description="Count of open model exceptions")
    has_overdue_items: bool = Field(
        False, description="Whether model has any overdue items")
    ownership_type: str = Field(
        ..., description="How user owns: primary, shared, developer, delegate")


class MyPortfolioResponse(BaseModel):
    """Complete portfolio report response."""
    report_generated_at: datetime = Field(...,
                                          description="Timestamp when report was generated")
    as_of_date: date = Field(...,
                             description="Date the metrics are calculated as of")
    team_id: Optional[int] = Field(
        None, description="Team ID if filtered, 0 for Unassigned, None for all")
    team_name: str = Field(
        "All Teams", description="Team name or 'All Teams' if no filter")

    summary: PortfolioSummary = Field(..., description="Summary statistics")
    action_items: List[ActionItem] = Field(
        ..., description="Items requiring action, sorted by urgency")
    monitoring_alerts: List[MonitoringAlert] = Field(
        ..., description="Yellow/red monitoring results")
    open_exceptions: List[ExceptionItem] = Field(
        ..., description="Open model exceptions requiring attention")
    calendar_items: List[CalendarItem] = Field(
        ..., description="All deadlines for calendar view")
    models: List[PortfolioModel] = Field(...,
                                         description="All models in portfolio")

    model_config = {"from_attributes": True}
