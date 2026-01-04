"""Team schemas."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TeamBase(BaseModel):
    """Base team schema."""
    name: str = Field(..., max_length=255, description="Team name")
    description: Optional[str] = Field(None, description="Team description")
    is_active: bool = Field(default=True, description="Whether the team is active")


class TeamCreate(TeamBase):
    """Schema for creating a team."""
    pass


class TeamUpdate(BaseModel):
    """Schema for updating a team."""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class TeamBasic(BaseModel):
    """Minimal team info for embedding in other responses."""
    team_id: int
    name: str

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class LOBUnitBasic(BaseModel):
    """Minimal LOB info for team assignments."""
    lob_id: int
    name: str
    org_unit: str
    level: int
    parent_id: Optional[int] = None
    full_path: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class TeamRead(TeamBase):
    """Team response schema."""
    team_id: int
    created_at: datetime
    updated_at: datetime
    lob_count: int = 0
    model_count: int = 0

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class TeamWithLOBs(TeamRead):
    """Team detail response with direct LOB assignments."""
    lob_units: List[LOBUnitBasic] = []
