"""KPM (Key Performance Metrics) schemas."""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class KpmEvaluationTypeEnum(str, Enum):
    """KPM evaluation type enum for API validation."""
    QUANTITATIVE = "Quantitative"
    QUALITATIVE = "Qualitative"
    OUTCOME_ONLY = "Outcome Only"


class KpmCategoryTypeEnum(str, Enum):
    """KPM category type enum for API validation."""
    QUANTITATIVE = "Quantitative"
    QUALITATIVE = "Qualitative"


class KpmBase(BaseModel):
    """Base schema for KPM."""
    name: str
    description: Optional[str] = None
    calculation: Optional[str] = None
    interpretation: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    evaluation_type: KpmEvaluationTypeEnum = KpmEvaluationTypeEnum.QUANTITATIVE


class KpmCreate(KpmBase):
    """Create schema for KPM."""
    category_id: int


class KpmUpdate(BaseModel):
    """Update schema for KPM (all fields optional)."""
    category_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    calculation: Optional[str] = None
    interpretation: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    evaluation_type: Optional[KpmEvaluationTypeEnum] = None


class KpmResponse(BaseModel):
    """Response schema for KPM."""
    kpm_id: int
    category_id: int
    name: str
    description: Optional[str] = None
    calculation: Optional[str] = None
    interpretation: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    evaluation_type: str  # Return as string for flexibility

    class Config:
        from_attributes = True


class KpmCategoryBase(BaseModel):
    """Base schema for KPM category."""
    code: str
    name: str
    description: Optional[str] = None
    sort_order: int = 0
    category_type: KpmCategoryTypeEnum = KpmCategoryTypeEnum.QUANTITATIVE


class KpmCategoryCreate(KpmCategoryBase):
    """Create schema for KPM category."""
    pass


class KpmCategoryUpdate(BaseModel):
    """Update schema for KPM category (all fields optional)."""
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    category_type: Optional[KpmCategoryTypeEnum] = None


class KpmCategoryResponse(BaseModel):
    """Response schema for KPM category with nested KPMs."""
    category_id: int
    code: str
    name: str
    description: Optional[str] = None
    sort_order: int = 0
    category_type: str  # Return as string for flexibility
    kpms: List[KpmResponse] = []

    class Config:
        from_attributes = True
