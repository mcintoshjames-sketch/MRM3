"""Model relationship schemas - hierarchy and dependencies."""
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


# ============================================================================
# Model Hierarchy Schemas
# ============================================================================

class ModelHierarchyBase(BaseModel):
    """Base model hierarchy schema."""
    relation_type_id: int = Field(..., description="Taxonomy value ID for relationship type (e.g., SUB_MODEL)")
    effective_date: Optional[date] = Field(None, description="Date when relationship became effective")
    end_date: Optional[date] = Field(None, description="Date when relationship ended")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes about the relationship")


class ModelHierarchyCreate(ModelHierarchyBase):
    """Schema for creating a new model hierarchy relationship."""
    child_model_id: int = Field(..., description="ID of the child (sub) model")


class ModelHierarchyUpdate(BaseModel):
    """Schema for updating a model hierarchy relationship."""
    relation_type_id: Optional[int] = None
    effective_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=500)


class ModelInfo(BaseModel):
    """Nested model information."""
    model_id: int
    model_name: str


class RelationTypeInfo(BaseModel):
    """Nested relation type information."""
    value_id: int
    code: str
    label: str


class ModelHierarchyResponse(ModelHierarchyBase):
    """Full model hierarchy response with relationships."""
    id: int
    parent_model_id: int
    child_model_id: int

    # Nested objects (populated by API)
    parent_model: Optional[ModelInfo] = None
    child_model: Optional[ModelInfo] = None
    relation_type: Optional[RelationTypeInfo] = None

    class Config:
        from_attributes = True


# ============================================================================
# Model Feed Dependency Schemas
# ============================================================================

class ModelFeedDependencyBase(BaseModel):
    """Base model feed dependency schema."""
    dependency_type_id: int = Field(..., description="Taxonomy value ID for dependency type (e.g., INPUT_DATA, SCORE)")
    description: Optional[str] = Field(None, max_length=500, description="Brief description of the dependency")
    effective_date: Optional[date] = Field(None, description="Date when dependency became effective")
    end_date: Optional[date] = Field(None, description="Date when dependency ended")
    is_active: bool = Field(True, description="Whether the dependency is currently active")


class ModelFeedDependencyCreate(ModelFeedDependencyBase):
    """Schema for creating a new model feed dependency."""
    consumer_model_id: int = Field(..., description="ID of the consumer model (receives data)")


class ModelFeedDependencyUpdate(BaseModel):
    """Schema for updating a model feed dependency."""
    dependency_type_id: Optional[int] = None
    description: Optional[str] = Field(None, max_length=500)
    effective_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


class DependencyTypeInfo(BaseModel):
    """Nested dependency type information."""
    value_id: int
    code: str
    label: str


class ModelFeedDependencyResponse(ModelFeedDependencyBase):
    """Full model feed dependency response with relationships."""
    id: int
    feeder_model_id: int
    consumer_model_id: int

    # Nested objects (populated by API)
    feeder_model: Optional[ModelInfo] = None
    consumer_model: Optional[ModelInfo] = None
    dependency_type: Optional[DependencyTypeInfo] = None

    class Config:
        from_attributes = True


# ============================================================================
# Summary/List Schemas
# ============================================================================

class ModelHierarchySummary(BaseModel):
    """Simplified hierarchy info for list views."""
    id: int
    model_id: int
    model_name: str
    relation_type: str
    effective_date: Optional[date]
    end_date: Optional[date]


class ModelDependencySummary(BaseModel):
    """Simplified dependency info for list views."""
    id: int
    model_id: int
    model_name: str
    dependency_type: str
    description: Optional[str]
    is_active: bool
    effective_date: Optional[date]
    end_date: Optional[date]
