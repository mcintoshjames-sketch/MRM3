"""KPI Report schemas for model risk management metrics."""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


class KPIDecomposition(BaseModel):
    """Decomposition of a ratio/percentage metric showing numerator and denominator."""
    numerator: int = Field(..., description="Count of items meeting the criteria")
    denominator: int = Field(..., description="Total count of items in scope")
    percentage: float = Field(..., description="Calculated percentage (numerator/denominator * 100)")
    numerator_label: str = Field(..., description="Human-readable label for numerator (e.g., 'on time')")
    denominator_label: str = Field(..., description="Human-readable label for denominator (e.g., 'total')")


class KPIBreakdown(BaseModel):
    """Breakdown category for metrics showing distribution across categories."""
    category: str = Field(..., description="Category name (e.g., 'Tier 1 (High)')")
    count: int = Field(..., description="Count of items in this category")
    percentage: float = Field(..., description="Percentage of total")


class KPIMetric(BaseModel):
    """Individual KPI metric with value and metadata."""
    metric_id: str = Field(..., description="Metric ID from METRICS.json (e.g., '4.1', '4.7')")
    metric_name: str = Field(..., description="Human-readable metric name")
    category: str = Field(..., description="Grouping category (e.g., 'Model Inventory', 'Validation')")
    metric_type: str = Field(..., description="Type of metric: 'count', 'ratio', 'duration', 'breakdown'")

    # Value fields - only one will be populated based on metric_type
    count_value: Optional[int] = Field(None, description="Value for count metrics")
    ratio_value: Optional[KPIDecomposition] = Field(None, description="Value for ratio/percentage metrics")
    duration_value: Optional[float] = Field(None, description="Value for duration metrics (in days)")
    breakdown_value: Optional[List[KPIBreakdown]] = Field(None, description="Value for breakdown metrics")

    # Metadata
    definition: str = Field(..., description="Metric definition from METRICS.json")
    calculation: str = Field(..., description="Calculation method/formula")
    is_kri: bool = Field(False, description="Whether this is a Key Risk Indicator")


class KPIReportResponse(BaseModel):
    """Complete KPI report response."""
    report_generated_at: datetime = Field(..., description="Timestamp when report was generated")
    as_of_date: date = Field(..., description="Date the metrics are calculated as of")
    metrics: List[KPIMetric] = Field(..., description="List of all KPI metrics")
    total_active_models: int = Field(..., description="Total count of active models (reference value)")

    # Region filter context
    region_id: Optional[int] = Field(None, description="Region ID if filtering by region, None for all regions")
    region_name: str = Field("All Regions", description="Region name or 'All Regions' if no filter")

    model_config = {"from_attributes": True}
