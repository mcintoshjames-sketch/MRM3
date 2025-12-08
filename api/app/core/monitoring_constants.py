"""Centralized constants for the monitoring module.

This file serves as the single source of truth for monitoring-related
configuration values. Changes here should be reflected in the database
seed data and vice versa.

WARNING: If you modify outcome codes here, you must also update:
- api/app/seed.py - Taxonomy value definitions
- web/src/components/MonitoringDataGrid.tsx - Frontend outcome handling
"""

# Taxonomy configuration
QUALITATIVE_OUTCOME_TAXONOMY_NAME = "Qualitative Outcome"

# Outcome codes (must match TaxonomyValue.code in seed data)
OUTCOME_GREEN = "GREEN"
OUTCOME_YELLOW = "YELLOW"
OUTCOME_RED = "RED"
OUTCOME_NA = "N/A"
OUTCOME_UNCONFIGURED = "UNCONFIGURED"  # Returned when no thresholds are set

# Valid outcome codes for validation (excludes N/A and UNCONFIGURED which are special states)
VALID_OUTCOME_CODES = frozenset({OUTCOME_GREEN, OUTCOME_YELLOW, OUTCOME_RED})

# All possible outcome codes including special states
ALL_OUTCOME_CODES = frozenset({
    OUTCOME_GREEN,
    OUTCOME_YELLOW,
    OUTCOME_RED,
    OUTCOME_NA,
    OUTCOME_UNCONFIGURED,
})
