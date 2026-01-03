"""Validation Scorecard Core Logic.

This module provides the core algorithms for computing validation scorecard ratings,
section summaries, and overall assessments.

Rating Scale:
    Green   -> 6 (best)
    Green-  -> 5
    Yellow+ -> 4
    Yellow  -> 3
    Yellow- -> 2
    Red     -> 1 (worst)
    NA/Unrated -> 0 (excluded from calculations)
"""

import json
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


# ============================================================================
# Rating ↔ Score Mapping
# ============================================================================

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

# NA representations (case-insensitive)
NA_VALUES = {"na", "n/a", "unrated", ""}


def rating_to_score(rating: Optional[str]) -> int:
    """
    Convert a rating string to its numeric score.

    Args:
        rating: Rating string (Green, Green-, Yellow+, Yellow, Yellow-, Red)
                or None/empty/"NA"/"Unrated"/"N/A" for unrated

    Returns:
        Integer score 0-6. Returns 0 for unrated/NA/invalid ratings.

    Examples:
        >>> rating_to_score("Green")
        6
        >>> rating_to_score("Yellow")
        3
        >>> rating_to_score(None)
        0
        >>> rating_to_score("NA")
        0
    """
    if rating is None:
        return 0
    if rating.lower() in NA_VALUES:
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

    Examples:
        >>> score_to_rating(6)
        'Green'
        >>> score_to_rating(3)
        'Yellow'
        >>> score_to_rating(0)
        None
    """
    if score < 0 or score > 6:
        raise ValueError(f"Score must be between 0 and 6, got {score}")
    return SCORE_TO_RATING.get(score)


def round_half_up(value: float) -> int:
    """
    Round a float using conventional half-up rounding.

    Half-up rounding: 0.5 rounds away from zero (up for positive numbers).

    Args:
        value: Float to round

    Returns:
        Rounded integer

    Examples:
        >>> round_half_up(3.5)
        4
        >>> round_half_up(3.49)
        3
        >>> round_half_up(2.5)
        3
    """
    return int(Decimal(str(value)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


# ============================================================================
# Section Summary Computation
# ============================================================================

def _get_section_name(section_code: str, config: dict) -> str:
    """Get the display name for a section code from config."""
    for section in config.get("sections", []):
        if section["code"] == section_code:
            return section["name"]
    return f"Section {section_code}"


def _get_section_description(section_code: str, config: dict) -> Optional[str]:
    """Get the description for a section code from config."""
    for section in config.get("sections", []):
        if section["code"] == section_code:
            return section.get("description")
    return None


def compute_section_summary(
    section_code: str,
    criteria_ratings: dict[str, Optional[str]],
    config: dict
) -> dict:
    """
    Compute weighted summary score for a single section.

    Algorithm:
    1. Get all criteria for this section from config
    2. For each criterion, convert rating to score (NA/missing = 0)
    3. Exclude criteria with score 0 from calculation
    4. Compute weighted mean of non-zero scores
    5. Round using half-up rounding
    6. Convert back to rating string

    Args:
        section_code: Section code (e.g., "1", "2", "3")
        criteria_ratings: Map of criterion_code -> rating string
        config: Parsed scorecard configuration with "sections" and "criteria" keys

    Returns:
        Dictionary with:
            - section_code: str
            - section_name: str
            - criteria_count: int (total criteria in section)
            - rated_count: int (criteria with non-zero scores)
            - unrated_count: int (criteria with score 0)
            - numeric_score: int (0-6)
            - rating: Optional[str] (None if all unrated)
    """
    # Get all criteria for this section
    criteria = config.get("criteria", [])
    section_criteria = [c for c in criteria if c.get(
        "section") == section_code]

    criteria_count = len(section_criteria)

    # Collect non-zero scores with weights
    weighted_scores = []  # List of (score, weight) tuples
    for criterion in section_criteria:
        code = criterion["code"]
        weight = criterion.get("weight", 1.0)
        rating = criteria_ratings.get(code)
        score = rating_to_score(rating)
        if score > 0:
            weighted_scores.append((score, weight))

    rated_count = len(weighted_scores)
    unrated_count = criteria_count - rated_count

    if rated_count == 0:
        # All unrated/NA
        return {
            "section_code": section_code,
            "section_name": _get_section_name(section_code, config),
            "description": _get_section_description(section_code, config),
            "criteria_count": criteria_count,
            "rated_count": 0,
            "unrated_count": unrated_count,
            "numeric_score": 0,
            "rating": None
        }

    # Compute weighted mean
    total_weighted_score = sum(
        score * weight for score, weight in weighted_scores)
    total_weight = sum(weight for _, weight in weighted_scores)
    weighted_mean = total_weighted_score / total_weight

    # Round and convert to rating
    rounded_score = round_half_up(weighted_mean)

    return {
        "section_code": section_code,
        "section_name": _get_section_name(section_code, config),
        "description": _get_section_description(section_code, config),
        "criteria_count": criteria_count,
        "rated_count": rated_count,
        "unrated_count": unrated_count,
        "numeric_score": rounded_score,
        "rating": score_to_rating(rounded_score)
    }


# ============================================================================
# Overall Assessment Computation
# ============================================================================

def compute_overall_assessment(section_summaries: list[dict]) -> dict:
    """
    Compute Overall Assessment from section summaries.

    Algorithm:
    1. Collect all non-zero section summary scores
    2. Exclude sections with score 0 (NA)
    3. Compute arithmetic mean of non-zero section scores
    4. Round using half-up rounding
    5. Convert to rating string

    Args:
        section_summaries: List of section summary dicts from compute_section_summary

    Returns:
        Dictionary with:
            - numeric_score: int (0-6)
            - rating: Optional[str] (None if all sections are NA)
            - sections_count: int (total sections)
            - rated_sections_count: int (sections with non-zero scores)
    """
    sections_count = len(section_summaries)

    # Collect non-zero section scores
    section_scores = [
        s["numeric_score"]
        for s in section_summaries
        if s["numeric_score"] > 0
    ]

    rated_sections_count = len(section_scores)

    if rated_sections_count == 0:
        # All sections unrated
        return {
            "numeric_score": 0,
            "rating": None,
            "sections_count": sections_count,
            "rated_sections_count": 0
        }

    # Compute mean and round
    mean_score = sum(section_scores) / len(section_scores)
    rounded_score = round_half_up(mean_score)

    return {
        "numeric_score": rounded_score,
        "rating": score_to_rating(rounded_score),
        "sections_count": sections_count,
        "rated_sections_count": rated_sections_count
    }


# ============================================================================
# Full Scorecard Computation
# ============================================================================

def compute_scorecard(
    criteria_ratings: dict[str, Optional[str]],
    config: dict
) -> dict:
    """
    Compute a complete validation scorecard.

    This is the main entry point for scorecard computation. It combines
    criteria ratings with configuration to produce section summaries
    and an overall assessment.

    Args:
        criteria_ratings: Map of criterion_code -> rating string
            Example: {"1.1": "Green", "1.2": "Yellow+", "2.1": None, ...}
        config: Parsed scorecard configuration with "sections" and "criteria" keys

    Returns:
        Dictionary with:
            - criteria_details: List of per-criterion information
            - section_summaries: List of section summary dicts
            - overall_assessment: Overall assessment dict

    Edge Cases:
        - Missing ratings for configured criteria: treated as score 0/NA
        - Ratings for unknown criteria: ignored (not included in output)
        - Invalid rating strings: treated as score 0/NA
    """
    # Build criteria details
    criteria_details = []
    for criterion in config.get("criteria", []):
        code = criterion["code"]
        rating = criteria_ratings.get(code)
        score = rating_to_score(rating)

        criteria_details.append({
            "criterion_code": code,
            "criterion_name": criterion["name"],
            "section_code": criterion["section"],
            "rating": rating,
            "numeric_score": score
        })

    # Compute section summaries
    section_codes = [s["code"] for s in config.get("sections", [])]
    section_summaries = [
        compute_section_summary(code, criteria_ratings, config)
        for code in section_codes
    ]

    # Compute overall assessment
    overall_assessment = compute_overall_assessment(section_summaries)

    return {
        "criteria_details": criteria_details,
        "section_summaries": section_summaries,
        "overall_assessment": overall_assessment
    }


# ============================================================================
# Configuration Loading
# ============================================================================

def load_scorecard_config(config_path: Optional[Path | str] = None) -> dict:
    """
    Load scorecard configuration from JSON file.

    Args:
        config_path: Optional path to JSON file. If not provided,
                     uses SCORE_CRITERIA.json in repository root.

    Returns:
        Parsed configuration dictionary with "sections" and "criteria" keys.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        json.JSONDecodeError: If config file is invalid JSON.
    """
    if config_path is not None and not isinstance(config_path, Path):
        config_path = Path(config_path)

    if config_path is None:
        # Default to SCORE_CRITERIA.json in repo root (/app in Docker).
        # In local dev, this file may live one level above /api.
        app_root = Path(__file__).resolve().parents[2]
        candidate_paths = [
            app_root / "SCORE_CRITERIA.json",
            app_root.parent / "SCORE_CRITERIA.json",
        ]
        for candidate in candidate_paths:
            if candidate.exists() and candidate.stat().st_size > 0:
                config_path = candidate
                break
        else:
            config_path = candidate_paths[0]

    assert config_path is not None
    with open(config_path, "r") as f:
        return json.load(f)


# ============================================================================
# Valid Rating Values (for API validation)
# ============================================================================

VALID_RATINGS = ["Green", "Green-", "Yellow+",
                 "Yellow", "Yellow-", "Red", "N/A"]


def is_valid_rating(rating: Optional[str]) -> bool:
    """
    Check if a rating string is valid.

    Valid ratings are: Green, Green-, Yellow+, Yellow, Yellow-, Red, N/A, None

    Args:
        rating: Rating string to validate

    Returns:
        True if valid, False otherwise
    """
    if rating is None:
        return True
    return rating in VALID_RATINGS
