"""Unit tests for bucket taxonomy validation logic."""
import pytest
from unittest.mock import MagicMock

from app.api.taxonomies import validate_bucket_taxonomy_values
from app.schemas.taxonomy import TaxonomyValueCreate


def create_mock_value(value_id: int, label: str, min_days: int | None, max_days: int | None):
    """Create a mock TaxonomyValue object for testing."""
    mock = MagicMock()
    mock.value_id = value_id
    mock.label = label
    mock.min_days = min_days
    mock.max_days = max_days
    return mock


class TestValidateBucketTaxonomyValues:
    """Tests for validate_bucket_taxonomy_values function."""

    # ===================
    # Happy Path Tests
    # ===================

    def test_empty_bucket_list_is_valid(self):
        """Empty bucket list should be valid."""
        is_valid, error = validate_bucket_taxonomy_values([])
        assert is_valid is True
        assert error is None

    def test_single_unbounded_bucket_is_valid(self):
        """Single bucket with both bounds null is valid."""
        values = [create_mock_value(1, "All", None, None)]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is True
        assert error is None

    def test_two_contiguous_buckets_valid(self):
        """Two buckets: (null, 0) and (1, null) should be valid."""
        values = [
            create_mock_value(1, "Current", None, 0),
            create_mock_value(2, "Past Due", 1, None),
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is True
        assert error is None

    def test_complete_past_due_level_buckets_valid(self):
        """Complete 6-bucket Past Due Level configuration should be valid."""
        values = [
            create_mock_value(1, "Current", None, 0),
            create_mock_value(2, "Minimal", 1, 365),
            create_mock_value(3, "Moderate", 366, 730),
            create_mock_value(4, "Significant", 731, 1095),
            create_mock_value(5, "Critical", 1096, 1825),
            create_mock_value(6, "Obsolete", 1826, None),
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is True
        assert error is None

    def test_three_contiguous_buckets_valid(self):
        """Three contiguous buckets should be valid."""
        values = [
            create_mock_value(1, "Low", None, 30),
            create_mock_value(2, "Medium", 31, 90),
            create_mock_value(3, "High", 91, None),
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is True
        assert error is None

    # ===================
    # Gap Detection Tests
    # ===================

    def test_gap_between_two_buckets_detected(self):
        """Gap between buckets should be detected."""
        values = [
            create_mock_value(1, "Low", None, 10),
            create_mock_value(2, "High", 15, None),  # Gap: 11-14 missing
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is False
        assert "Gap detected" in error
        assert "11" in error  # Expected min_days

    def test_gap_in_middle_of_range_detected(self):
        """Gap in the middle of a multi-bucket range should be detected."""
        values = [
            create_mock_value(1, "Low", None, 30),
            create_mock_value(2, "Medium", 31, 60),
            # Gap: 61-89 missing
            create_mock_value(3, "High", 90, None),
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is False
        assert "Gap detected" in error

    def test_single_day_gap_detected(self):
        """Even a single-day gap should be detected."""
        values = [
            create_mock_value(1, "Current", None, 0),
            create_mock_value(2, "Past Due", 2, None),  # Gap: day 1 missing
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is False
        assert "Gap detected" in error

    # ===================
    # Overlap Detection Tests
    # ===================

    def test_overlapping_buckets_detected(self):
        """Overlapping buckets should be detected."""
        values = [
            create_mock_value(1, "Low", None, 50),
            create_mock_value(2, "High", 40, None),  # Overlap: 40-50
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is False
        assert "Overlap detected" in error

    def test_exact_boundary_overlap_detected(self):
        """Buckets sharing exact boundary should be detected as overlap."""
        values = [
            create_mock_value(1, "Low", None, 30),
            create_mock_value(2, "High", 30, None),  # Overlap at 30
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is False
        assert "Overlap detected" in error

    def test_complete_overlap_detected(self):
        """Completely overlapping buckets should be detected."""
        values = [
            create_mock_value(1, "All", None, None),
            create_mock_value(2, "Some", 10, 50),  # Completely within first bucket
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is False
        # Should fail because middle bucket can't have null max_days (first bucket has it)
        assert "highest bucket" in error.lower() or "overlap" in error.lower()

    # ===================
    # Boundary Validation Tests
    # ===================

    def test_first_bucket_without_null_min_fails(self):
        """First bucket (lowest) must have min_days=null."""
        values = [
            create_mock_value(1, "Low", 0, 30),  # Should have min_days=None
            create_mock_value(2, "High", 31, None),
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is False
        assert "min_days=null" in error.lower() or "lowest bucket" in error.lower()

    def test_last_bucket_without_null_max_fails(self):
        """Last bucket (highest) must have max_days=null."""
        values = [
            create_mock_value(1, "Low", None, 30),
            create_mock_value(2, "High", 31, 100),  # Should have max_days=None
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is False
        assert "max_days=null" in error.lower() or "highest bucket" in error.lower()

    def test_middle_bucket_with_null_min_fails(self):
        """Middle bucket cannot have min_days=null."""
        values = [
            create_mock_value(1, "First", None, 30),
            create_mock_value(2, "Middle", None, 60),  # Invalid: min_days should not be null
            create_mock_value(3, "Last", 61, None),
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is False
        assert "Only the lowest bucket" in error or "min_days=null" in error.lower()

    def test_middle_bucket_with_null_max_fails(self):
        """Middle bucket cannot have max_days=null."""
        values = [
            create_mock_value(1, "First", None, 30),
            create_mock_value(2, "Middle", 31, None),  # Invalid: max_days should not be null
            create_mock_value(3, "Last", 61, None),
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is False
        assert "Only the highest bucket" in error or "max_days=null" in error.lower()

    def test_single_bucket_with_only_null_min_fails(self):
        """Single bucket with only min_days=null is invalid."""
        values = [create_mock_value(1, "Only", None, 100)]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is False
        assert "single bucket" in error.lower()

    def test_single_bucket_with_only_null_max_fails(self):
        """Single bucket with only max_days=null is invalid."""
        values = [create_mock_value(1, "Only", 0, None)]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is False
        assert "single bucket" in error.lower()

    def test_single_bucket_with_both_non_null_fails(self):
        """Single bucket with both min and max non-null is invalid."""
        values = [create_mock_value(1, "Only", 0, 100)]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is False
        assert "single bucket" in error.lower()

    # ===================
    # Edge Cases
    # ===================

    def test_single_day_bucket_in_middle_valid(self):
        """Single-day bucket (min=max) in the middle is valid."""
        values = [
            create_mock_value(1, "Before", None, 4),
            create_mock_value(2, "Exactly 5", 5, 5),  # Single day
            create_mock_value(3, "After", 6, None),
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is True
        assert error is None

    def test_negative_day_values_valid(self):
        """Negative day values (days before due date) should be valid."""
        values = [
            create_mock_value(1, "Early", None, -1),  # Before due date
            create_mock_value(2, "On Time", 0, 0),  # Due date
            create_mock_value(3, "Late", 1, None),  # After due date
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is True
        assert error is None

    def test_large_day_values_valid(self):
        """Very large day values should be handled correctly."""
        values = [
            create_mock_value(1, "Normal", None, 999999),
            create_mock_value(2, "Extreme", 1000000, None),
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is True
        assert error is None

    def test_buckets_out_of_order_still_validated(self):
        """Buckets provided out of order should still be validated correctly."""
        # Provide buckets in reverse order - function should sort them
        values = [
            create_mock_value(3, "High", 91, None),
            create_mock_value(1, "Low", None, 30),
            create_mock_value(2, "Medium", 31, 90),
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is True
        assert error is None

    # ===================
    # New Value Tests
    # ===================

    def test_adding_valid_new_value(self):
        """Adding a valid new value should pass validation."""
        existing = [
            create_mock_value(1, "Current", None, 0),
            create_mock_value(2, "Past Due", 1, None),
        ]
        new_value = TaxonomyValueCreate(
            code="MODERATE",
            label="Moderate",
            min_days=31,
            max_days=None,
        )
        # Update existing to make room for new value
        existing[1].max_days = 30

        is_valid, error = validate_bucket_taxonomy_values(existing, new_value=new_value)
        assert is_valid is True
        assert error is None

    def test_adding_value_that_creates_gap_fails(self):
        """Adding a value that creates a gap should fail."""
        existing = [
            create_mock_value(1, "Low", None, 30),
            create_mock_value(2, "High", 61, None),  # Gap at 31-60
        ]
        new_value = TaxonomyValueCreate(
            code="EXTRA",
            label="Extra",
            min_days=100,
            max_days=200,
        )
        is_valid, error = validate_bucket_taxonomy_values(existing, new_value=new_value)
        assert is_valid is False

    def test_adding_value_that_creates_overlap_fails(self):
        """Adding a value that overlaps should fail."""
        existing = [
            create_mock_value(1, "Low", None, 50),
            create_mock_value(2, "High", 51, None),
        ]
        new_value = TaxonomyValueCreate(
            code="OVERLAP",
            label="Overlap",
            min_days=40,
            max_days=60,
        )
        is_valid, error = validate_bucket_taxonomy_values(existing, new_value=new_value)
        assert is_valid is False

    # ===================
    # Update Value Tests
    # ===================

    def test_updating_value_creating_overlap_fails(self):
        """Updating a value that creates an overlap should fail."""
        values = [
            create_mock_value(1, "Low", None, 30),
            create_mock_value(2, "Medium", 31, 60),
            create_mock_value(3, "High", 61, None),
        ]
        # Update medium bucket to expand past High's min_days - creates overlap
        is_valid, error = validate_bucket_taxonomy_values(
            values,
            updating_value_id=2,
            updated_min_days=31,
            updated_max_days=90,  # Overlaps with High which starts at 61
        )
        assert is_valid is False
        assert "Overlap detected" in error

    def test_updating_value_maintaining_contiguity(self):
        """Updating values while maintaining contiguity should pass."""
        values = [
            create_mock_value(1, "Low", None, 30),
            create_mock_value(2, "Medium", 31, 60),
            create_mock_value(3, "High", 61, None),
        ]
        # Update medium bucket - valid change that maintains contiguity
        is_valid, error = validate_bucket_taxonomy_values(
            values,
            updating_value_id=2,
            updated_min_days=31,
            updated_max_days=60,  # Same as before
        )
        assert is_valid is True
        assert error is None

    def test_updating_first_bucket_max(self):
        """Updating first bucket's max_days while maintaining contiguity."""
        values = [
            create_mock_value(1, "Low", None, 30),
            create_mock_value(2, "High", 31, None),
        ]
        # This would create a gap
        is_valid, error = validate_bucket_taxonomy_values(
            values,
            updating_value_id=1,
            updated_min_days=None,
            updated_max_days=20,  # Shrink - creates gap 21-30
        )
        assert is_valid is False
        assert "Gap detected" in error


class TestBucketValidationErrorMessages:
    """Tests to ensure error messages are helpful and descriptive."""

    def test_gap_error_includes_bucket_labels(self):
        """Gap error should mention the affected bucket labels."""
        values = [
            create_mock_value(1, "First Bucket", None, 10),
            create_mock_value(2, "Second Bucket", 20, None),
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is False
        assert "First Bucket" in error
        assert "Second Bucket" in error

    def test_overlap_error_includes_bucket_labels(self):
        """Overlap error should mention the affected bucket labels."""
        values = [
            create_mock_value(1, "Alpha", None, 50),
            create_mock_value(2, "Beta", 40, None),
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is False
        assert "Alpha" in error
        assert "Beta" in error

    def test_boundary_error_includes_bucket_label(self):
        """Boundary validation error should mention the affected bucket."""
        values = [
            create_mock_value(1, "My Special Bucket", 10, 50),  # Missing null min
            create_mock_value(2, "Other", 51, None),
        ]
        is_valid, error = validate_bucket_taxonomy_values(values)
        assert is_valid is False
        assert "My Special Bucket" in error or "lowest bucket" in error.lower()
