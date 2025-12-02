"""Residual Risk Map schemas."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ResidualRiskMatrixCell(BaseModel):
    """A single cell in the residual risk matrix."""
    inherent_risk: str = Field(..., description="The inherent risk tier (row)")
    scorecard_outcome: str = Field(..., description="The scorecard outcome (column)")
    residual_risk: str = Field(..., description="The resulting residual risk")


class ResidualRiskMatrixConfig(BaseModel):
    """The full matrix configuration structure.

    Example:
    {
        "row_axis_label": "Inherent Risk Tier",
        "column_axis_label": "Scorecard Outcome",
        "row_values": ["High", "Medium", "Low", "Very Low"],
        "column_values": ["Red", "Yellow-", "Yellow", "Yellow+", "Green-", "Green"],
        "result_values": ["High", "Medium", "Low"],
        "matrix": {
            "High": {
                "Red": "High",
                "Yellow-": "High",
                ...
            },
            ...
        }
    }
    """
    row_axis_label: str = Field(
        default="Inherent Risk Tier",
        description="Label for the row axis (inherent risk tiers)"
    )
    column_axis_label: str = Field(
        default="Scorecard Outcome",
        description="Label for the column axis (scorecard outcomes)"
    )
    row_values: list[str] = Field(
        default=["High", "Medium", "Low", "Very Low"],
        description="Valid values for the row axis (inherent risk tiers)"
    )
    column_values: list[str] = Field(
        default=["Red", "Yellow-", "Yellow", "Yellow+", "Green-", "Green"],
        description="Valid values for the column axis (scorecard outcomes)"
    )
    result_values: list[str] = Field(
        default=["High", "Medium", "Low"],
        description="Valid values for the result (residual risk)"
    )
    matrix: dict[str, dict[str, str]] = Field(
        ...,
        description="The 2D matrix mapping (row, column) -> result"
    )


class ResidualRiskMapCreate(BaseModel):
    """Schema for creating a new residual risk map configuration."""
    version_name: Optional[str] = Field(
        None,
        description="Optional display name for this version"
    )
    description: Optional[str] = Field(
        None,
        description="Optional description or changelog"
    )
    matrix_config: ResidualRiskMatrixConfig = Field(
        ...,
        description="The matrix configuration"
    )


class ResidualRiskMapUpdate(BaseModel):
    """Schema for updating the residual risk map configuration.

    When updating, a new version is created (current becomes inactive).
    """
    version_name: Optional[str] = Field(
        None,
        description="Optional display name for the new version"
    )
    description: Optional[str] = Field(
        None,
        description="Optional description or changelog"
    )
    matrix_config: ResidualRiskMatrixConfig = Field(
        ...,
        description="The updated matrix configuration"
    )


class ResidualRiskMapResponse(BaseModel):
    """Response schema for residual risk map configuration."""
    config_id: int
    version_number: int
    version_name: Optional[str]
    description: Optional[str]
    matrix_config: ResidualRiskMatrixConfig
    is_active: bool
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResidualRiskMapListResponse(BaseModel):
    """Response schema for listing residual risk map versions."""
    config_id: int
    version_number: int
    version_name: Optional[str]
    description: Optional[str]
    is_active: bool
    created_by_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ResidualRiskCalculateRequest(BaseModel):
    """Request schema for calculating residual risk."""
    inherent_risk_tier: str = Field(
        ...,
        description="The inherent risk tier (e.g., 'High', 'Medium', 'Low', 'Very Low')"
    )
    scorecard_outcome: str = Field(
        ...,
        description="The scorecard outcome (e.g., 'Green', 'Yellow', 'Red')"
    )


class ResidualRiskCalculateResponse(BaseModel):
    """Response schema for residual risk calculation."""
    inherent_risk_tier: str
    scorecard_outcome: str
    residual_risk: str
    config_version: int = Field(
        ...,
        description="Version of the configuration used for calculation"
    )
