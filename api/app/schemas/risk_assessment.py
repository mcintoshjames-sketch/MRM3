"""Pydantic schemas for Model Risk Assessment API."""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Factor Rating Schemas
# ============================================================================

class FactorRatingInput(BaseModel):
    """Input schema for a single factor rating."""
    factor_id: int
    rating: Optional[str] = Field(None, pattern="^(HIGH|MEDIUM|LOW)$")
    comment: Optional[str] = None


class QualitativeFactorResponse(BaseModel):
    """Response schema for a qualitative factor assessment."""
    model_config = ConfigDict(from_attributes=True)

    factor_assessment_id: int
    factor_id: int
    factor_code: str
    factor_name: str
    rating: Optional[str] = None
    comment: Optional[str] = None
    weight: float
    score: Optional[float] = None


# ============================================================================
# Assessment Create/Update Schemas
# ============================================================================

class RiskAssessmentCreate(BaseModel):
    """Schema for creating a risk assessment."""
    region_id: Optional[int] = None  # None = Global assessment

    # Quantitative
    quantitative_rating: Optional[str] = Field(None, pattern="^(HIGH|MEDIUM|LOW)$")
    quantitative_comment: Optional[str] = None
    quantitative_override: Optional[str] = Field(None, pattern="^(HIGH|MEDIUM|LOW)$")
    quantitative_override_comment: Optional[str] = None

    # Qualitative factors
    factor_ratings: List[FactorRatingInput] = Field(default_factory=list)

    # Qualitative override
    qualitative_override: Optional[str] = Field(None, pattern="^(HIGH|MEDIUM|LOW)$")
    qualitative_override_comment: Optional[str] = None

    # Final tier override
    derived_risk_tier_override: Optional[str] = Field(None, pattern="^(HIGH|MEDIUM|LOW|VERY_LOW)$")
    derived_risk_tier_override_comment: Optional[str] = None


class RiskAssessmentUpdate(BaseModel):
    """Schema for updating a risk assessment."""
    # Quantitative
    quantitative_rating: Optional[str] = Field(None, pattern="^(HIGH|MEDIUM|LOW)$")
    quantitative_comment: Optional[str] = None
    quantitative_override: Optional[str] = Field(None, pattern="^(HIGH|MEDIUM|LOW)$")
    quantitative_override_comment: Optional[str] = None

    # Qualitative factors
    factor_ratings: List[FactorRatingInput] = Field(default_factory=list)

    # Qualitative override
    qualitative_override: Optional[str] = Field(None, pattern="^(HIGH|MEDIUM|LOW)$")
    qualitative_override_comment: Optional[str] = None

    # Final tier override
    derived_risk_tier_override: Optional[str] = Field(None, pattern="^(HIGH|MEDIUM|LOW|VERY_LOW)$")
    derived_risk_tier_override_comment: Optional[str] = None


# ============================================================================
# Nested Response Schemas
# ============================================================================

class RegionBrief(BaseModel):
    """Brief region info for assessment response."""
    model_config = ConfigDict(from_attributes=True)

    region_id: int
    code: str
    name: str


class UserBrief(BaseModel):
    """Brief user info for assessment response."""
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    email: str
    full_name: str


class TaxonomyValueBrief(BaseModel):
    """Brief taxonomy value info for assessment response."""
    model_config = ConfigDict(from_attributes=True)

    value_id: int
    code: str
    label: str


# ============================================================================
# Assessment Response Schema
# ============================================================================

class RiskAssessmentResponse(BaseModel):
    """Full response schema for a risk assessment."""
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    assessment_id: int
    model_id: int
    region: Optional[RegionBrief] = None

    # Qualitative
    qualitative_factors: List[QualitativeFactorResponse] = Field(default_factory=list)
    qualitative_calculated_score: Optional[float] = None
    qualitative_calculated_level: Optional[str] = None
    qualitative_override: Optional[str] = None
    qualitative_override_comment: Optional[str] = None
    qualitative_effective_level: Optional[str] = None

    # Quantitative
    quantitative_rating: Optional[str] = None
    quantitative_comment: Optional[str] = None
    quantitative_override: Optional[str] = None
    quantitative_override_comment: Optional[str] = None
    quantitative_effective_rating: Optional[str] = None

    # Derived risk
    derived_risk_tier: Optional[str] = None
    derived_risk_tier_override: Optional[str] = None
    derived_risk_tier_override_comment: Optional[str] = None
    derived_risk_tier_effective: Optional[str] = None

    # Final
    final_tier: Optional[TaxonomyValueBrief] = None

    # Metadata
    assessed_by: Optional[UserBrief] = None
    assessed_at: Optional[datetime] = None
    is_complete: bool = False

    created_at: datetime
    updated_at: datetime


class RiskAssessmentListResponse(BaseModel):
    """List response for risk assessments."""
    assessments: List[RiskAssessmentResponse]


# ============================================================================
# Assessment History Schema
# ============================================================================

class RiskAssessmentHistoryItem(BaseModel):
    """A single history item for risk assessment changes."""
    model_config = ConfigDict(from_attributes=True)

    log_id: int
    action: str  # CREATE, UPDATE, DELETE
    timestamp: datetime
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    region_id: Optional[int] = None
    region_name: Optional[str] = None
    old_tier: Optional[str] = None
    new_tier: Optional[str] = None
    old_quantitative: Optional[str] = None
    new_quantitative: Optional[str] = None
    old_qualitative: Optional[str] = None
    new_qualitative: Optional[str] = None
    changes_summary: str  # Human-readable summary


# ============================================================================
# Assessment Status Schema
# ============================================================================

class GlobalAssessmentStatusResponse(BaseModel):
    """Response schema for global risk assessment status check."""
    model_id: int
    has_assessment: bool
    is_complete: bool
    assessed_at: Optional[datetime] = None
    final_tier_id: Optional[int] = None
    assessment_id: Optional[int] = None
    model_config = ConfigDict(protected_namespaces=())
