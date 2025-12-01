"""Tests for risk calculation logic (TDD - RED phase).

These tests define the expected behavior of the risk calculation module.
Run these tests FIRST before implementing the module.
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock

# Note: These imports will fail until the module is implemented
# That's expected in TDD - RED phase
from app.core.risk_calculation import (
    RATING_SCORES,
    calculate_qualitative_score,
    lookup_inherent_risk,
    map_to_tier_code,
    get_effective_values,
    INHERENT_RISK_MATRIX,
    TIER_MAPPING,
)


class TestRatingScores:
    """Test the rating score constants."""

    def test_high_is_3(self):
        assert RATING_SCORES['HIGH'] == 3

    def test_medium_is_2(self):
        assert RATING_SCORES['MEDIUM'] == 2

    def test_low_is_1(self):
        assert RATING_SCORES['LOW'] == 1


class TestCalculateQualitativeScore:
    """Test the weighted qualitative score calculation."""

    def test_qualitative_all_high(self):
        """All HIGH ratings should yield score 3.0 and level HIGH."""
        factor_assessments = [
            _create_factor_assessment(rating='HIGH', weight=Decimal('0.30')),
            _create_factor_assessment(rating='HIGH', weight=Decimal('0.30')),
            _create_factor_assessment(rating='HIGH', weight=Decimal('0.20')),
            _create_factor_assessment(rating='HIGH', weight=Decimal('0.20')),
        ]
        score, level = calculate_qualitative_score(factor_assessments)
        assert score == Decimal('3.00')
        assert level == 'HIGH'

    def test_qualitative_all_medium(self):
        """All MEDIUM ratings should yield score 2.0 and level MEDIUM."""
        factor_assessments = [
            _create_factor_assessment(rating='MEDIUM', weight=Decimal('0.30')),
            _create_factor_assessment(rating='MEDIUM', weight=Decimal('0.30')),
            _create_factor_assessment(rating='MEDIUM', weight=Decimal('0.20')),
            _create_factor_assessment(rating='MEDIUM', weight=Decimal('0.20')),
        ]
        score, level = calculate_qualitative_score(factor_assessments)
        assert score == Decimal('2.00')
        assert level == 'MEDIUM'

    def test_qualitative_all_low(self):
        """All LOW ratings should yield score 1.0 and level LOW."""
        factor_assessments = [
            _create_factor_assessment(rating='LOW', weight=Decimal('0.30')),
            _create_factor_assessment(rating='LOW', weight=Decimal('0.30')),
            _create_factor_assessment(rating='LOW', weight=Decimal('0.20')),
            _create_factor_assessment(rating='LOW', weight=Decimal('0.20')),
        ]
        score, level = calculate_qualitative_score(factor_assessments)
        assert score == Decimal('1.00')
        assert level == 'LOW'

    def test_qualitative_mixed_high(self):
        """REP=H, COMP=H, USE=M, STAB=M should yield score=2.4, level=HIGH."""
        # 0.30*3 + 0.30*3 + 0.20*2 + 0.20*2 = 0.9 + 0.9 + 0.4 + 0.4 = 2.6
        factor_assessments = [
            _create_factor_assessment(rating='HIGH', weight=Decimal('0.30')),
            _create_factor_assessment(rating='HIGH', weight=Decimal('0.30')),
            _create_factor_assessment(rating='MEDIUM', weight=Decimal('0.20')),
            _create_factor_assessment(rating='MEDIUM', weight=Decimal('0.20')),
        ]
        score, level = calculate_qualitative_score(factor_assessments)
        assert score == Decimal('2.60')
        assert level == 'HIGH'

    def test_qualitative_mixed_medium(self):
        """REP=M, COMP=M, USE=L, STAB=L should yield score=1.6, level=MEDIUM."""
        # 0.30*2 + 0.30*2 + 0.20*1 + 0.20*1 = 0.6 + 0.6 + 0.2 + 0.2 = 1.6
        factor_assessments = [
            _create_factor_assessment(rating='MEDIUM', weight=Decimal('0.30')),
            _create_factor_assessment(rating='MEDIUM', weight=Decimal('0.30')),
            _create_factor_assessment(rating='LOW', weight=Decimal('0.20')),
            _create_factor_assessment(rating='LOW', weight=Decimal('0.20')),
        ]
        score, level = calculate_qualitative_score(factor_assessments)
        assert score == Decimal('1.60')
        assert level == 'MEDIUM'

    def test_qualitative_mixed_low(self):
        """REP=L, COMP=M, USE=L, STAB=L should yield score=1.3, level=LOW."""
        # 0.30*1 + 0.30*2 + 0.20*1 + 0.20*1 = 0.3 + 0.6 + 0.2 + 0.2 = 1.3
        factor_assessments = [
            _create_factor_assessment(rating='LOW', weight=Decimal('0.30')),
            _create_factor_assessment(rating='MEDIUM', weight=Decimal('0.30')),
            _create_factor_assessment(rating='LOW', weight=Decimal('0.20')),
            _create_factor_assessment(rating='LOW', weight=Decimal('0.20')),
        ]
        score, level = calculate_qualitative_score(factor_assessments)
        assert score == Decimal('1.30')
        assert level == 'LOW'

    def test_qualitative_boundary_high(self):
        """Score exactly 2.1 should be HIGH."""
        # 0.30*3 + 0.30*2 + 0.20*2 + 0.20*2 = 0.9 + 0.6 + 0.4 + 0.4 = 2.3
        # Need: 2.1 = 0.30*x1 + 0.30*x2 + 0.20*x3 + 0.20*x4
        # Try: 0.30*3 + 0.30*2 + 0.20*1 + 0.20*1 = 0.9 + 0.6 + 0.2 + 0.2 = 1.9
        # Try: 0.30*3 + 0.30*2 + 0.20*2 + 0.20*1 = 0.9 + 0.6 + 0.4 + 0.2 = 2.1
        factor_assessments = [
            _create_factor_assessment(rating='HIGH', weight=Decimal('0.30')),
            _create_factor_assessment(rating='MEDIUM', weight=Decimal('0.30')),
            _create_factor_assessment(rating='MEDIUM', weight=Decimal('0.20')),
            _create_factor_assessment(rating='LOW', weight=Decimal('0.20')),
        ]
        score, level = calculate_qualitative_score(factor_assessments)
        assert score == Decimal('2.10')
        assert level == 'HIGH'

    def test_qualitative_boundary_medium_lower(self):
        """Score exactly 1.6 should be MEDIUM."""
        factor_assessments = [
            _create_factor_assessment(rating='MEDIUM', weight=Decimal('0.30')),
            _create_factor_assessment(rating='MEDIUM', weight=Decimal('0.30')),
            _create_factor_assessment(rating='LOW', weight=Decimal('0.20')),
            _create_factor_assessment(rating='LOW', weight=Decimal('0.20')),
        ]
        score, level = calculate_qualitative_score(factor_assessments)
        assert score == Decimal('1.60')
        assert level == 'MEDIUM'

    def test_qualitative_just_below_medium_boundary(self):
        """Score 1.59 should be LOW."""
        # 0.30*1 + 0.30*2 + 0.20*2 + 0.20*1 = 0.3 + 0.6 + 0.4 + 0.2 = 1.5
        factor_assessments = [
            _create_factor_assessment(rating='LOW', weight=Decimal('0.30')),
            _create_factor_assessment(rating='MEDIUM', weight=Decimal('0.30')),
            _create_factor_assessment(rating='MEDIUM', weight=Decimal('0.20')),
            _create_factor_assessment(rating='LOW', weight=Decimal('0.20')),
        ]
        score, level = calculate_qualitative_score(factor_assessments)
        assert score == Decimal('1.50')
        assert level == 'LOW'

    def test_qualitative_partial_factors_rated(self):
        """Partial factors (only some rated) should still calculate."""
        # Only 2 factors rated (weights 0.30 + 0.30 = 0.60)
        factor_assessments = [
            _create_factor_assessment(rating='HIGH', weight=Decimal('0.30')),
            _create_factor_assessment(rating='MEDIUM', weight=Decimal('0.30')),
            _create_factor_assessment(rating=None, weight=Decimal('0.20')),
            _create_factor_assessment(rating=None, weight=Decimal('0.20')),
        ]
        score, level = calculate_qualitative_score(factor_assessments)
        # 0.30*3 + 0.30*2 = 0.9 + 0.6 = 1.5
        assert score == Decimal('1.50')
        assert level == 'LOW'

    def test_qualitative_empty_factors(self):
        """No rated factors should return None, None."""
        factor_assessments = [
            _create_factor_assessment(rating=None, weight=Decimal('0.30')),
            _create_factor_assessment(rating=None, weight=Decimal('0.30')),
            _create_factor_assessment(rating=None, weight=Decimal('0.20')),
            _create_factor_assessment(rating=None, weight=Decimal('0.20')),
        ]
        score, level = calculate_qualitative_score(factor_assessments)
        assert score is None
        assert level is None

    def test_qualitative_empty_list(self):
        """Empty list should return None, None."""
        score, level = calculate_qualitative_score([])
        assert score is None
        assert level is None


class TestInherentRiskMatrix:
    """Test the inherent risk matrix lookup (all 9 combinations)."""

    def test_matrix_high_high(self):
        assert lookup_inherent_risk('HIGH', 'HIGH') == 'HIGH'

    def test_matrix_high_medium(self):
        assert lookup_inherent_risk('HIGH', 'MEDIUM') == 'MEDIUM'

    def test_matrix_high_low(self):
        assert lookup_inherent_risk('HIGH', 'LOW') == 'LOW'

    def test_matrix_medium_high(self):
        assert lookup_inherent_risk('MEDIUM', 'HIGH') == 'MEDIUM'

    def test_matrix_medium_medium(self):
        assert lookup_inherent_risk('MEDIUM', 'MEDIUM') == 'MEDIUM'

    def test_matrix_medium_low(self):
        assert lookup_inherent_risk('MEDIUM', 'LOW') == 'LOW'

    def test_matrix_low_high(self):
        assert lookup_inherent_risk('LOW', 'HIGH') == 'LOW'

    def test_matrix_low_medium(self):
        assert lookup_inherent_risk('LOW', 'MEDIUM') == 'LOW'

    def test_matrix_low_low(self):
        assert lookup_inherent_risk('LOW', 'LOW') == 'VERY_LOW'

    def test_matrix_invalid_quantitative(self):
        """Invalid quantitative value should return None."""
        assert lookup_inherent_risk('INVALID', 'HIGH') is None

    def test_matrix_invalid_qualitative(self):
        """Invalid qualitative value should return None."""
        assert lookup_inherent_risk('HIGH', 'INVALID') is None

    def test_matrix_none_quantitative(self):
        """None quantitative should return None."""
        assert lookup_inherent_risk(None, 'HIGH') is None

    def test_matrix_none_qualitative(self):
        """None qualitative should return None."""
        assert lookup_inherent_risk('HIGH', None) is None


class TestTierMapping:
    """Test the tier code mapping."""

    def test_tier_mapping_high(self):
        assert map_to_tier_code('HIGH') == 'TIER_1'

    def test_tier_mapping_medium(self):
        assert map_to_tier_code('MEDIUM') == 'TIER_2'

    def test_tier_mapping_low(self):
        assert map_to_tier_code('LOW') == 'TIER_3'

    def test_tier_mapping_very_low(self):
        assert map_to_tier_code('VERY_LOW') == 'TIER_4'

    def test_tier_mapping_none(self):
        assert map_to_tier_code(None) is None

    def test_tier_mapping_invalid(self):
        assert map_to_tier_code('INVALID') is None


class TestGetEffectiveValues:
    """Test the effective values calculation with overrides."""

    def test_effective_values_no_overrides(self):
        """Without overrides, effective = calculated."""
        assessment = _create_assessment(
            quantitative_rating='HIGH',
            quantitative_override=None,
            qualitative_calculated_level='MEDIUM',
            qualitative_override=None,
            derived_risk_tier_override=None
        )
        result = get_effective_values(assessment)
        assert result['effective_quantitative'] == 'HIGH'
        assert result['effective_qualitative'] == 'MEDIUM'
        assert result['derived_risk_tier'] == 'MEDIUM'  # Matrix: HIGH x MEDIUM = MEDIUM
        assert result['effective_risk_tier'] == 'MEDIUM'
        assert result['tier_code'] == 'TIER_2'

    def test_effective_values_quantitative_override(self):
        """Quantitative override should replace quantitative rating."""
        assessment = _create_assessment(
            quantitative_rating='HIGH',
            quantitative_override='LOW',  # Override to LOW
            qualitative_calculated_level='MEDIUM',
            qualitative_override=None,
            derived_risk_tier_override=None
        )
        result = get_effective_values(assessment)
        assert result['effective_quantitative'] == 'LOW'
        assert result['effective_qualitative'] == 'MEDIUM'
        assert result['derived_risk_tier'] == 'LOW'  # Matrix: LOW x MEDIUM = LOW
        assert result['effective_risk_tier'] == 'LOW'
        assert result['tier_code'] == 'TIER_3'

    def test_effective_values_qualitative_override(self):
        """Qualitative override should replace calculated level."""
        assessment = _create_assessment(
            quantitative_rating='MEDIUM',
            quantitative_override=None,
            qualitative_calculated_level='LOW',
            qualitative_override='HIGH',  # Override to HIGH
            derived_risk_tier_override=None
        )
        result = get_effective_values(assessment)
        assert result['effective_quantitative'] == 'MEDIUM'
        assert result['effective_qualitative'] == 'HIGH'
        assert result['derived_risk_tier'] == 'MEDIUM'  # Matrix: MEDIUM x HIGH = MEDIUM
        assert result['effective_risk_tier'] == 'MEDIUM'
        assert result['tier_code'] == 'TIER_2'

    def test_effective_values_final_override(self):
        """Final override should replace derived tier."""
        assessment = _create_assessment(
            quantitative_rating='LOW',
            quantitative_override=None,
            qualitative_calculated_level='LOW',
            qualitative_override=None,
            derived_risk_tier_override='HIGH'  # Override final to HIGH
        )
        result = get_effective_values(assessment)
        assert result['effective_quantitative'] == 'LOW'
        assert result['effective_qualitative'] == 'LOW'
        assert result['derived_risk_tier'] == 'VERY_LOW'  # Matrix: LOW x LOW = VERY_LOW
        assert result['effective_risk_tier'] == 'HIGH'  # Overridden
        assert result['tier_code'] == 'TIER_1'

    def test_effective_values_all_overrides(self):
        """All three overrides applied together."""
        assessment = _create_assessment(
            quantitative_rating='LOW',
            quantitative_override='HIGH',  # Override 1
            qualitative_calculated_level='LOW',
            qualitative_override='HIGH',  # Override 2
            derived_risk_tier_override='VERY_LOW'  # Override 3
        )
        result = get_effective_values(assessment)
        assert result['effective_quantitative'] == 'HIGH'
        assert result['effective_qualitative'] == 'HIGH'
        assert result['derived_risk_tier'] == 'HIGH'  # Matrix: HIGH x HIGH = HIGH
        assert result['effective_risk_tier'] == 'VERY_LOW'  # Final override
        assert result['tier_code'] == 'TIER_4'

    def test_effective_values_missing_quantitative(self):
        """Missing quantitative should result in no derived tier."""
        assessment = _create_assessment(
            quantitative_rating=None,
            quantitative_override=None,
            qualitative_calculated_level='HIGH',
            qualitative_override=None,
            derived_risk_tier_override=None
        )
        result = get_effective_values(assessment)
        assert result['effective_quantitative'] is None
        assert result['effective_qualitative'] == 'HIGH'
        assert result['derived_risk_tier'] is None
        assert result['effective_risk_tier'] is None
        assert result['tier_code'] is None

    def test_effective_values_missing_qualitative(self):
        """Missing qualitative should result in no derived tier."""
        assessment = _create_assessment(
            quantitative_rating='HIGH',
            quantitative_override=None,
            qualitative_calculated_level=None,
            qualitative_override=None,
            derived_risk_tier_override=None
        )
        result = get_effective_values(assessment)
        assert result['effective_quantitative'] == 'HIGH'
        assert result['effective_qualitative'] is None
        assert result['derived_risk_tier'] is None
        assert result['effective_risk_tier'] is None
        assert result['tier_code'] is None


# Helper functions for creating test objects

def _create_factor_assessment(rating: str = None, weight: Decimal = Decimal('0.25')):
    """Create a mock factor assessment for testing."""
    mock = MagicMock()
    mock.rating = rating
    mock.weight_at_assessment = weight
    return mock


def _create_assessment(
    quantitative_rating: str = None,
    quantitative_override: str = None,
    qualitative_calculated_level: str = None,
    qualitative_override: str = None,
    derived_risk_tier_override: str = None
):
    """Create a mock assessment for testing effective values."""
    mock = MagicMock()
    mock.quantitative_rating = quantitative_rating
    mock.quantitative_override = quantitative_override
    mock.qualitative_calculated_level = qualitative_calculated_level
    mock.qualitative_override = qualitative_override
    mock.derived_risk_tier_override = derived_risk_tier_override
    return mock
