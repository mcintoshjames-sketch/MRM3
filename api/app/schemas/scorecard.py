"""Pydantic schemas for Validation Scorecard API."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Valid Rating Values
# ============================================================================

VALID_RATINGS = ["Green", "Green-", "Yellow+",
                 "Yellow", "Yellow-", "Red", "N/A"]
RATING_PATTERN = "^(Green|Green-|Yellow\\+|Yellow|Yellow-|Red|N/A)$"


# ============================================================================
# Configuration Schemas (Sections & Criteria)
# ============================================================================

class ScorecardSectionBase(BaseModel):
    """Base schema for scorecard section."""
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True


class ScorecardSectionCreate(ScorecardSectionBase):
    """Schema for creating a scorecard section."""
    pass


class ScorecardSectionUpdate(BaseModel):
    """Schema for updating a scorecard section."""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ScorecardSectionResponse(ScorecardSectionBase):
    """Response schema for scorecard section."""
    model_config = ConfigDict(from_attributes=True)

    section_id: int
    created_at: datetime
    updated_at: datetime


class ScorecardCriterionBase(BaseModel):
    """Base schema for scorecard criterion."""
    code: str = Field(..., max_length=20)
    section_id: int
    name: str = Field(..., max_length=255)
    description_prompt: Optional[str] = None
    comments_prompt: Optional[str] = None
    include_in_summary: bool = True
    allow_zero: bool = True
    weight: float = 1.0
    sort_order: int = 0
    is_active: bool = True


class ScorecardCriterionCreate(ScorecardCriterionBase):
    """Schema for creating a scorecard criterion."""
    pass


class ScorecardCriterionUpdate(BaseModel):
    """Schema for updating a scorecard criterion."""
    name: Optional[str] = Field(None, max_length=255)
    description_prompt: Optional[str] = None
    comments_prompt: Optional[str] = None
    include_in_summary: Optional[bool] = None
    allow_zero: Optional[bool] = None
    weight: Optional[float] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ScorecardCriterionResponse(ScorecardCriterionBase):
    """Response schema for scorecard criterion."""
    model_config = ConfigDict(from_attributes=True)

    criterion_id: int
    created_at: datetime
    updated_at: datetime


class ScorecardSectionWithCriteria(ScorecardSectionResponse):
    """Section response with nested criteria."""
    criteria: List[ScorecardCriterionResponse] = []


class ScorecardConfigResponse(BaseModel):
    """Full scorecard configuration response."""
    sections: List[ScorecardSectionWithCriteria] = []


# ============================================================================
# Criterion Rating Schemas (Input/Output)
# ============================================================================

class CriterionRatingInput(BaseModel):
    """Input schema for a single criterion rating."""
    criterion_code: str = Field(..., max_length=20)
    rating: Optional[str] = Field(None, pattern=RATING_PATTERN)
    description: Optional[str] = None
    comments: Optional[str] = None


class ScorecardRatingsCreate(BaseModel):
    """Schema for creating/updating all scorecard ratings at once."""
    ratings: List[CriterionRatingInput] = Field(..., min_length=0)


class CriterionRatingUpdate(BaseModel):
    """Schema for updating a single criterion rating."""
    rating: Optional[str] = Field(None, pattern=RATING_PATTERN)
    description: Optional[str] = None
    comments: Optional[str] = None


class OverallNarrativeUpdate(BaseModel):
    """Schema for updating the overall assessment narrative."""
    overall_assessment_narrative: Optional[str] = Field(
        None,
        description="Free-text narrative for overall scorecard assessment"
    )


class CriterionRatingResponse(BaseModel):
    """Response schema for a criterion rating."""
    model_config = ConfigDict(from_attributes=True)

    rating_id: int
    request_id: int
    criterion_code: str
    rating: Optional[str] = None
    description: Optional[str] = None
    comments: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Computed Result Schemas
# ============================================================================

class CriterionDetailResponse(BaseModel):
    """Detailed criterion information with rating and score."""
    criterion_code: str
    criterion_name: str
    section_code: str
    rating: Optional[str] = None
    numeric_score: int
    description: Optional[str] = None
    comments: Optional[str] = None


class SectionSummaryResponse(BaseModel):
    """Section summary with computed score."""
    section_code: str
    section_name: str
    description: Optional[str] = None
    criteria_count: int
    rated_count: int
    unrated_count: int
    numeric_score: int
    rating: Optional[str] = None


class OverallAssessmentResponse(BaseModel):
    """Overall assessment with computed score."""
    numeric_score: int
    rating: Optional[str] = None
    sections_count: int
    rated_sections_count: int
    overall_assessment_narrative: Optional[str] = None


class ScorecardResultResponse(BaseModel):
    """Full scorecard result response."""
    model_config = ConfigDict(from_attributes=True)

    result_id: int
    request_id: int
    overall_numeric_score: Optional[int] = None
    overall_rating: Optional[str] = None
    overall_assessment_narrative: Optional[str] = None
    section_summaries: Optional[dict] = None
    config_snapshot: Optional[dict] = None
    computed_at: datetime


class ConfigCriterionResponse(BaseModel):
    """Criterion config for frontend rendering."""
    code: str
    name: str
    description_prompt: Optional[str] = None
    comments_prompt: Optional[str] = None
    allow_zero: bool = True
    weight: float = 1.0
    sort_order: int = 0


class ConfigSectionResponse(BaseModel):
    """Section config with nested criteria for frontend rendering."""
    code: str
    name: str
    description: Optional[str] = None
    sort_order: int = 0
    criteria: List[ConfigCriterionResponse] = []


class ScorecardFullResponse(BaseModel):
    """Complete scorecard response with all details."""
    request_id: int
    criteria_details: List[CriterionDetailResponse]
    section_summaries: List[SectionSummaryResponse]
    overall_assessment: OverallAssessmentResponse
    computed_at: datetime
    config_sections: List[ConfigSectionResponse] = []


# ============================================================================
# Legacy/Simple Config Response (for loading from JSON)
# ============================================================================

class SimpleSectionConfig(BaseModel):
    """Simple section config (matching SCORE_CRITERIA.json format)."""
    code: str
    name: str


class SimpleCriterionConfig(BaseModel):
    """Simple criterion config (matching SCORE_CRITERIA.json format)."""
    code: str
    section: str
    name: str
    description_prompt: Optional[str] = None
    comments_prompt: Optional[str] = None
    include_in_summary: bool = True
    allow_zero: bool = True
    weight: float = 1.0


class ScorecardJsonConfig(BaseModel):
    """Schema for SCORE_CRITERIA.json format."""
    sections: List[SimpleSectionConfig]
    criteria: List[SimpleCriterionConfig]


# ============================================================================
# Configuration Versioning Schemas
# ============================================================================

class ScorecardSectionSnapshotResponse(BaseModel):
    """Response schema for a section snapshot within a config version."""
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: int
    code: str
    name: str
    description: Optional[str] = None
    sort_order: int
    is_active: bool


class ScorecardCriterionSnapshotResponse(BaseModel):
    """Response schema for a criterion snapshot within a config version."""
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: int
    section_code: str
    code: str
    name: str
    description_prompt: Optional[str] = None
    comments_prompt: Optional[str] = None
    include_in_summary: bool
    allow_zero: bool
    weight: float
    sort_order: int
    is_active: bool


class ScorecardConfigVersionResponse(BaseModel):
    """Response schema for scorecard configuration version (summary)."""
    model_config = ConfigDict(from_attributes=True)

    version_id: int
    version_number: int
    version_name: Optional[str] = None
    description: Optional[str] = None
    published_by_name: Optional[str] = None
    published_at: datetime
    is_active: bool
    sections_count: int
    criteria_count: int
    scorecards_count: int
    created_at: datetime
    # True if config changed since this version was published
    has_unpublished_changes: bool = False


class ScorecardConfigVersionDetailResponse(ScorecardConfigVersionResponse):
    """Detailed response schema including all snapshots."""
    section_snapshots: List[ScorecardSectionSnapshotResponse] = []
    criterion_snapshots: List[ScorecardCriterionSnapshotResponse] = []


class PublishScorecardVersionRequest(BaseModel):
    """Request schema for publishing a new scorecard configuration version."""
    version_name: Optional[str] = Field(
        None, max_length=200, description="Optional display name for this version")
    description: Optional[str] = Field(
        None, description="Changelog or notes for this version")
