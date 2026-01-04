"""LOB (Line of Business) unit schemas."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List, Optional
from datetime import datetime
import re

from app.schemas.team import TeamBasic


class LOBUnitBase(BaseModel):
    """Base schema for LOB unit."""
    code: str = Field(..., max_length=50, description="Short code (e.g., 'RETAIL', 'PB')")
    name: str = Field(..., max_length=255, description="Display name")
    org_unit: str = Field(..., min_length=5, max_length=5, description="5-char org unit ID (e.g., '12345' or 'S0001')")
    sort_order: int = Field(default=0, description="Display ordering within parent")
    description: Optional[str] = Field(None, description="Description of the LOB unit")

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate code is alphanumeric + underscore only."""
        if not re.match(r'^[A-Za-z0-9_]+$', v):
            raise ValueError('Code must contain only alphanumeric characters and underscores')
        return v.upper()

    @field_validator('org_unit')
    @classmethod
    def validate_org_unit(cls, v: str) -> str:
        """Validate org_unit format: 5 digits OR S + 4 digits."""
        if len(v) != 5:
            raise ValueError('org_unit must be exactly 5 characters')
        # Real org_units: 5 digits (e.g., "12345", "00001")
        # Synthetic org_units: S + 4 digits (e.g., "S0001")
        if v[0].upper() == 'S':
            if not v[1:].isdigit():
                raise ValueError('Synthetic org_unit must be S followed by 4 digits (e.g., S0001)')
            return v.upper()
        elif v.isdigit():
            return v
        else:
            raise ValueError('org_unit must be 5 digits or S + 4 digits')
        return v


class LOBUnitCreate(LOBUnitBase):
    """Schema for creating a new LOB unit."""
    parent_id: Optional[int] = Field(None, description="Parent LOB unit ID (null for root/SBU level)")
    # Metadata fields (typically populated on leaf nodes via CSV import)
    contact_name: Optional[str] = Field(None, max_length=255, description="Contact person name")
    org_description: Optional[str] = Field(None, description="Org unit description")
    legal_entity_id: Optional[str] = Field(None, max_length=50, description="Legal entity ID")
    legal_entity_name: Optional[str] = Field(None, max_length=255, description="Legal entity name")
    short_name: Optional[str] = Field(None, max_length=100, description="Short display name")
    status_code: Optional[str] = Field(None, max_length=20, description="Status code")
    tier: Optional[str] = Field(None, max_length=50, description="Tier classification")


class LOBUnitUpdate(BaseModel):
    """Schema for updating an LOB unit."""
    code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=255)
    org_unit: Optional[str] = Field(None, min_length=5, max_length=5)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None
    # Metadata fields
    contact_name: Optional[str] = Field(None, max_length=255)
    org_description: Optional[str] = None
    legal_entity_id: Optional[str] = Field(None, max_length=50)
    legal_entity_name: Optional[str] = Field(None, max_length=255)
    short_name: Optional[str] = Field(None, max_length=100)
    status_code: Optional[str] = Field(None, max_length=20)
    tier: Optional[str] = Field(None, max_length=50)

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: Optional[str]) -> Optional[str]:
        """Validate code is alphanumeric + underscore only."""
        if v is not None and not re.match(r'^[A-Za-z0-9_]+$', v):
            raise ValueError('Code must contain only alphanumeric characters and underscores')
        return v.upper() if v else v

    @field_validator('org_unit')
    @classmethod
    def validate_org_unit(cls, v: Optional[str]) -> Optional[str]:
        """Validate org_unit format: 5 digits OR S + 4 digits."""
        if v is None:
            return v
        if len(v) != 5:
            raise ValueError('org_unit must be exactly 5 characters')
        if v[0].upper() == 'S':
            if not v[1:].isdigit():
                raise ValueError('Synthetic org_unit must be S followed by 4 digits')
            return v.upper()
        elif v.isdigit():
            return v
        else:
            raise ValueError('org_unit must be 5 digits or S + 4 digits')
        return v


class LOBUnitResponse(LOBUnitBase):
    """Schema for LOB unit response (flat)."""
    lob_id: int
    parent_id: Optional[int] = None
    level: int
    is_active: bool
    full_path: str = Field(..., description="Computed full path: 'Retail > Private Banking > Wealth Management'")
    user_count: int = Field(default=0, description="Number of users in this LOB unit")
    # Metadata fields (typically on leaf nodes)
    contact_name: Optional[str] = None
    org_description: Optional[str] = None
    legal_entity_id: Optional[str] = None
    legal_entity_name: Optional[str] = None
    short_name: Optional[str] = None
    status_code: Optional[str] = None
    tier: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class LOBUnitTreeNode(BaseModel):
    """Schema for LOB unit tree node (hierarchical)."""
    lob_id: int
    parent_id: Optional[int] = None
    code: str
    name: str
    org_unit: str
    level: int
    sort_order: int
    is_active: bool
    full_path: str
    user_count: int = 0
    description: Optional[str] = None
    # Metadata fields (typically on leaf nodes)
    contact_name: Optional[str] = None
    org_description: Optional[str] = None
    legal_entity_id: Optional[str] = None
    legal_entity_name: Optional[str] = None
    short_name: Optional[str] = None
    status_code: Optional[str] = None
    tier: Optional[str] = None
    children: List[LOBUnitTreeNode] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# Enable self-referential model
LOBUnitTreeNode.model_rebuild()


class LOBUnitTeamTreeNode(BaseModel):
    """LOB unit tree node with team assignment metadata."""
    lob_id: int
    parent_id: Optional[int] = None
    code: str
    name: str
    org_unit: str
    level: int
    is_active: bool
    direct_team_id: Optional[int] = None
    direct_team_name: Optional[str] = None
    effective_team_id: Optional[int] = None
    effective_team_name: Optional[str] = None
    children: List["LOBUnitTeamTreeNode"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


LOBUnitTeamTreeNode.model_rebuild()


class LOBTreeWithTeamsResponse(BaseModel):
    """Response schema for LOB tree with team assignments."""
    lob_units: List[LOBUnitTeamTreeNode] = Field(default_factory=list)
    teams: List[TeamBasic] = Field(default_factory=list)


class LOBImportPreview(BaseModel):
    """Schema for CSV import preview (dry run results)."""
    to_create: List[dict] = Field(default_factory=list, description="Nodes that will be created")
    to_update: List[dict] = Field(default_factory=list, description="Nodes that will be updated")
    to_skip: List[dict] = Field(default_factory=list, description="Nodes that will be skipped (no changes)")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    detected_columns: List[str] = Field(default_factory=list, description="Detected hierarchy columns from CSV")
    max_depth: int = Field(default=0, description="Maximum hierarchy depth detected")


class LOBImportResult(BaseModel):
    """Schema for CSV import result."""
    created_count: int
    updated_count: int
    skipped_count: int
    errors: List[str] = Field(default_factory=list)


class LOBUnitWithAncestors(LOBUnitResponse):
    """Schema for LOB unit with ancestor chain."""
    ancestors: List[LOBUnitResponse] = Field(default_factory=list, description="Ancestor chain from root to parent")


class LOBUnitWithDescendants(LOBUnitResponse):
    """Schema for LOB unit with descendants."""
    descendants: List[LOBUnitResponse] = Field(default_factory=list, description="All descendant nodes")
