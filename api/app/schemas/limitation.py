"""Model Limitations schemas."""
from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import datetime
from typing import Optional, List, Any, Literal
from app.schemas.taxonomy import TaxonomyValueResponse


# ==================== HELPER SCHEMAS ====================

class UserSummary(BaseModel):
    """Minimal user info for limitation responses."""
    user_id: int
    full_name: str
    email: str

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ModelSummary(BaseModel):
    """Minimal model info for limitation responses."""
    model_id: int
    model_name: str
    status: str

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ValidationRequestSummary(BaseModel):
    """Minimal validation request info for limitation responses."""
    request_id: int
    validation_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    @model_validator(mode='before')
    @classmethod
    def extract_validation_type_label(cls, data: Any) -> Any:
        """Extract validation_type label from ORM relationship object."""
        if isinstance(data, dict):
            return data
        if hasattr(data, 'request_id'):
            validation_type_label = None
            if hasattr(data, 'validation_type') and data.validation_type is not None:
                validation_type_label = getattr(data.validation_type, 'label', None)
            return {
                'request_id': data.request_id,
                'validation_type': validation_type_label
            }
        return data


class ModelVersionSummary(BaseModel):
    """Minimal model version info for limitation responses."""
    version_id: int
    version_number: str

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class RecommendationSummary(BaseModel):
    """Minimal recommendation info for limitation responses."""
    recommendation_id: int
    recommendation_code: str
    title: str

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class RegionSummary(BaseModel):
    """Minimal region info for critical limitations report."""
    region_id: int
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# ==================== LIMITATION SCHEMAS ====================

class LimitationBase(BaseModel):
    """Base schema for limitation."""
    validation_request_id: Optional[int] = None
    model_version_id: Optional[int] = None
    significance: Literal["Critical", "Non-Critical"]
    category_id: int
    description: str = Field(..., min_length=1)
    impact_assessment: str = Field(..., min_length=1)
    conclusion: Literal["Mitigate", "Accept"]
    conclusion_rationale: str = Field(..., min_length=1)
    user_awareness_description: Optional[str] = None
    recommendation_id: Optional[int] = None

    @model_validator(mode='after')
    def validate_critical_awareness(self):
        """Critical limitations must have user awareness description."""
        if self.significance == "Critical" and not self.user_awareness_description:
            raise ValueError("User awareness description is required for Critical limitations")
        return self


    model_config = ConfigDict(protected_namespaces=())
class LimitationCreate(LimitationBase):
    """Schema for creating a limitation."""
    pass


class LimitationUpdate(BaseModel):
    """Schema for updating a limitation."""
    validation_request_id: Optional[int] = None
    model_version_id: Optional[int] = None
    significance: Optional[Literal["Critical", "Non-Critical"]] = None
    category_id: Optional[int] = None
    description: Optional[str] = None
    impact_assessment: Optional[str] = None
    conclusion: Optional[Literal["Mitigate", "Accept"]] = None
    conclusion_rationale: Optional[str] = None
    user_awareness_description: Optional[str] = None
    recommendation_id: Optional[int] = None


    model_config = ConfigDict(protected_namespaces=())
class LimitationRetire(BaseModel):
    """Schema for retiring a limitation."""
    retirement_reason: str = Field(..., min_length=1)


class LimitationResponse(BaseModel):
    """Full response schema for limitation."""
    limitation_id: int
    model_id: int
    model: ModelSummary
    validation_request_id: Optional[int] = None
    validation_request: Optional[ValidationRequestSummary] = None
    model_version_id: Optional[int] = None
    model_version: Optional[ModelVersionSummary] = None
    recommendation_id: Optional[int] = None
    recommendation: Optional[RecommendationSummary] = None
    significance: str
    category_id: int
    category: TaxonomyValueResponse
    description: str
    impact_assessment: str
    conclusion: str
    conclusion_rationale: str
    user_awareness_description: Optional[str] = None
    is_retired: bool
    retirement_date: Optional[datetime] = None
    retirement_reason: Optional[str] = None
    retired_by: Optional[UserSummary] = None
    created_by: UserSummary
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class LimitationListResponse(BaseModel):
    """List response schema for limitation (minimal fields)."""
    limitation_id: int
    model_id: int
    significance: str
    category: TaxonomyValueResponse
    description: str
    conclusion: str
    validation_request_id: Optional[int] = None
    is_retired: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# ==================== REPORT SCHEMAS ====================

class CriticalLimitationReportItem(BaseModel):
    """Item in the critical limitations report."""
    limitation_id: int
    model_id: int
    model_name: str
    region_name: Optional[str] = None
    category_label: str
    description: str
    impact_assessment: str
    conclusion: str
    conclusion_rationale: str
    user_awareness_description: str
    originating_validation: Optional[str] = None
    created_at: datetime


    model_config = ConfigDict(protected_namespaces=())
class CriticalLimitationsReportResponse(BaseModel):
    """Response for critical limitations report."""
    filters_applied: dict
    total_count: int
    items: List[CriticalLimitationReportItem]
