"""Tests for validation scorecard functionality.

TDD approach: These tests are written BEFORE the implementation.
Run with: python -m pytest tests/test_scorecard.py -v
"""
import pytest
from decimal import Decimal


# ============================================================================
# Section 1: Rating ↔ Score Mapping Tests
# ============================================================================

class TestRatingToScore:
    """Tests for rating_to_score function."""

    def test_green_returns_6(self):
        from app.core.scorecard import rating_to_score
        assert rating_to_score("Green") == 6

    def test_green_minus_returns_5(self):
        from app.core.scorecard import rating_to_score
        assert rating_to_score("Green-") == 5

    def test_yellow_plus_returns_4(self):
        from app.core.scorecard import rating_to_score
        assert rating_to_score("Yellow+") == 4

    def test_yellow_returns_3(self):
        from app.core.scorecard import rating_to_score
        assert rating_to_score("Yellow") == 3

    def test_yellow_minus_returns_2(self):
        from app.core.scorecard import rating_to_score
        assert rating_to_score("Yellow-") == 2

    def test_red_returns_1(self):
        from app.core.scorecard import rating_to_score
        assert rating_to_score("Red") == 1

    def test_none_returns_0(self):
        from app.core.scorecard import rating_to_score
        assert rating_to_score(None) == 0

    def test_empty_string_returns_0(self):
        from app.core.scorecard import rating_to_score
        assert rating_to_score("") == 0

    def test_na_returns_0(self):
        from app.core.scorecard import rating_to_score
        assert rating_to_score("NA") == 0
        assert rating_to_score("N/A") == 0

    def test_unrated_returns_0(self):
        from app.core.scorecard import rating_to_score
        assert rating_to_score("Unrated") == 0

    def test_invalid_rating_returns_0(self):
        from app.core.scorecard import rating_to_score
        assert rating_to_score("InvalidRating") == 0
        assert rating_to_score("Greeeen") == 0


class TestScoreToRating:
    """Tests for score_to_rating function."""

    def test_6_returns_green(self):
        from app.core.scorecard import score_to_rating
        assert score_to_rating(6) == "Green"

    def test_5_returns_green_minus(self):
        from app.core.scorecard import score_to_rating
        assert score_to_rating(5) == "Green-"

    def test_4_returns_yellow_plus(self):
        from app.core.scorecard import score_to_rating
        assert score_to_rating(4) == "Yellow+"

    def test_3_returns_yellow(self):
        from app.core.scorecard import score_to_rating
        assert score_to_rating(3) == "Yellow"

    def test_2_returns_yellow_minus(self):
        from app.core.scorecard import score_to_rating
        assert score_to_rating(2) == "Yellow-"

    def test_1_returns_red(self):
        from app.core.scorecard import score_to_rating
        assert score_to_rating(1) == "Red"

    def test_0_returns_none(self):
        from app.core.scorecard import score_to_rating
        assert score_to_rating(0) is None

    def test_negative_raises_error(self):
        from app.core.scorecard import score_to_rating
        with pytest.raises(ValueError):
            score_to_rating(-1)

    def test_above_6_raises_error(self):
        from app.core.scorecard import score_to_rating
        with pytest.raises(ValueError):
            score_to_rating(7)


class TestRoundHalfUp:
    """Tests for round_half_up function (conventional half-up rounding)."""

    def test_3_5_rounds_to_4(self):
        from app.core.scorecard import round_half_up
        assert round_half_up(3.5) == 4

    def test_3_49_rounds_to_3(self):
        from app.core.scorecard import round_half_up
        assert round_half_up(3.49) == 3

    def test_3_51_rounds_to_4(self):
        from app.core.scorecard import round_half_up
        assert round_half_up(3.51) == 4

    def test_2_5_rounds_to_3(self):
        from app.core.scorecard import round_half_up
        assert round_half_up(2.5) == 3

    def test_integer_unchanged(self):
        from app.core.scorecard import round_half_up
        assert round_half_up(4.0) == 4

    def test_4_5_rounds_to_5(self):
        from app.core.scorecard import round_half_up
        assert round_half_up(4.5) == 5

    def test_5_5_rounds_to_6(self):
        from app.core.scorecard import round_half_up
        assert round_half_up(5.5) == 6


# ============================================================================
# Section 2: Section Summary Computation Tests
# ============================================================================

# Sample configuration for tests
SAMPLE_CONFIG = {
    "sections": [
        {"code": "1", "name": "Evaluation of Conceptual Soundness"},
        {"code": "2", "name": "Ongoing Monitoring/Benchmarking"},
        {"code": "3", "name": "Outcome Analysis"}
    ],
    "criteria": [
        {"code": "1.1", "section": "1", "name": "Model Development Documentation", "weight": 1.0},
        {"code": "1.2", "section": "1", "name": "Model Development Data", "weight": 1.0},
        {"code": "1.3", "section": "1", "name": "Model Methodology", "weight": 1.0},
        {"code": "2.1", "section": "2", "name": "Benchmarking", "weight": 1.0},
        {"code": "2.2", "section": "2", "name": "Process Verification", "weight": 1.0},
        {"code": "3.1", "section": "3", "name": "Backtesting", "weight": 1.0},
        {"code": "3.2", "section": "3", "name": "Stress Testing", "weight": 1.0}
    ]
}


class TestComputeSectionSummary:
    """Tests for compute_section_summary function."""

    def test_all_green_returns_score_6(self):
        """Section with all Green ratings -> score 6."""
        from app.core.scorecard import compute_section_summary
        ratings = {"1.1": "Green", "1.2": "Green", "1.3": "Green"}
        result = compute_section_summary("1", ratings, SAMPLE_CONFIG)
        assert result["numeric_score"] == 6
        assert result["rating"] == "Green"
        assert result["rated_count"] == 3

    def test_mixed_ratings_computes_mean(self):
        """Section with Green(6), Yellow+(4), Yellow(3) -> mean 4.33 -> rounds to 4."""
        from app.core.scorecard import compute_section_summary
        ratings = {"1.1": "Green", "1.2": "Yellow+", "1.3": "Yellow"}
        result = compute_section_summary("1", ratings, SAMPLE_CONFIG)
        # Mean: (6 + 4 + 3) / 3 = 4.33... -> rounds to 4
        assert result["numeric_score"] == 4
        assert result["rating"] == "Yellow+"

    def test_na_excluded_from_average(self):
        """Section with some NA ratings - excluded from average."""
        from app.core.scorecard import compute_section_summary
        ratings = {"1.1": "Green", "1.2": None, "1.3": "Yellow-"}
        result = compute_section_summary("1", ratings, SAMPLE_CONFIG)
        # Only Green(6) and Yellow-(2) counted: (6 + 2) / 2 = 4
        assert result["numeric_score"] == 4
        assert result["rating"] == "Yellow+"
        assert result["rated_count"] == 2
        assert result["unrated_count"] == 1

    def test_all_na_returns_score_0(self):
        """Section with all NA ratings -> score 0."""
        from app.core.scorecard import compute_section_summary
        ratings = {"1.1": None, "1.2": "NA", "1.3": ""}
        result = compute_section_summary("1", ratings, SAMPLE_CONFIG)
        assert result["numeric_score"] == 0
        assert result["rating"] is None
        assert result["rated_count"] == 0

    def test_rounding_half_up_3_5_to_4(self):
        """Test half-up rounding: mean 3.5 -> 4."""
        from app.core.scorecard import compute_section_summary
        # Yellow+(4) + Yellow(3) = 7, 7/2 = 3.5 -> 4
        config = {
            "sections": [{"code": "1", "name": "Test"}],
            "criteria": [
                {"code": "1.1", "section": "1", "name": "C1", "weight": 1.0},
                {"code": "1.2", "section": "1", "name": "C2", "weight": 1.0}
            ]
        }
        ratings = {"1.1": "Yellow+", "1.2": "Yellow"}
        result = compute_section_summary("1", ratings, config)
        assert result["numeric_score"] == 4
        assert result["rating"] == "Yellow+"

    def test_weighted_average(self):
        """Test weighted average: weight 2 criterion counts double."""
        from app.core.scorecard import compute_section_summary
        config = {
            "sections": [{"code": "1", "name": "Test"}],
            "criteria": [
                {"code": "1.1", "section": "1", "name": "C1", "weight": 2.0},  # Green(6) * 2 = 12
                {"code": "1.2", "section": "1", "name": "C2", "weight": 1.0}   # Yellow(3) * 1 = 3
            ]
        }
        ratings = {"1.1": "Green", "1.2": "Yellow"}
        # Weighted mean: (6*2 + 3*1) / (2+1) = 15/3 = 5.0 -> Green-
        result = compute_section_summary("1", ratings, config)
        assert result["numeric_score"] == 5
        assert result["rating"] == "Green-"

    def test_weighted_average_excludes_na(self):
        """Weighted average excludes NA criteria entirely (weight not counted)."""
        from app.core.scorecard import compute_section_summary
        config = {
            "sections": [{"code": "1", "name": "Test"}],
            "criteria": [
                {"code": "1.1", "section": "1", "name": "C1", "weight": 2.0},  # Green(6) * 2 = 12
                {"code": "1.2", "section": "1", "name": "C2", "weight": 3.0},  # NA - excluded
                {"code": "1.3", "section": "1", "name": "C3", "weight": 1.0}   # Yellow(3) * 1 = 3
            ]
        }
        ratings = {"1.1": "Green", "1.2": None, "1.3": "Yellow"}
        # Weighted mean: (6*2 + 3*1) / (2+1) = 15/3 = 5.0 -> Green-
        result = compute_section_summary("1", ratings, config)
        assert result["numeric_score"] == 5
        assert result["rating"] == "Green-"
        assert result["rated_count"] == 2
        assert result["unrated_count"] == 1

    def test_missing_criterion_treated_as_na(self):
        """Criterion in config but not in ratings -> treated as NA."""
        from app.core.scorecard import compute_section_summary
        ratings = {"1.1": "Green"}  # 1.2, 1.3 missing
        result = compute_section_summary("1", ratings, SAMPLE_CONFIG)
        # Only Green(6) counted
        assert result["numeric_score"] == 6
        assert result["rating"] == "Green"
        assert result["rated_count"] == 1
        assert result["unrated_count"] == 2

    def test_returns_section_metadata(self):
        """Result includes section code, name, and counts."""
        from app.core.scorecard import compute_section_summary
        ratings = {"1.1": "Green", "1.2": "Yellow", "1.3": None}
        result = compute_section_summary("1", ratings, SAMPLE_CONFIG)
        assert result["section_code"] == "1"
        assert result["section_name"] == "Evaluation of Conceptual Soundness"
        assert result["criteria_count"] == 3


# ============================================================================
# Section 3: Overall Assessment Computation Tests
# ============================================================================

class TestComputeOverallAssessment:
    """Tests for compute_overall_assessment function."""

    def test_all_sections_rated(self):
        """All sections have non-zero scores."""
        from app.core.scorecard import compute_overall_assessment
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

    def test_one_section_na_excluded(self):
        """One section is NA - excluded from average."""
        from app.core.scorecard import compute_overall_assessment
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

    def test_only_one_section_rated(self):
        """Only one section has ratings."""
        from app.core.scorecard import compute_overall_assessment
        section_summaries = [
            {"section_code": "1", "numeric_score": 3, "rating": "Yellow"},
            {"section_code": "2", "numeric_score": 0, "rating": None},
            {"section_code": "3", "numeric_score": 0, "rating": None}
        ]
        result = compute_overall_assessment(section_summaries)
        assert result["numeric_score"] == 3
        assert result["rating"] == "Yellow"
        assert result["rated_sections_count"] == 1

    def test_all_sections_na(self):
        """All sections are NA -> overall is NA."""
        from app.core.scorecard import compute_overall_assessment
        section_summaries = [
            {"section_code": "1", "numeric_score": 0, "rating": None},
            {"section_code": "2", "numeric_score": 0, "rating": None},
            {"section_code": "3", "numeric_score": 0, "rating": None}
        ]
        result = compute_overall_assessment(section_summaries)
        assert result["numeric_score"] == 0
        assert result["rating"] is None
        assert result["rated_sections_count"] == 0

    def test_rounding_half_up_4_5_to_5(self):
        """Test half-up rounding in overall: (5 + 4) / 2 = 4.5 -> 5."""
        from app.core.scorecard import compute_overall_assessment
        section_summaries = [
            {"section_code": "1", "numeric_score": 5, "rating": "Green-"},
            {"section_code": "2", "numeric_score": 4, "rating": "Yellow+"}
        ]
        result = compute_overall_assessment(section_summaries)
        assert result["numeric_score"] == 5
        assert result["rating"] == "Green-"

    def test_returns_section_counts(self):
        """Result includes sections_count."""
        from app.core.scorecard import compute_overall_assessment
        section_summaries = [
            {"section_code": "1", "numeric_score": 5, "rating": "Green-"},
            {"section_code": "2", "numeric_score": 0, "rating": None}
        ]
        result = compute_overall_assessment(section_summaries)
        assert result["sections_count"] == 2
        assert result["rated_sections_count"] == 1


# ============================================================================
# Section 4: Full Scorecard Computation Tests
# ============================================================================

class TestComputeScorecard:
    """Tests for compute_scorecard function (integration of all components)."""

    def test_full_scorecard_structure(self):
        """Full scorecard computation returns correct structure."""
        from app.core.scorecard import compute_scorecard
        ratings = {
            "1.1": "Green",
            "1.2": "Yellow+",
            "1.3": "Yellow",
            "2.1": "Green",
            "2.2": "Green-",
            "3.1": "Yellow",
            "3.2": "Yellow-"
        }
        result = compute_scorecard(ratings, SAMPLE_CONFIG)

        # Verify structure
        assert "criteria_details" in result
        assert "section_summaries" in result
        assert "overall_assessment" in result

        # Check criteria details
        assert len(result["criteria_details"]) == 7  # All 7 criteria from config

    def test_unknown_criterion_ignored(self):
        """Unknown criterion codes are ignored."""
        from app.core.scorecard import compute_scorecard
        config = {
            "sections": [{"code": "1", "name": "S1"}],
            "criteria": [{"code": "1.1", "section": "1", "name": "C1", "weight": 1.0}]
        }
        ratings = {"1.1": "Green", "9.9": "Red"}  # 9.9 doesn't exist
        result = compute_scorecard(ratings, config)

        # Only 1.1 should be in details
        assert len(result["criteria_details"]) == 1
        assert result["criteria_details"][0]["criterion_code"] == "1.1"

    def test_empty_ratings_all_na(self):
        """Empty ratings dict -> all NA."""
        from app.core.scorecard import compute_scorecard
        result = compute_scorecard({}, SAMPLE_CONFIG)

        assert result["overall_assessment"]["numeric_score"] == 0
        assert result["overall_assessment"]["rating"] is None

    def test_section_summaries_computed_correctly(self):
        """Section summaries are computed from criteria ratings."""
        from app.core.scorecard import compute_scorecard
        ratings = {
            "1.1": "Green",   # 6
            "1.2": "Green",   # 6
            "1.3": "Green",   # 6
            "2.1": "Yellow",  # 3
            "2.2": "Yellow",  # 3
            "3.1": None,      # NA
            "3.2": None       # NA
        }
        result = compute_scorecard(ratings, SAMPLE_CONFIG)

        # Section 1: (6+6+6)/3 = 6
        sec1 = next(s for s in result["section_summaries"] if s["section_code"] == "1")
        assert sec1["numeric_score"] == 6
        assert sec1["rating"] == "Green"

        # Section 2: (3+3)/2 = 3
        sec2 = next(s for s in result["section_summaries"] if s["section_code"] == "2")
        assert sec2["numeric_score"] == 3
        assert sec2["rating"] == "Yellow"

        # Section 3: all NA
        sec3 = next(s for s in result["section_summaries"] if s["section_code"] == "3")
        assert sec3["numeric_score"] == 0
        assert sec3["rating"] is None

    def test_overall_from_sections(self):
        """Overall assessment is computed from section summaries."""
        from app.core.scorecard import compute_scorecard
        ratings = {
            "1.1": "Green",   # Section 1: score 6
            "1.2": "Green",
            "1.3": "Green",
            "2.1": "Yellow",  # Section 2: score 3
            "2.2": "Yellow",
            "3.1": None,      # Section 3: NA (excluded)
            "3.2": None
        }
        result = compute_scorecard(ratings, SAMPLE_CONFIG)

        # Overall: (6 + 3) / 2 = 4.5 -> rounds to 5 (half-up)
        assert result["overall_assessment"]["numeric_score"] == 5
        assert result["overall_assessment"]["rating"] == "Green-"


# ============================================================================
# Section 5: Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_explicit_na_treated_as_0(self):
        """Explicit 'N/A' string treated as score 0."""
        from app.core.scorecard import rating_to_score
        assert rating_to_score("N/A") == 0

    def test_case_insensitive_na(self):
        """NA matching is case-insensitive."""
        from app.core.scorecard import rating_to_score
        assert rating_to_score("na") == 0
        assert rating_to_score("Na") == 0
        assert rating_to_score("nA") == 0

    def test_single_criterion_section(self):
        """Section with single criterion works correctly."""
        from app.core.scorecard import compute_section_summary
        config = {
            "sections": [{"code": "1", "name": "Single"}],
            "criteria": [{"code": "1.1", "section": "1", "name": "Only", "weight": 1.0}]
        }
        ratings = {"1.1": "Yellow"}
        result = compute_section_summary("1", ratings, config)
        assert result["numeric_score"] == 3
        assert result["rating"] == "Yellow"

    def test_very_low_weighted_mean(self):
        """Weighted mean rounding at boundary."""
        from app.core.scorecard import compute_section_summary
        config = {
            "sections": [{"code": "1", "name": "Test"}],
            "criteria": [
                {"code": "1.1", "section": "1", "name": "C1", "weight": 1.0},  # Red(1)
                {"code": "1.2", "section": "1", "name": "C2", "weight": 1.0}   # Red(1)
            ]
        }
        ratings = {"1.1": "Red", "1.2": "Red"}
        result = compute_section_summary("1", ratings, config)
        assert result["numeric_score"] == 1
        assert result["rating"] == "Red"

    def test_empty_config_no_criteria(self):
        """Config with no criteria for a section."""
        from app.core.scorecard import compute_section_summary
        config = {
            "sections": [{"code": "1", "name": "Empty"}],
            "criteria": []  # No criteria
        }
        ratings = {"1.1": "Green"}
        result = compute_section_summary("1", ratings, config)
        # No criteria means all unrated (count 0)
        assert result["numeric_score"] == 0
        assert result["criteria_count"] == 0

    def test_section_not_in_config(self):
        """Section code not found returns empty result."""
        from app.core.scorecard import compute_section_summary
        ratings = {"1.1": "Green"}
        result = compute_section_summary("99", ratings, SAMPLE_CONFIG)
        assert result["numeric_score"] == 0
        assert result["criteria_count"] == 0


# ============================================================================
# Section 6: Configuration Loading Tests
# ============================================================================

class TestLoadScorecardConfig:
    """Tests for loading scorecard configuration from JSON."""

    def test_load_from_json_file(self):
        """Load configuration from SCORE_CRITERIA.json."""
        from app.core.scorecard import load_scorecard_config

        config = load_scorecard_config()

        # Verify sections
        assert "sections" in config
        assert len(config["sections"]) == 3
        section_codes = [s["code"] for s in config["sections"]]
        assert "1" in section_codes
        assert "2" in section_codes
        assert "3" in section_codes

        # Verify criteria
        assert "criteria" in config
        assert len(config["criteria"]) == 14  # Based on SCORE_CRITERIA.json

    def test_config_criteria_have_required_fields(self):
        """All criteria have required fields."""
        from app.core.scorecard import load_scorecard_config

        config = load_scorecard_config()

        for criterion in config["criteria"]:
            assert "code" in criterion
            assert "section" in criterion
            assert "name" in criterion
            assert "weight" in criterion

    def test_config_sections_have_required_fields(self):
        """All sections have required fields."""
        from app.core.scorecard import load_scorecard_config

        config = load_scorecard_config()

        for section in config["sections"]:
            assert "code" in section
            assert "name" in section
