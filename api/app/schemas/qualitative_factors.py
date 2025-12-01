"""Pydantic schemas for Qualitative Risk Factor Configuration API."""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator


# ============================================================================
# Guidance Schemas
# ============================================================================

class GuidanceCreate(BaseModel):
    """Schema for creating guidance."""
    rating: str = Field(..., pattern="^(HIGH|MEDIUM|LOW|VERY_HIGH|VERY_LOW)$")
    points: int = Field(..., ge=0, le=10)
    description: str = Field(..., min_length=1)
    sort_order: int = Field(default=0)


class GuidanceUpdate(BaseModel):
    """Schema for updating guidance."""
    rating: Optional[str] = Field(None, pattern="^(HIGH|MEDIUM|LOW|VERY_HIGH|VERY_LOW)$")
    points: Optional[int] = Field(None, ge=0, le=10)
    description: Optional[str] = None
    sort_order: Optional[int] = None


class GuidanceResponse(BaseModel):
    """Response schema for guidance."""
    model_config = ConfigDict(from_attributes=True)

    guidance_id: int
    factor_id: int
    rating: str
    points: int
    description: str
    sort_order: int


# ============================================================================
# Factor Schemas
# ============================================================================

class FactorCreate(BaseModel):
    """Schema for creating a factor."""
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    weight: float = Field(..., ge=0.0, le=1.0)
    sort_order: int = Field(default=0)
    guidance: Optional[List[GuidanceCreate]] = None

    @field_validator('weight')
    @classmethod
    def validate_weight_precision(cls, v):
        """Ensure weight has reasonable precision."""
        return round(v, 4)


class FactorUpdate(BaseModel):
    """Schema for updating a factor."""
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator('weight')
    @classmethod
    def validate_weight_precision(cls, v):
        """Ensure weight has reasonable precision."""
        if v is not None:
            return round(v, 4)
        return v


class WeightUpdate(BaseModel):
    """Schema for updating weight only."""
    weight: float = Field(..., ge=0.0, le=1.0)

    @field_validator('weight')
    @classmethod
    def validate_weight_precision(cls, v):
        """Ensure weight has reasonable precision."""
        return round(v, 4)


class FactorResponse(BaseModel):
    """Response schema for a factor with guidance."""
    model_config = ConfigDict(from_attributes=True)

    factor_id: int
    code: str
    name: str
    description: Optional[str] = None
    weight: float
    sort_order: int
    is_active: bool
    guidance: List[GuidanceResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Utility Schemas
# ============================================================================

class WeightValidationResponse(BaseModel):
    """Response for weight validation."""
    valid: bool
    total: float
    message: Optional[str] = None


class ReorderRequest(BaseModel):
    """Request schema for reordering factors."""
    factor_ids: List[int]
