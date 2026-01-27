# Validation Scorecard Implementation Plan

This document outlines the TDD-driven implementation plan for adding validation scorecard capability to the MRM inventory system.

---

## 1. Overview

The validation scorecard allows validators to:
1. Rate individual criteria defined in `SCORE_CRITERIA.json`
2. Automatically compute section-level summary ratings
3. Automatically compute an Overall Assessment rating

All criteria and sections are **user-configurable** via the existing taxonomy system.

---

## 2. Taxonomy / Data Model Design

### 2.1 Scorecard Configuration Taxonomy

Import `SCORE_CRITERIA.json` into the taxonomy system using two new taxonomies:

#### Taxonomy: "Scorecard Section"
| value_id | code | label | description | sort_order |
|----------|------|-------|-------------|------------|
| auto | SEC_1 | Evaluation of Conceptual Soundness | Section 1 | 1 |
| auto | SEC_2 | Ongoing Monitoring/Benchmarking | Section 2 | 2 |
| auto | SEC_3 | Outcome Analysis | Section 3 | 3 |

#### Taxonomy: "Scorecard Criterion"
Each criterion from SCORE_CRITERIA.json becomes a taxonomy value with extended metadata stored in a JSON `metadata` column or dedicated table.

| value_id | code | label | description | sort_order | metadata (JSON) |
|----------|------|-------|-------------|------------|-----------------|
| auto | CRIT_1_1 | Model Development Documentation | (description_prompt) | 1 | `{"section_code": "SEC_1", "comments_prompt": "...", "include_in_summary": true, "allow_zero": true, "weight": 1}` |
| auto | CRIT_1_2 | Model Development Data | ... | 2 | `{"section_code": "SEC_1", ...}` |
| ... | ... | ... | ... | ... | ... |

**Alternative (Recommended): Dedicated ScorecardCriterion Table**

Rather than overloading TaxonomyValue with metadata, create a dedicated configuration table:

```python
class ScorecardSection(Base):
    """Scorecard sections - user configurable."""
    __tablename__ = "scorecard_sections"

    section_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # "1", "2", "3"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

class ScorecardCriterion(Base):
    """Scorecard criteria - user configurable."""
    __tablename__ = "scorecard_criteria"

    criterion_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # "1.1", "2.1"
    section_id: Mapped[int] = mapped_column(Integer, ForeignKey("scorecard_sections.section_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    comments_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    include_in_summary: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_zero: Mapped[bool] = mapped_column(Boolean, default=True)
    weight: Mapped[float] = mapped_column(Numeric(5, 2), default=1.0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    section = relationship("ScorecardSection", backref="criteria")
```

### 2.2 Scorecard Rating Storage

Store validator ratings for each criterion:

```python
class ValidationScorecardRating(Base):
    """Per-criterion ratings entered by validators."""
    __tablename__ = "validation_scorecard_ratings"

    rating_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    outcome_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("validation_outcomes.outcome_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    criterion_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Criterion code (e.g., '1.1', '2.3') - keyed by code for resilience"
    )
    rating: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Rating string: Green, Green-, Yellow+, Yellow, Yellow-, Red, or NULL for Unrated"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Validator's description response"
    )
    comments: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Validator's comments"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    outcome = relationship("ValidationOutcome", back_populates="scorecard_ratings")

    __table_args__ = (
        UniqueConstraint('outcome_id', 'criterion_code', name='uq_outcome_criterion'),
    )
```

### 2.3 Computed Scorecard Result Storage

Store computed section summaries and overall assessment:

```python
class ValidationScorecardResult(Base):
    """Computed scorecard results - section summaries and overall assessment."""
    __tablename__ = "validation_scorecard_results"

    result_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    outcome_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("validation_outcomes.outcome_id", ondelete="CASCADE"),
        nullable=False,
        unique=True  # ONE result per outcome
    )

    # Overall Assessment
    overall_numeric_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-6
    overall_rating: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Section Summaries (JSON for flexibility)
    section_summaries: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON object with per-section summaries"
    )
    # Example: {
    #   "1": {"numeric_score": 4, "rating": "Yellow+", "criteria_count": 5, "rated_count": 4},
    #   "2": {"numeric_score": 5, "rating": "Green-", "criteria_count": 3, "rated_count": 3},
    #   "3": {"numeric_score": 0, "rating": null, "criteria_count": 6, "rated_count": 0}
    # }

    computed_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # Relationships
    outcome = relationship("ValidationOutcome", back_populates="scorecard_result")
```

---

## 3. Rating ↔ Score Mapping

### 3.1 Fixed Mapping Table

| Rating String | Numeric Score |
|---------------|---------------|
| `Green` | 6 |
| `Green-` | 5 |
| `Yellow+` | 4 |
| `Yellow` | 3 |
| `Yellow-` | 2 |
| `Red` | 1 |
| `Unrated` / `NA` / `null` / `""` | 0 |

### 3.2 Helper Functions

```python
# Location: api/app/core/scorecard.py

from typing import Optional
from decimal import Decimal, ROUND_HALF_UP

RATING_TO_SCORE = {
    "Green": 6,
    "Green-": 5,
    "Yellow+": 4,
    "Yellow": 3,
    "Yellow-": 2,
    "Red": 1,
}

SCORE_TO_RATING = {
    6: "Green",
    5: "Green-",
    4: "Yellow+",
    3: "Yellow",
    2: "Yellow-",
    1: "Red",
    0: None,  # Unrated/NA
}

def rating_to_score(rating: Optional[str]) -> int:
    """
    Convert a rating string to its numeric score.

    Args:
        rating: Rating string (Green, Green-, Yellow+, Yellow, Yellow-, Red)
                or None/empty/"NA"/"Unrated" for unrated

    Returns:
        Integer score 0-6. Returns 0 for unrated/NA/invalid.
    """
    if rating is None or rating == "" or rating.upper() in ("NA", "UNRATED", "N/A"):
        return 0
    return RATING_TO_SCORE.get(rating, 0)


def score_to_rating(score: int) -> Optional[str]:
    """
    Convert a numeric score to its rating string.

    Args:
        score: Integer 0-6

    Returns:
        Rating string or None for score 0.

    Raises:
        ValueError: If score is not in range 0-6.
    """
    if score < 0 or score > 6:
        raise ValueError(f"Score must be between 0 and 6, got {score}")
    return SCORE_TO_RATING.get(score)


def round_half_up(value: float) -> int:
    """
    Round a float using conventional half-up rounding.

    Examples:
        3.5 -> 4
        3.49 -> 3
        3.51 -> 4
    """
    return int(Decimal(str(value)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
```

---

## 4. Section Summary Score Algorithm (Weighted)

```python
def compute_section_summary(
    section_code: str,
    criteria_ratings: dict[str, Optional[str]],
    criteria_config: list[dict]
) -> dict:
    """
    Compute weighted summary score for a single section.

    Args:
        section_code: Section code (e.g., "1", "2", "3")
        criteria_ratings: Map of criterion_code -> rating string
        criteria_config: List of criterion configs from taxonomy/SCORE_CRITERIA.json

    Returns:
        {
            "section_code": str,
            "section_name": str,
            "criteria_count": int,
            "rated_count": int,
            "unrated_count": int,
            "numeric_score": int,  # 0-6
            "rating": Optional[str]
        }
    """
    # 1. Get all criteria for this section
    section_criteria = [c for c in criteria_config if c["section"] == section_code]

    # 2. Collect non-zero scores with weights
    weighted_scores = []  # List of (score, weight) tuples
    for criterion in section_criteria:
        code = criterion["code"]
        weight = criterion.get("weight", 1.0)
        rating = criteria_ratings.get(code)
        score = rating_to_score(rating)
        if score > 0:
            weighted_scores.append((score, weight))

    # 3. Compute summary
    criteria_count = len(section_criteria)
    rated_count = len(weighted_scores)
    unrated_count = criteria_count - rated_count

    if rated_count == 0:
        # All unrated/NA
        return {
            "section_code": section_code,
            "section_name": get_section_name(section_code, criteria_config),
            "criteria_count": criteria_count,
            "rated_count": 0,
            "unrated_count": unrated_count,
            "numeric_score": 0,
            "rating": None
        }

    # 4. Compute weighted mean and round
    total_weighted_score = sum(score * weight for score, weight in weighted_scores)
    total_weight = sum(weight for _, weight in weighted_scores)
    weighted_mean = total_weighted_score / total_weight
    rounded_score = round_half_up(weighted_mean)

    return {
        "section_code": section_code,
        "section_name": get_section_name(section_code, criteria_config),
        "criteria_count": criteria_count,
        "rated_count": rated_count,
        "unrated_count": unrated_count,
        "numeric_score": rounded_score,
        "rating": score_to_rating(rounded_score)
    }
```

---

## 5. Overall Assessment Algorithm

```python
def compute_overall_assessment(
    section_summaries: list[dict]
) -> dict:
    """
    Compute Overall Assessment from section summaries.

    Args:
        section_summaries: List of section summary dicts from compute_section_summary

    Returns:
        {
            "numeric_score": int,  # 0-6
            "rating": Optional[str],
            "sections_count": int,
            "rated_sections_count": int
        }
    """
    # 1. Collect non-zero section scores
    section_scores = [s["numeric_score"] for s in section_summaries if s["numeric_score"] > 0]

    sections_count = len(section_summaries)
    rated_sections_count = len(section_scores)

    if rated_sections_count == 0:
        # All sections unrated
        return {
            "numeric_score": 0,
            "rating": None,
            "sections_count": sections_count,
            "rated_sections_count": 0
        }

    # 2. Compute mean and round
    mean_score = sum(section_scores) / len(section_scores)
    rounded_score = round_half_up(mean_score)

    return {
        "numeric_score": rounded_score,
        "rating": score_to_rating(rounded_score),
        "sections_count": sections_count,
        "rated_sections_count": rated_sections_count
    }
```

---

## 6. Public API: `compute_scorecard`

```python
def compute_scorecard(
    criteria_ratings: dict[str, Optional[str]],
    taxonomy_config: dict
) -> dict:
    """
    Main entry point for computing a complete validation scorecard.

    Args:
        criteria_ratings: Map of criterion_code -> rating string
            Example: {"1.1": "Green", "1.2": "Yellow+", "2.1": None, ...}
        taxonomy_config: Parsed SCORE_CRITERIA.json or equivalent from taxonomy
            Must have "sections" and "criteria" keys

    Returns:
        {
            "criteria_details": [
                {
                    "code": "1.1",
                    "name": "Model Development Documentation",
                    "section_code": "1",
                    "rating": "Green",
                    "numeric_score": 6
                },
                ...
            ],
            "section_summaries": [
                {
                    "section_code": "1",
                    "section_name": "Evaluation of Conceptual Soundness",
                    "criteria_count": 5,
                    "rated_count": 4,
                    "unrated_count": 1,
                    "numeric_score": 5,
                    "rating": "Green-"
                },
                ...
            ],
            "overall_assessment": {
                "numeric_score": 4,
                "rating": "Yellow+",
                "sections_count": 3,
                "rated_sections_count": 2
            }
        }

    Edge Cases:
        - Missing ratings for configured criteria: treated as score 0/NA
        - Ratings for unknown criteria: ignored (not included in output)
        - Invalid rating strings: treated as score 0/NA (with optional warning)
    """
```

---

## 7. Rating Capture Approach

### 7.1 API Endpoints

Add to `/validation-workflow/`:

```
POST   /requests/{request_id}/outcome/scorecard
       Create or replace all criterion ratings for an outcome
       Body: { "ratings": [{"criterion_code": "1.1", "rating": "Green", "description": "...", "comments": "..."}, ...] }

GET    /requests/{request_id}/outcome/scorecard
       Get scorecard ratings and computed results

PATCH  /requests/{request_id}/outcome/scorecard/ratings/{criterion_code}
       Update a single criterion rating

GET    /scorecard/config
       Get current scorecard configuration (sections + criteria)
```

### 7.2 Pydantic Schemas

```python
# api/app/schemas/scorecard.py

class CriterionRatingCreate(BaseModel):
    criterion_code: str
    rating: Optional[str] = None  # Green, Green-, Yellow+, Yellow, Yellow-, Red, or None
    description: Optional[str] = None
    comments: Optional[str] = None

class ScorecardCreate(BaseModel):
    ratings: list[CriterionRatingCreate]

class CriterionRatingResponse(BaseModel):
    criterion_code: str
    criterion_name: str
    section_code: str
    rating: Optional[str]
    numeric_score: int
    description: Optional[str]
    comments: Optional[str]

class SectionSummaryResponse(BaseModel):
    section_code: str
    section_name: str
    criteria_count: int
    rated_count: int
    unrated_count: int
    numeric_score: int
    rating: Optional[str]

class OverallAssessmentResponse(BaseModel):
    numeric_score: int
    rating: Optional[str]
    sections_count: int
    rated_sections_count: int

class ScorecardResponse(BaseModel):
    outcome_id: int
    criteria_details: list[CriterionRatingResponse]
    section_summaries: list[SectionSummaryResponse]
    overall_assessment: OverallAssessmentResponse
    computed_at: datetime
```

### 7.3 Frontend Integration

- Add "Scorecard" tab to Validation Request detail page
- Display criteria grouped by section with rating dropdowns
- Show computed section summaries and overall assessment
- Auto-recompute on rating changes
- Disable editing when status >= PENDING_APPROVAL

---

## 8. TDD Test Plan

### 8.1 Unit Tests: Rating ↔ Score Mapping

**File:** `api/tests/test_scorecard_mapping.py`

```python
# Test rating_to_score
def test_rating_to_score_green():
    assert rating_to_score("Green") == 6

def test_rating_to_score_green_minus():
    assert rating_to_score("Green-") == 5

def test_rating_to_score_yellow_plus():
    assert rating_to_score("Yellow+") == 4

def test_rating_to_score_yellow():
    assert rating_to_score("Yellow") == 3

def test_rating_to_score_yellow_minus():
    assert rating_to_score("Yellow-") == 2

def test_rating_to_score_red():
    assert rating_to_score("Red") == 1

def test_rating_to_score_none():
    assert rating_to_score(None) == 0

def test_rating_to_score_empty_string():
    assert rating_to_score("") == 0

def test_rating_to_score_na():
    assert rating_to_score("NA") == 0

def test_rating_to_score_unrated():
    assert rating_to_score("Unrated") == 0

def test_rating_to_score_invalid():
    assert rating_to_score("InvalidRating") == 0

# Test score_to_rating
def test_score_to_rating_6():
    assert score_to_rating(6) == "Green"

def test_score_to_rating_5():
    assert score_to_rating(5) == "Green-"

def test_score_to_rating_4():
    assert score_to_rating(4) == "Yellow+"

def test_score_to_rating_3():
    assert score_to_rating(3) == "Yellow"

def test_score_to_rating_2():
    assert score_to_rating(2) == "Yellow-"

def test_score_to_rating_1():
    assert score_to_rating(1) == "Red"

def test_score_to_rating_0():
    assert score_to_rating(0) is None

def test_score_to_rating_invalid_negative():
    with pytest.raises(ValueError):
        score_to_rating(-1)

def test_score_to_rating_invalid_high():
    with pytest.raises(ValueError):
        score_to_rating(7)

# Test round_half_up
def test_round_half_up_3_5():
    assert round_half_up(3.5) == 4

def test_round_half_up_3_49():
    assert round_half_up(3.49) == 3

def test_round_half_up_3_51():
    assert round_half_up(3.51) == 4

def test_round_half_up_2_5():
    assert round_half_up(2.5) == 3

def test_round_half_up_integer():
    assert round_half_up(4.0) == 4
```

### 8.2 Unit Tests: Section Summary Computation

**File:** `api/tests/test_scorecard_section.py`

```python
SAMPLE_CONFIG = {
    "sections": [
        {"code": "1", "name": "Evaluation of Conceptual Soundness"},
        {"code": "2", "name": "Ongoing Monitoring/Benchmarking"},
        {"code": "3", "name": "Outcome Analysis"}
    ],
    "criteria": [
        {"code": "1.1", "section": "1", "name": "Model Development Documentation"},
        {"code": "1.2", "section": "1", "name": "Model Development Data"},
        {"code": "1.3", "section": "1", "name": "Model Methodology"},
        {"code": "2.1", "section": "2", "name": "Benchmarking"},
        {"code": "2.2", "section": "2", "name": "Process Verification"},
        {"code": "3.1", "section": "3", "name": "Backtesting"},
        {"code": "3.2", "section": "3", "name": "Stress Testing"}
    ]
}

def test_section_summary_all_green():
    """Section with all Green ratings -> score 6."""
    ratings = {"1.1": "Green", "1.2": "Green", "1.3": "Green"}
    result = compute_section_summary("1", ratings, SAMPLE_CONFIG["criteria"])
    assert result["numeric_score"] == 6
    assert result["rating"] == "Green"
    assert result["rated_count"] == 3

def test_section_summary_mixed_ratings():
    """Section with Green(6), Yellow+(4), Yellow(3) -> mean 4.33 -> rounds to 4 -> Yellow+."""
    ratings = {"1.1": "Green", "1.2": "Yellow+", "1.3": "Yellow"}
    result = compute_section_summary("1", ratings, SAMPLE_CONFIG["criteria"])
    # Mean: (6 + 4 + 3) / 3 = 4.33... -> rounds to 4
    assert result["numeric_score"] == 4
    assert result["rating"] == "Yellow+"

def test_section_summary_with_na():
    """Section with some NA ratings - excluded from average."""
    ratings = {"1.1": "Green", "1.2": None, "1.3": "Yellow-"}
    result = compute_section_summary("1", ratings, SAMPLE_CONFIG["criteria"])
    # Only Green(6) and Yellow-(2) counted: (6 + 2) / 2 = 4
    assert result["numeric_score"] == 4
    assert result["rating"] == "Yellow+"
    assert result["rated_count"] == 2
    assert result["unrated_count"] == 1

def test_section_summary_all_na():
    """Section with all NA ratings -> score 0."""
    ratings = {"1.1": None, "1.2": "NA", "1.3": ""}
    result = compute_section_summary("1", ratings, SAMPLE_CONFIG["criteria"])
    assert result["numeric_score"] == 0
    assert result["rating"] is None
    assert result["rated_count"] == 0

def test_section_summary_rounding_half_up():
    """Test half-up rounding: mean 3.5 -> 4."""
    ratings = {"1.1": "Yellow+", "1.2": "Yellow"}  # (4 + 3) / 2 = 3.5 -> 4
    # Need to adjust config for 2-criterion section
    config = [
        {"code": "1.1", "section": "1", "name": "C1", "weight": 1.0},
        {"code": "1.2", "section": "1", "name": "C2", "weight": 1.0}
    ]
    result = compute_section_summary("1", ratings, config)
    assert result["numeric_score"] == 4
    assert result["rating"] == "Yellow+"

def test_section_summary_weighted():
    """Test weighted average: weight 2 criterion counts double."""
    config = [
        {"code": "1.1", "section": "1", "name": "C1", "weight": 2.0},  # Green (6) * 2 = 12
        {"code": "1.2", "section": "1", "name": "C2", "weight": 1.0}   # Yellow (3) * 1 = 3
    ]
    ratings = {"1.1": "Green", "1.2": "Yellow"}
    # Weighted mean: (6*2 + 3*1) / (2+1) = 15/3 = 5.0 -> Green-
    result = compute_section_summary("1", ratings, config)
    assert result["numeric_score"] == 5
    assert result["rating"] == "Green-"

def test_section_summary_weighted_with_na():
    """Weighted average excludes NA criteria entirely (weight not counted)."""
    config = [
        {"code": "1.1", "section": "1", "name": "C1", "weight": 2.0},  # Green (6) * 2 = 12
        {"code": "1.2", "section": "1", "name": "C2", "weight": 3.0},  # NA - excluded
        {"code": "1.3", "section": "1", "name": "C3", "weight": 1.0}   # Yellow (3) * 1 = 3
    ]
    ratings = {"1.1": "Green", "1.2": None, "1.3": "Yellow"}
    # Weighted mean: (6*2 + 3*1) / (2+1) = 15/3 = 5.0 -> Green-
    result = compute_section_summary("1", ratings, config)
    assert result["numeric_score"] == 5
    assert result["rating"] == "Green-"
    assert result["rated_count"] == 2
    assert result["unrated_count"] == 1

def test_section_summary_missing_criterion():
    """Criterion in config but not in ratings -> treated as NA."""
    ratings = {"1.1": "Green"}  # 1.2, 1.3 missing
    result = compute_section_summary("1", ratings, SAMPLE_CONFIG["criteria"])
    # Only Green(6) counted
    assert result["numeric_score"] == 6
    assert result["rating"] == "Green"
    assert result["rated_count"] == 1
    assert result["unrated_count"] == 2
```

### 8.3 Unit Tests: Overall Assessment Computation

**File:** `api/tests/test_scorecard_overall.py`

```python
def test_overall_all_sections_rated():
    """All sections have non-zero scores."""
    section_summaries = [
        {"section_code": "1", "numeric_score": 5, "rating": "Green-"},
        {"section_code": "2", "numeric_score": 4, "rating": "Yellow+"},
        {"section_code": "3", "numeric_score": 3, "rating": "Yellow"}
    ]
    result = compute_overall_assessment(section_summaries)
    # Mean: (5 + 4 + 3) / 3 = 4
    assert result["numeric_score"] == 4
    assert result["rating"] == "Yellow+"
    assert result["rated_sections_count"] == 3

def test_overall_one_section_na():
    """One section is NA - excluded from average."""
    section_summaries = [
        {"section_code": "1", "numeric_score": 6, "rating": "Green"},
        {"section_code": "2", "numeric_score": 0, "rating": None},  # NA
        {"section_code": "3", "numeric_score": 4, "rating": "Yellow+"}
    ]
    result = compute_overall_assessment(section_summaries)
    # Only sections 1 and 3: (6 + 4) / 2 = 5
    assert result["numeric_score"] == 5
    assert result["rating"] == "Green-"
    assert result["rated_sections_count"] == 2

def test_overall_only_one_section_rated():
    """Only one section has ratings."""
    section_summaries = [
        {"section_code": "1", "numeric_score": 3, "rating": "Yellow"},
        {"section_code": "2", "numeric_score": 0, "rating": None},
        {"section_code": "3", "numeric_score": 0, "rating": None}
    ]
    result = compute_overall_assessment(section_summaries)
    assert result["numeric_score"] == 3
    assert result["rating"] == "Yellow"
    assert result["rated_sections_count"] == 1

def test_overall_all_sections_na():
    """All sections are NA -> overall is NA."""
    section_summaries = [
        {"section_code": "1", "numeric_score": 0, "rating": None},
        {"section_code": "2", "numeric_score": 0, "rating": None},
        {"section_code": "3", "numeric_score": 0, "rating": None}
    ]
    result = compute_overall_assessment(section_summaries)
    assert result["numeric_score"] == 0
    assert result["rating"] is None
    assert result["rated_sections_count"] == 0

def test_overall_rounding_half_up():
    """Test half-up rounding in overall: (5 + 4) / 2 = 4.5 -> 5."""
    section_summaries = [
        {"section_code": "1", "numeric_score": 5, "rating": "Green-"},
        {"section_code": "2", "numeric_score": 4, "rating": "Yellow+"}
    ]
    result = compute_overall_assessment(section_summaries)
    assert result["numeric_score"] == 5
    assert result["rating"] == "Green-"
```

### 8.4 Integration Tests: compute_scorecard

**File:** `api/tests/test_scorecard_integration.py`

```python
def test_compute_scorecard_full():
    """Full scorecard computation with mixed ratings."""
    config = load_score_criteria_json()  # Load actual SCORE_CRITERIA.json
    ratings = {
        "1.1": "Green",
        "1.2": "Green-",
        "1.3": "Yellow+",
        "1.4": "Yellow",
        "1.5": None,  # NA
        "2.1": "Green",
        "2.2": "Green",
        "2.3": "Yellow+",
        "3.1": "Yellow",
        "3.2": "Yellow-",
        "3.3": "Red",
        "3.4": None,
        "3.5": None,
        "3.6": "Yellow"
    }
    result = compute_scorecard(ratings, config)

    # Verify structure
    assert "criteria_details" in result
    assert "section_summaries" in result
    assert "overall_assessment" in result

    # Verify section 1: (6+5+4+3)/4 = 4.5 -> 5
    sec1 = next(s for s in result["section_summaries"] if s["section_code"] == "1")
    assert sec1["numeric_score"] == 5
    assert sec1["rating"] == "Green-"

def test_compute_scorecard_unknown_criterion():
    """Unknown criterion codes are ignored."""
    config = {"sections": [{"code": "1", "name": "S1"}], "criteria": [{"code": "1.1", "section": "1", "name": "C1"}]}
    ratings = {"1.1": "Green", "9.9": "Red"}  # 9.9 doesn't exist
    result = compute_scorecard(ratings, config)

    # Only 1.1 should be in details
    assert len(result["criteria_details"]) == 1
    assert result["criteria_details"][0]["criterion_code"] == "1.1"

def test_compute_scorecard_empty_ratings():
    """Empty ratings dict -> all NA."""
    config = load_score_criteria_json()
    result = compute_scorecard({}, config)

    assert result["overall_assessment"]["numeric_score"] == 0
    assert result["overall_assessment"]["rating"] is None
```

### 8.5 API Endpoint Tests

**File:** `api/tests/test_scorecard_api.py`

```python
def test_get_scorecard_config(client, admin_token):
    """GET /scorecard/config returns sections and criteria."""
    response = client.get("/scorecard/config", headers=auth_header(admin_token))
    assert response.status_code == 200
    data = response.json()
    assert "sections" in data
    assert "criteria" in data
    assert len(data["sections"]) == 3
    assert len(data["criteria"]) == 14

def test_create_scorecard_ratings(client, admin_token, validation_with_outcome):
    """POST /requests/{id}/outcome/scorecard creates ratings."""
    response = client.post(
        f"/validation-workflow/requests/{validation_with_outcome}/outcome/scorecard",
        headers=auth_header(admin_token),
        json={
            "ratings": [
                {"criterion_code": "1.1", "rating": "Green", "comments": "Well documented"},
                {"criterion_code": "1.2", "rating": "Yellow+"}
            ]
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["overall_assessment"]["numeric_score"] > 0

def test_create_scorecard_requires_outcome(client, admin_token, validation_without_outcome):
    """Cannot create scorecard without an outcome first."""
    response = client.post(
        f"/validation-workflow/requests/{validation_without_outcome}/outcome/scorecard",
        headers=auth_header(admin_token),
        json={"ratings": [{"criterion_code": "1.1", "rating": "Green"}]}
    )
    assert response.status_code == 400
    assert "outcome" in response.json()["detail"].lower()

def test_get_scorecard_ratings(client, admin_token, validation_with_scorecard):
    """GET /requests/{id}/outcome/scorecard returns computed results."""
    response = client.get(
        f"/validation-workflow/requests/{validation_with_scorecard}/outcome/scorecard",
        headers=auth_header(admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    assert "criteria_details" in data
    assert "section_summaries" in data
    assert "overall_assessment" in data
```

---

## 9. Implementation Phases

### Phase 1: Core Scoring Logic (TDD)
1. Create `api/app/core/scorecard.py` with helper functions
2. Write tests in `api/tests/test_scorecard_*.py`
3. Implement functions to pass tests

### Phase 2: Configuration/Taxonomy
1. Create migration for `scorecard_sections` and `scorecard_criteria` tables
2. Load SCORE_CRITERIA.json into database during seed
3. Add API endpoint `GET /scorecard/config`

### Phase 3: Rating Storage
1. Create migration for `validation_scorecard_ratings` and `validation_scorecard_results` tables
2. Add relationships to ValidationOutcome model
3. Create Pydantic schemas

### Phase 4: API Endpoints
1. Implement `POST/GET /requests/{id}/outcome/scorecard`
2. Implement `PATCH /requests/{id}/outcome/scorecard/ratings/{code}`
3. Add integration tests

### Phase 5: Frontend
1. Add Scorecard tab to ValidationRequestDetailPage
2. Implement rating form grouped by section
3. Display computed summaries
4. Handle edit permissions based on status

---

## 10. Design Decisions (Clarified)

1. **Audit Logging:** Log at scorecard level when saved (not individual criterion changes). A single audit log entry captures the entire scorecard save operation.

2. **Rating Validation:** Use pick lists (dropdowns) in UI to prevent invalid input. Backend accepts only valid rating strings from the enum.

3. **Taxonomy Editability:** Scorecard sections/criteria will be editable via the existing Taxonomy management page.

4. **Weight Support:** Implement weighted averages now. The `weight` field from SCORE_CRITERIA.json will be used in calculations.

5. **When to Compute:** Recompute immediately on every rating change. Frontend shows live updates.

6. **Historical Versions:** Version the configuration. When a scorecard is created, snapshot the configuration state so historical scorecards remain accurate even if criteria change.

7. **Required Ratings:** Allow flexibility - no blocking on status progression for unrated criteria.

8. **UI Design:**
   - Summary card at top showing overall assessment + section ratings
   - Progress indicator (e.g., "8/14 criteria rated")
   - Collapsible sections
   - **Explicit N/A selection required** - unrated criteria must be explicitly marked N/A (not left blank) to ensure progress indicator accuracy

---

## Appendix: SCORE_CRITERIA.json Summary

**Sections:**
| Code | Name | Criteria Count |
|------|------|----------------|
| 1 | Evaluation of Conceptual Soundness | 5 (1.1-1.5) |
| 2 | Ongoing Monitoring/Benchmarking | 3 (2.1-2.3) |
| 3 | Outcome Analysis | 6 (3.1-3.6) |

**Total Criteria:** 14

**Common Fields:**
- `code`: Unique identifier (e.g., "1.1")
- `section`: Parent section code
- `name`: Display name
- `description_prompt`: Guidance for validator's description
- `comments_prompt`: Guidance for validator's comments
- `include_in_summary`: Whether to include in summary (all true)
- `allow_zero`: Whether NA is allowed (all true)
- `weight`: Weight for averaging (all 1.0)
