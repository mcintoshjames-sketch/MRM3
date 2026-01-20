"""
Pytest fixtures for KPI report testing.
Provides mock data factories for various test scenarios.

IMPORTANT: These fixtures depend on `taxonomy_values` from main conftest.py
which seeds all required Taxonomy/TaxonomyValue records.
"""
import pytest
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from app.models import Model, ValidationRequest, ValidationPolicy
from app.models.validation import ValidationRequestModelVersion, ValidationOutcome
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.residual_risk_map import ResidualRiskMapConfig
from app.models.scorecard import ValidationScorecardResult


# =============================================================================
# Cache Clearing Fixture
# =============================================================================

@pytest.fixture(autouse=True)
def clear_kpi_cache():
    """Clear KPI report cache before each test.

    The KPI report uses a module-level cache that can cause test interference
    when tests run in parallel. This fixture ensures each test starts with
    an empty cache.
    """
    from app.api.kpi_report import _KPI_CACHE
    _KPI_CACHE.clear()
    yield
    _KPI_CACHE.clear()


# =============================================================================
# Master Taxonomy Fixture (Gap 1 Fix)
# =============================================================================

@pytest.fixture
def kpi_taxonomies(db_session, taxonomy_values):
    """
    Master fixture ensuring all KPI-required taxonomies exist.

    CRITICAL: This fixture MUST be included in any test that uses
    tier1_policy, create_approved_validation, or create_interim_validation.

    The `taxonomy_values` fixture from conftest.py creates:
    - Model Risk Tier: TIER_1, TIER_2
    - Validation Type: INITIAL, COMPREHENSIVE, TARGETED, INTERIM
    - Validation Outcome: PASS, PASS_WITH_FINDINGS, FAIL
    - Validation Request Status: INTAKE, PLANNING, IN_PROGRESS, REVIEW, PENDING_APPROVAL, APPROVED
    """
    # Return the taxonomy_values dict for easy access in tests
    return taxonomy_values


# =============================================================================
# Validation Policy Fixtures
# =============================================================================

@pytest.fixture
def kpi_tier1_policy(db_session, kpi_taxonomies):
    """Create Tier 1 validation policy with standard SLAs.

    FIXED: Now depends on kpi_taxonomies to ensure TIER_1 exists.
    """
    tier1 = kpi_taxonomies["tier1"]  # Direct reference, not query

    policy = ValidationPolicy(
        risk_tier_id=tier1.value_id,
        frequency_months=12,
        grace_period_months=3,
        model_change_lead_time_days=90
    )
    db_session.add(policy)
    db_session.commit()
    return policy


@pytest.fixture
def kpi_tier2_policy(db_session, kpi_taxonomies):
    """Create Tier 2 validation policy with relaxed SLAs."""
    tier2 = kpi_taxonomies["tier2"]

    policy = ValidationPolicy(
        risk_tier_id=tier2.value_id,
        frequency_months=24,  # 2-year frequency
        grace_period_months=6,
        model_change_lead_time_days=60
    )
    db_session.add(policy)
    db_session.commit()
    return policy


# =============================================================================
# Model Fixtures
# =============================================================================

@pytest.fixture
def kpi_active_model(db_session, admin_user, kpi_taxonomies, usage_frequency, kpi_tier1_policy):
    """Create a single active model with TIER_1 risk tier.

    FIXED: Links to tier1 via risk_tier_id for proper ID-based resolution.
    """
    model = Model(
        model_name="Test KPI Model",
        status="Active",
        owner_id=admin_user.user_id,
        development_type="In-House",
        risk_tier_id=kpi_taxonomies["tier1"].value_id,  # Proper ID link
        usage_frequency_id=usage_frequency["daily"].value_id,
        row_approval_status="approved"
    )
    db_session.add(model)
    db_session.commit()
    return model


@pytest.fixture
def kpi_second_active_model(db_session, admin_user, kpi_taxonomies, usage_frequency, kpi_tier2_policy):
    """Create a second active model with TIER_2 risk tier."""
    model = Model(
        model_name="Second KPI Model",
        status="Active",
        owner_id=admin_user.user_id,
        development_type="In-House",
        risk_tier_id=kpi_taxonomies["tier2"].value_id,
        usage_frequency_id=usage_frequency["weekly"].value_id,
        row_approval_status="approved"
    )
    db_session.add(model)
    db_session.commit()
    return model


@pytest.fixture
def kpi_active_model_no_tier(db_session, admin_user, usage_frequency):
    """Create active model WITHOUT risk tier (for edge case testing)."""
    model = Model(
        model_name="No Tier Model",
        status="Active",
        owner_id=admin_user.user_id,
        development_type="In-House",
        risk_tier_id=None,  # Deliberately null
        usage_frequency_id=usage_frequency["daily"].value_id,
        row_approval_status="approved"
    )
    db_session.add(model)
    db_session.commit()
    return model


# =============================================================================
# Validation Factory Fixtures (Gap 1 Fix)
# =============================================================================

@pytest.fixture
def kpi_create_approved_validation(db_session, admin_user, kpi_taxonomies):
    """Factory to create approved COMPREHENSIVE validation.

    FIXED: Uses kpi_taxonomies dependency instead of querying.
    Uses correct field names: requestor_id, priority_id, target_completion_date.
    """
    def _create(model, completion_date, validated_risk_tier_id=None, scorecard_overall_rating=None):
        comprehensive = kpi_taxonomies["comprehensive"]
        approved = kpi_taxonomies["status_approved"]
        priority = kpi_taxonomies["priority_standard"]

        request = ValidationRequest(
            validation_type_id=comprehensive.value_id,
            current_status_id=approved.value_id,
            completion_date=completion_date,
            requestor_id=admin_user.user_id,
            priority_id=priority.value_id,
            target_completion_date=completion_date.date() if hasattr(completion_date, 'date') else completion_date,
            validated_risk_tier_id=validated_risk_tier_id  # For 4.27 testing
        )
        db_session.add(request)
        db_session.flush()

        # Link to model
        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=model.model_id
        )
        db_session.add(link)

        # Create scorecard result if rating provided (for 4.27 testing)
        if scorecard_overall_rating:
            scorecard_result = ValidationScorecardResult(
                request_id=request.request_id,
                overall_rating=scorecard_overall_rating
            )
            db_session.add(scorecard_result)

        db_session.commit()

        return request

    return _create


@pytest.fixture
def kpi_create_interim_validation(db_session, admin_user, kpi_taxonomies):
    """Factory to create approved INTERIM validation with expiration.

    FIXED: Uses kpi_taxonomies dependency instead of querying.
    Uses correct field names and required fields.
    """
    def _create(model, expiration_date):
        interim = kpi_taxonomies["interim"]
        approved = kpi_taxonomies["status_approved"]
        priority = kpi_taxonomies["priority_standard"]
        pass_outcome = kpi_taxonomies["pass"]

        request = ValidationRequest(
            validation_type_id=interim.value_id,
            current_status_id=approved.value_id,
            completion_date=date.today(),
            requestor_id=admin_user.user_id,
            priority_id=priority.value_id,
            target_completion_date=date.today()
        )
        db_session.add(request)
        db_session.flush()

        # Link to model
        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=model.model_id
        )
        db_session.add(link)

        # Create outcome with expiration (requires overall_rating_id, executive_summary, effective_date)
        outcome = ValidationOutcome(
            request_id=request.request_id,
            overall_rating_id=pass_outcome.value_id,
            executive_summary="Interim validation approved",
            effective_date=date.today(),
            expiration_date=expiration_date
        )
        db_session.add(outcome)
        db_session.commit()

        return request

    return _create


@pytest.fixture
def kpi_create_active_validation_request(db_session, admin_user, kpi_taxonomies):
    """Factory to create an active (in-progress) validation request."""
    def _create(model, submission_received_date=None):
        comprehensive = kpi_taxonomies["comprehensive"]
        in_progress = kpi_taxonomies["status_in_progress"]
        priority = kpi_taxonomies["priority_standard"]

        request = ValidationRequest(
            validation_type_id=comprehensive.value_id,
            current_status_id=in_progress.value_id,
            submission_received_date=submission_received_date,
            requestor_id=admin_user.user_id,
            priority_id=priority.value_id,
            target_completion_date=date.today() + timedelta(days=90)
        )
        db_session.add(request)
        db_session.flush()

        link = ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=model.model_id
        )
        db_session.add(link)
        db_session.commit()

        return request

    return _create


# =============================================================================
# Metric 4.27 Fixtures (Gap 2 Fix)
# =============================================================================

@pytest.fixture
def validated_risk_tier_taxonomy(db_session):
    """Create validated risk tier taxonomy with full labels for 4.27 testing.

    CRITICAL: Production code uses validated_risk_tier.label for matrix lookup.
    The tier_mapping in _compute_metric_4_27 expects these exact labels.
    """
    taxonomy = Taxonomy(name="Validated Risk Tier", is_system=True)
    db_session.add(taxonomy)
    db_session.flush()

    tiers = {
        "high": TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="HIGH_INHERENT",
            label="High Inherent Risk",  # Exact label for tier_mapping
            sort_order=1
        ),
        "medium": TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="MEDIUM_INHERENT",
            label="Medium Inherent Risk",
            sort_order=2
        ),
        "low": TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="LOW_INHERENT",
            label="Low Inherent Risk",
            sort_order=3
        ),
        "very_low": TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="VERY_LOW_INHERENT",
            label="Very Low Inherent Risk",
            sort_order=4
        ),
    }

    db_session.add_all(tiers.values())
    db_session.commit()

    return {"taxonomy": taxonomy, **tiers}


@pytest.fixture
def kpi_create_model_with_tier_and_scorecard(
    db_session, admin_user, kpi_taxonomies, usage_frequency,
    validated_risk_tier_taxonomy, kpi_create_approved_validation
):
    """Factory to create model with validated risk tier and scorecard rating.

    FIXED (Gap 2): Creates actual TaxonomyValue record links via ID,
    not just string fields. Tests the actual production join path.

    Production path: ValidationRequest.validated_risk_tier_id ->
                     TaxonomyValue.label -> tier_mapping -> matrix lookup
    """
    def _create(tier_label: str, scorecard_rating: str):
        # Map tier_label to taxonomy value
        tier_key_map = {
            "High": "high",
            "High Inherent Risk": "high",
            "Medium": "medium",
            "Medium Inherent Risk": "medium",
            "Low": "low",
            "Low Inherent Risk": "low",
            "Very Low": "very_low",
            "Very Low Inherent Risk": "very_low",
        }
        tier_key = tier_key_map.get(tier_label)
        if not tier_key:
            raise ValueError(f"Unknown tier_label: {tier_label}")

        tier_value = validated_risk_tier_taxonomy[tier_key]

        # Create model
        model = Model(
            model_name=f"Model {tier_label} {scorecard_rating}",
            status="Active",
            owner_id=admin_user.user_id,
            development_type="In-House",
            risk_tier_id=kpi_taxonomies["tier1"].value_id,
            usage_frequency_id=usage_frequency["daily"].value_id,
            row_approval_status="approved"
        )
        db_session.add(model)
        db_session.flush()

        # Create approved validation WITH validated_risk_tier_id (ID link!)
        kpi_create_approved_validation(
            model=model,
            completion_date=date.today() - timedelta(days=30),
            validated_risk_tier_id=tier_value.value_id,  # Actual ID link
            scorecard_overall_rating=scorecard_rating  # String field
        )

        return model

    return _create


@pytest.fixture
def standard_risk_config(db_session):
    """Create standard residual risk matrix config."""
    config = ResidualRiskMapConfig(
        is_active=True,
        matrix_config={
            "matrix": {
                "High": {"Red": "High", "Yellow-": "High", "Yellow": "Medium", "Yellow+": "Medium", "Green-": "Low", "Green": "Low"},
                "Medium": {"Red": "High", "Yellow-": "Medium", "Yellow": "Medium", "Yellow+": "Low", "Green-": "Low", "Green": "Low"},
                "Low": {"Red": "Medium", "Yellow-": "Low", "Yellow": "Low", "Yellow+": "Low", "Green-": "Low", "Green": "Low"},
                "Very Low": {"Red": "Low", "Yellow-": "Low", "Yellow": "Low", "Yellow+": "Low", "Green-": "Low", "Green": "Low"},
            }
        }
    )
    db_session.add(config)
    db_session.commit()
    return config


@pytest.fixture
def kpi_create_empty_risk_config(db_session):
    """Factory to create empty residual risk config (edge case)."""
    def _create():
        config = ResidualRiskMapConfig(
            is_active=True,
            matrix_config={}  # Empty matrix
        )
        db_session.add(config)
        db_session.commit()
        return config
    return _create


# =============================================================================
# Metric 4.22 Fixtures (Gap 3 Fix)
# =============================================================================

@pytest.fixture
def kpi_create_attestation_cycle(db_session):
    """Factory to create attestation cycles for 4.22 testing.

    Uses actual AttestationCycle model fields:
    - cycle_name (not name)
    - period_start_date, period_end_date (not start_date, end_date)
    - submission_due_date
    """
    from app.models.attestation import AttestationCycle

    def _create(name: str, status: str, end_date: date):
        cycle = AttestationCycle(
            cycle_name=name,
            status=status,
            period_start_date=end_date - timedelta(days=90),
            period_end_date=end_date,
            submission_due_date=end_date + timedelta(days=30)  # Due 30 days after period end
        )
        db_session.add(cycle)
        db_session.commit()
        return cycle

    return _create


@pytest.fixture
def kpi_create_attestation_record(db_session, admin_user):
    """Factory to create attestation records for 4.22 testing."""
    from app.models.attestation import AttestationRecord
    from datetime import datetime

    def _create(cycle, model, due_date: date, attested_at_date=None):
        attested_at = datetime.combine(attested_at_date, datetime.min.time()) if attested_at_date else None
        record = AttestationRecord(
            cycle_id=cycle.cycle_id,
            model_id=model.model_id,
            attesting_user_id=admin_user.user_id,
            due_date=due_date,
            status="SUBMITTED" if attested_at else "PENDING",
            attested_at=attested_at
        )
        db_session.add(record)
        db_session.commit()
        return record

    return _create
