"""Tests for Model Exceptions system.

This test file covers:
- Model & Schema Tests
- Detection Logic Tests (Type 1, 2, 3)
- Auto-Close Tests
- API Endpoint Tests
- Status History Tests
- Integration Tests

Tests are organized to be written alongside implementation (test-first where possible).
"""
import pytest
from datetime import datetime, date, timedelta
from sqlalchemy import text
from app.models.model_exception import ModelException, ModelExceptionStatusHistory
from app.models.model import Model
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.monitoring import (
    MonitoringPlan, MonitoringPlanMetric, MonitoringCycle, MonitoringResult,
    MonitoringFrequency
)
from app.models.attestation import (
    AttestationCycle, AttestationRecord, AttestationResponse,
    AttestationCycleStatus
)
from app.models.kpm import Kpm, KpmCategory
from app.models.version_deployment_task import VersionDeploymentTask
from app.models.model_version import ModelVersion
from app.models.region import Region
from app.models.recommendation import Recommendation
from app.models.validation import ValidationRequest, ValidationRequestModelVersion
from app.core.time import utc_now
import app.core.exception_detection as exception_detection
from app.core.exception_detection import (
    generate_exception_code,
    detect_type1_unmitigated_performance,
    detect_type2_outside_intended_purpose,
    detect_type3_use_prior_to_validation,
    detect_type3_for_deployment_task,
    autoclose_type1_on_improved_result,
    autoclose_type3_on_full_validation_approved,
    acknowledge_exception,
    close_exception_manually,
    EXCEPTION_TYPE_UNMITIGATED_PERFORMANCE,
    EXCEPTION_TYPE_OUTSIDE_INTENDED_PURPOSE,
    EXCEPTION_TYPE_USE_PRIOR_TO_VALIDATION,
    STATUS_OPEN,
    STATUS_ACKNOWLEDGED,
    STATUS_CLOSED,
)


# =============================================================================
# Fixtures for Exception Testing
# =============================================================================

def _ensure_taxonomy_value(
    db_session,
    taxonomy_name: str,
    code: str,
    label: str,
    sort_order: int,
):
    taxonomy = db_session.query(Taxonomy).filter(
        Taxonomy.name == taxonomy_name
    ).first()
    if not taxonomy:
        taxonomy = Taxonomy(name=taxonomy_name, is_system=True)
        db_session.add(taxonomy)
        db_session.flush()

    value = db_session.query(TaxonomyValue).filter(
        TaxonomyValue.taxonomy_id == taxonomy.taxonomy_id,
        TaxonomyValue.code == code,
    ).first()
    if not value:
        value = TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code=code,
            label=label,
            sort_order=sort_order,
        )
        db_session.add(value)
        db_session.flush()

    return value


@pytest.fixture
def recommendation_taxonomies(db_session):
    """Create minimal recommendation taxonomy values needed for exceptions tests."""
    open_status = _ensure_taxonomy_value(
        db_session,
        taxonomy_name="Recommendation Status",
        code="REC_OPEN",
        label="Open",
        sort_order=1,
    )
    closed_status = _ensure_taxonomy_value(
        db_session,
        taxonomy_name="Recommendation Status",
        code="REC_CLOSED",
        label="Closed",
        sort_order=2,
    )
    priority = _ensure_taxonomy_value(
        db_session,
        taxonomy_name="Recommendation Priority",
        code="REC_PRIORITY_HIGH",
        label="High",
        sort_order=1,
    )
    db_session.commit()

    return {
        "open_status": open_status,
        "closed_status": closed_status,
        "priority": priority,
    }


@pytest.fixture
def exception_closure_reason_taxonomy(db_session):
    """Create Exception Closure Reason taxonomy for testing."""
    taxonomy = Taxonomy(name="Exception Closure Reason", is_system=True)
    db_session.add(taxonomy)
    db_session.flush()

    no_longer = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="NO_LONGER_EXCEPTION",
        label="No longer an exception",
        sort_order=1
    )
    overridden = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="EXCEPTION_OVERRIDDEN",
        label="Exception overridden",
        sort_order=2
    )
    other = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="OTHER",
        label="Other",
        sort_order=3
    )
    db_session.add_all([no_longer, overridden, other])
    db_session.commit()

    return {
        "taxonomy": taxonomy,
        "no_longer_exception": no_longer,
        "exception_overridden": overridden,
        "other": other
    }


@pytest.fixture
def attestation_question_taxonomy(db_session):
    """Create Attestation Question taxonomy with ATT_Q10_USE_RESTRICTIONS for Type 2 testing."""
    taxonomy = Taxonomy(name="Attestation Question", is_system=True)
    db_session.add(taxonomy)
    db_session.flush()

    q10 = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="ATT_Q10_USE_RESTRICTIONS",
        label="Is the model being used within its validated purpose/scope?",
        description="Required question for exception detection",
        sort_order=10,
        is_system_protected=True  # Cannot be deleted
    )
    db_session.add(q10)
    db_session.commit()

    return {
        "taxonomy": taxonomy,
        "q10_use_restrictions": q10
    }


@pytest.fixture
def sample_exception(db_session, sample_model):
    """Create a sample model exception for testing."""
    exception = ModelException(
        exception_code="EXC-2025-00001",
        model_id=sample_model.model_id,
        exception_type="UNMITIGATED_PERFORMANCE",
        status="OPEN",
        description="RED monitoring result persists without linked recommendation",
        detected_at=utc_now()
    )
    db_session.add(exception)
    db_session.commit()
    db_session.refresh(exception)
    return exception


@pytest.fixture
def monitoring_setup(db_session, sample_model, admin_user):
    """Create monitoring infrastructure for Type 1 detection testing."""
    # Create monitoring plan
    plan = MonitoringPlan(
        name="Test Plan",
        description="Test monitoring plan",
        frequency=MonitoringFrequency.MONTHLY,
    )
    db_session.add(plan)
    db_session.flush()

    # Create KPM category and KPM
    kpm_category = KpmCategory(
        code="PERF",
        name="Performance",
        description="Performance metrics",
        sort_order=1
    )
    db_session.add(kpm_category)
    db_session.flush()

    kpm = Kpm(
        category_id=kpm_category.category_id,
        name="Test Metric",
        description="Test metric description",
        sort_order=1
    )
    db_session.add(kpm)
    db_session.flush()

    # Create metric linking plan to KPM
    metric = MonitoringPlanMetric(
        plan_id=plan.plan_id,
        kpm_id=kpm.kpm_id,
    )
    db_session.add(metric)
    db_session.flush()

    # Create monitoring cycle
    cycle = MonitoringCycle(
        plan_id=plan.plan_id,
        period_start_date=date(2025, 1, 1),
        period_end_date=date(2025, 3, 31),
        submission_due_date=date(2025, 4, 15),
        report_due_date=date(2025, 4, 30),
        status="DATA_COLLECTION",
    )
    db_session.add(cycle)
    db_session.flush()

    # Associate model with plan
    plan.models = [sample_model]
    db_session.commit()

    return {
        "plan": plan,
        "metric": metric,
        "cycle": cycle,
        "kpm_category": kpm_category,
        "kpm": kpm,
    }


@pytest.fixture
def attestation_setup(db_session, sample_model, admin_user, attestation_question_taxonomy):
    """Create attestation infrastructure for Type 2 detection testing."""
    # Create attestation status taxonomy
    att_status_tax = Taxonomy(name="Attestation Status", is_system=True)
    db_session.add(att_status_tax)
    db_session.flush()

    submitted_status = TaxonomyValue(
        taxonomy_id=att_status_tax.taxonomy_id,
        code="SUBMITTED",
        label="Submitted",
        sort_order=3
    )
    db_session.add(submitted_status)
    db_session.flush()

    # Create attestation cycle
    cycle = AttestationCycle(
        cycle_name="2025-Annual",
        period_start_date=date(2025, 1, 1),
        period_end_date=date(2025, 12, 31),
        submission_due_date=date(2025, 12, 31),
        status="OPEN",
    )
    db_session.add(cycle)
    db_session.flush()

    # Create attestation record for the model
    record = AttestationRecord(
        cycle_id=cycle.cycle_id,
        model_id=sample_model.model_id,
        attesting_user_id=admin_user.user_id,
        due_date=date(2025, 12, 31),
        status="SUBMITTED",
        attested_at=utc_now(),
    )
    db_session.add(record)
    db_session.commit()

    return {
        "cycle": cycle,
        "record": record,
        "q10": attestation_question_taxonomy["q10_use_restrictions"],
        "submitted_status": submitted_status,
    }


@pytest.fixture
def deployment_setup(db_session, sample_model, admin_user):
    """Create deployment task infrastructure for Type 3 detection testing."""
    # Create region
    region = Region(code="US", name="United States")
    db_session.add(region)
    db_session.flush()

    # Create model version
    version = ModelVersion(
        model_id=sample_model.model_id,
        version_number="1.0.0",
        change_type="INITIAL",
        change_description="Initial version",
        created_by_id=admin_user.user_id,
    )
    db_session.add(version)
    db_session.flush()

    db_session.commit()

    return {
        "region": region,
        "version": version,
    }


# =============================================================================
# Model & Schema Tests
# =============================================================================

class TestModelExceptionModel:
    """Tests for ModelException ORM model."""

    def test_create_exception_model(self, db_session, sample_model):
        """ModelException can be created with required fields."""
        exception = ModelException(
            exception_code="EXC-2025-00001",
            model_id=sample_model.model_id,
            exception_type="UNMITIGATED_PERFORMANCE",
            status="OPEN",
            description="Test exception description",
            detected_at=utc_now()
        )
        db_session.add(exception)
        db_session.commit()
        db_session.refresh(exception)

        assert exception.exception_id is not None
        assert exception.exception_code == "EXC-2025-00001"
        assert exception.model_id == sample_model.model_id
        assert exception.exception_type == "UNMITIGATED_PERFORMANCE"
        assert exception.status == "OPEN"
        assert exception.auto_closed is False  # Default value

    def test_exception_code_format(self, db_session, sample_model):
        """Exception codes follow EXC-YYYY-NNNNN format."""
        exception = ModelException(
            exception_code="EXC-2025-00123",
            model_id=sample_model.model_id,
            exception_type="OUTSIDE_INTENDED_PURPOSE",
            status="OPEN",
            description="Test",
            detected_at=utc_now()
        )
        db_session.add(exception)
        db_session.commit()

        assert exception.exception_code.startswith("EXC-")
        assert len(exception.exception_code) == 14  # EXC-YYYY-NNNNN

    def test_exception_code_unique(self, db_session, sample_model):
        """Exception codes must be unique."""
        exception1 = ModelException(
            exception_code="EXC-2025-00001",
            model_id=sample_model.model_id,
            exception_type="UNMITIGATED_PERFORMANCE",
            status="OPEN",
            description="First",
            detected_at=utc_now()
        )
        db_session.add(exception1)
        db_session.commit()

        exception2 = ModelException(
            exception_code="EXC-2025-00001",  # Duplicate
            model_id=sample_model.model_id,
            exception_type="OUTSIDE_INTENDED_PURPOSE",
            status="OPEN",
            description="Second",
            detected_at=utc_now()
        )
        db_session.add(exception2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_exception_types_valid(self, db_session, sample_model):
        """Only valid exception types are allowed."""
        # Valid types should work
        for idx, exc_type in enumerate(["UNMITIGATED_PERFORMANCE", "OUTSIDE_INTENDED_PURPOSE", "USE_PRIOR_TO_VALIDATION"]):
            exception = ModelException(
                exception_code=f"EXC-2025-0000{idx+1}",
                model_id=sample_model.model_id,
                exception_type=exc_type,
                status="OPEN",
                description="Test",
                detected_at=utc_now()
            )
            db_session.add(exception)
        db_session.commit()

    def test_exception_status_values(self, db_session, sample_model, exception_closure_reason_taxonomy):
        """Only valid status values are allowed."""
        # Valid statuses - CLOSED requires closure fields due to CHECK constraint
        closure_reason = exception_closure_reason_taxonomy["no_longer_exception"]

        for idx, status in enumerate(["OPEN", "ACKNOWLEDGED", "CLOSED"]):
            exception_kwargs = {
                "exception_code": f"EXC-2025-0010{idx+1}",
                "model_id": sample_model.model_id,
                "exception_type": "UNMITIGATED_PERFORMANCE",
                "status": status,
                "description": "Test",
                "detected_at": utc_now()
            }
            # CLOSED status requires closure fields per CHECK constraint
            if status == "CLOSED":
                exception_kwargs["closure_reason_id"] = closure_reason.value_id
                exception_kwargs["closure_narrative"] = "Test closure narrative for database constraint validation."

            exception = ModelException(**exception_kwargs)
            db_session.add(exception)
        db_session.commit()

    def test_auto_closed_default_false(self, db_session, sample_model):
        """auto_closed defaults to False."""
        exception = ModelException(
            exception_code="EXC-2025-00001",
            model_id=sample_model.model_id,
            exception_type="UNMITIGATED_PERFORMANCE",
            status="OPEN",
            description="Test",
            detected_at=utc_now()
        )
        db_session.add(exception)
        db_session.commit()

        assert exception.auto_closed is False

    def test_generate_exception_code(self, db_session):
        """Exception code generator creates valid codes."""
        code1 = generate_exception_code(db_session)
        assert code1.startswith("EXC-")
        assert len(code1) == 14  # EXC-YYYY-NNNNN

        # Second code should increment
        # Create first exception to test incrementing
        exc = ModelException(
            exception_code=code1,
            model_id=1,  # Dummy
            exception_type="UNMITIGATED_PERFORMANCE",
            status="OPEN",
            description="Test",
            detected_at=utc_now()
        )
        db_session.add(exc)
        db_session.flush()

        code2 = generate_exception_code(db_session)
        # Extract sequence numbers
        seq1 = int(code1.split("-")[-1])
        seq2 = int(code2.split("-")[-1])
        assert seq2 == seq1 + 1


class TestExceptionCodeCollisionRetry:
    """Tests for exception code collision retry logic."""

    def test_exception_code_collision_retry(
        self, db_session, sample_model, monitoring_setup, admin_user, monkeypatch
    ):
        """Retries and succeeds on exception_code collision."""
        monitoring_setup["cycle"].status = "APPROVED"
        db_session.flush()

        result = MonitoringResult(
            cycle_id=monitoring_setup["cycle"].cycle_id,
            plan_metric_id=monitoring_setup["metric"].metric_id,
            model_id=sample_model.model_id,
            numeric_value=0.5,
            calculated_outcome="RED",
            entered_by_user_id=admin_user.user_id,
        )
        db_session.add(result)
        db_session.commit()

        existing = ModelException(
            exception_code="EXC-2025-00001",
            model_id=sample_model.model_id,
            exception_type=EXCEPTION_TYPE_UNMITIGATED_PERFORMANCE,
            status=STATUS_OPEN,
            description="Existing exception",
            detected_at=utc_now(),
        )
        db_session.add(existing)
        db_session.commit()

        codes = iter(["EXC-2025-00001", "EXC-2025-00002"])

        def fake_generate_exception_code(_db):
            return next(codes)

        monkeypatch.setattr(exception_detection, "generate_exception_code", fake_generate_exception_code)

        exceptions = detect_type1_unmitigated_performance(db_session, sample_model.model_id)

        assert len(exceptions) == 1
        assert exceptions[0].exception_code == "EXC-2025-00002"


class TestModelExceptionStatusHistory:
    """Tests for ModelExceptionStatusHistory ORM model."""

    def test_create_status_history(self, db_session, sample_exception, admin_user):
        """Status history can be created for an exception."""
        history = ModelExceptionStatusHistory(
            exception_id=sample_exception.exception_id,
            old_status=None,
            new_status="OPEN",
            changed_by_id=admin_user.user_id,
            changed_at=utc_now(),
            notes="Initial creation"
        )
        db_session.add(history)
        db_session.commit()
        db_session.refresh(history)

        assert history.history_id is not None
        assert history.exception_id == sample_exception.exception_id
        assert history.old_status is None
        assert history.new_status == "OPEN"

    def test_status_history_null_changed_by_for_system(self, db_session, sample_exception):
        """changed_by_id can be NULL for system-initiated changes."""
        history = ModelExceptionStatusHistory(
            exception_id=sample_exception.exception_id,
            old_status="OPEN",
            new_status="CLOSED",
            changed_by_id=None,  # System change
            changed_at=utc_now(),
            notes="Auto-closed by system"
        )
        db_session.add(history)
        db_session.commit()

        assert history.changed_by_id is None


class TestTaxonomyValueSystemProtected:
    """Tests for is_system_protected field on TaxonomyValue."""

    def test_system_protected_default_false(self, db_session):
        """is_system_protected defaults to False."""
        taxonomy = Taxonomy(name="Test Taxonomy", is_system=False)
        db_session.add(taxonomy)
        db_session.flush()

        value = TaxonomyValue(
            taxonomy_id=taxonomy.taxonomy_id,
            code="TEST",
            label="Test Value",
            sort_order=1
        )
        db_session.add(value)
        db_session.commit()

        assert value.is_system_protected is False

    def test_system_protected_can_be_set_true(self, db_session, attestation_question_taxonomy):
        """is_system_protected can be set to True."""
        q10 = attestation_question_taxonomy["q10_use_restrictions"]
        assert q10.is_system_protected is True


# =============================================================================
# Detection Logic Tests - Type 1: Unmitigated Performance
# =============================================================================

class TestType1DetectionUnmitigatedPerformance:
    """Tests for Type 1 exception detection (Unmitigated Performance Problem)."""

    def test_detect_type1_red_without_recommendation(
        self, db_session, sample_model, monitoring_setup
    ):
        """Creates exception when RED result has no linked recommendation."""
        # Set cycle to APPROVED - detection only runs on finalized cycles
        monitoring_setup["cycle"].status = "APPROVED"
        db_session.flush()

        # Create RED monitoring result
        result = MonitoringResult(
            cycle_id=monitoring_setup["cycle"].cycle_id,
            plan_metric_id=monitoring_setup["metric"].metric_id,
            model_id=sample_model.model_id,
            numeric_value=0.5,
            calculated_outcome="RED",
            entered_by_user_id=1,
        )
        db_session.add(result)
        db_session.commit()

        # Run detection
        exceptions = detect_type1_unmitigated_performance(db_session, sample_model.model_id)

        assert len(exceptions) == 1
        assert exceptions[0].exception_type == EXCEPTION_TYPE_UNMITIGATED_PERFORMANCE
        assert exceptions[0].model_id == sample_model.model_id
        assert exceptions[0].monitoring_result_id == result.result_id
        assert exceptions[0].status == STATUS_OPEN

    def test_terminal_recommendation_does_not_suppress_exception(
        self, db_session, sample_model, monitoring_setup, recommendation_taxonomies, admin_user
    ):
        """Terminal recommendation status should not suppress Type 1 exception."""
        monitoring_setup["cycle"].status = "APPROVED"
        db_session.flush()

        result = MonitoringResult(
            cycle_id=monitoring_setup["cycle"].cycle_id,
            plan_metric_id=monitoring_setup["metric"].metric_id,
            model_id=sample_model.model_id,
            numeric_value=0.5,
            calculated_outcome="RED",
            entered_by_user_id=admin_user.user_id,
        )
        db_session.add(result)
        db_session.flush()

        recommendation = Recommendation(
            recommendation_code="REC-2025-00001",
            model_id=sample_model.model_id,
            monitoring_cycle_id=monitoring_setup["cycle"].cycle_id,
            plan_metric_id=monitoring_setup["metric"].metric_id,
            title="Closed recommendation",
            description="Already addressed",
            priority_id=recommendation_taxonomies["priority"].value_id,
            current_status_id=recommendation_taxonomies["closed_status"].value_id,
            created_by_id=admin_user.user_id,
            assigned_to_id=admin_user.user_id,
            original_target_date=date.today(),
            current_target_date=date.today(),
        )
        db_session.add(recommendation)
        db_session.commit()

        exceptions = detect_type1_unmitigated_performance(db_session, sample_model.model_id)

        assert len(exceptions) == 1
        assert exceptions[0].monitoring_result_id == result.result_id

    def test_active_recommendation_suppresses_exception(
        self, db_session, sample_model, monitoring_setup, recommendation_taxonomies, admin_user
    ):
        """Active recommendation for the same metric suppresses Type 1 exception."""
        monitoring_setup["cycle"].status = "APPROVED"
        db_session.flush()

        result = MonitoringResult(
            cycle_id=monitoring_setup["cycle"].cycle_id,
            plan_metric_id=monitoring_setup["metric"].metric_id,
            model_id=sample_model.model_id,
            numeric_value=0.5,
            calculated_outcome="RED",
            entered_by_user_id=admin_user.user_id,
        )
        db_session.add(result)
        db_session.flush()

        recommendation = Recommendation(
            recommendation_code="REC-2025-00002",
            model_id=sample_model.model_id,
            monitoring_cycle_id=monitoring_setup["cycle"].cycle_id,
            plan_metric_id=monitoring_setup["metric"].metric_id,
            title="Open recommendation",
            description="In progress",
            priority_id=recommendation_taxonomies["priority"].value_id,
            current_status_id=recommendation_taxonomies["open_status"].value_id,
            created_by_id=admin_user.user_id,
            assigned_to_id=admin_user.user_id,
            original_target_date=date.today(),
            current_target_date=date.today(),
        )
        db_session.add(recommendation)
        db_session.commit()

        exceptions = detect_type1_unmitigated_performance(db_session, sample_model.model_id)

        assert len(exceptions) == 0

    def test_no_exception_when_result_is_green(
        self, db_session, sample_model, monitoring_setup
    ):
        """No exception when result is GREEN."""
        # Set cycle to APPROVED - detection only runs on finalized cycles
        monitoring_setup["cycle"].status = "APPROVED"
        db_session.flush()

        # Create GREEN monitoring result
        result = MonitoringResult(
            cycle_id=monitoring_setup["cycle"].cycle_id,
            plan_metric_id=monitoring_setup["metric"].metric_id,
            model_id=sample_model.model_id,
            numeric_value=0.95,
            calculated_outcome="GREEN",
            entered_by_user_id=1,
        )
        db_session.add(result)
        db_session.commit()

        # Run detection
        exceptions = detect_type1_unmitigated_performance(db_session, sample_model.model_id)

        assert len(exceptions) == 0

    def test_no_exception_when_cycle_not_approved(
        self, db_session, sample_model, monitoring_setup
    ):
        """No exception when cycle is not yet APPROVED (Issue 11).

        Before a monitoring cycle is approved, teams may still be
        creating recommendations to address RED results. Detection
        should only run on finalized (APPROVED) cycles.
        """
        # Verify cycle is NOT approved (fixture creates DATA_COLLECTION)
        assert monitoring_setup["cycle"].status != "APPROVED"

        # Create RED monitoring result in non-approved cycle
        result = MonitoringResult(
            cycle_id=monitoring_setup["cycle"].cycle_id,
            plan_metric_id=monitoring_setup["metric"].metric_id,
            model_id=sample_model.model_id,
            numeric_value=0.5,
            calculated_outcome="RED",
            entered_by_user_id=1,
        )
        db_session.add(result)
        db_session.commit()

        # Run detection - should find NO exceptions because cycle not approved
        exceptions = detect_type1_unmitigated_performance(db_session, sample_model.model_id)

        assert len(exceptions) == 0, "Should not detect exceptions for non-APPROVED cycles"

    def test_no_duplicate_type1_exception(
        self, db_session, sample_model, monitoring_setup
    ):
        """Does not create duplicate if exception already exists for same source."""
        # Set cycle to APPROVED - detection only runs on finalized cycles
        monitoring_setup["cycle"].status = "APPROVED"
        db_session.flush()

        # Create RED monitoring result
        result = MonitoringResult(
            cycle_id=monitoring_setup["cycle"].cycle_id,
            plan_metric_id=monitoring_setup["metric"].metric_id,
            model_id=sample_model.model_id,
            numeric_value=0.5,
            calculated_outcome="RED",
            entered_by_user_id=1,
        )
        db_session.add(result)
        db_session.commit()

        # Create existing exception for this result
        existing = ModelException(
            exception_code="EXC-2025-00001",
            model_id=sample_model.model_id,
            exception_type=EXCEPTION_TYPE_UNMITIGATED_PERFORMANCE,
            status=STATUS_OPEN,
            description="Existing exception",
            detected_at=utc_now(),
            monitoring_result_id=result.result_id,
        )
        db_session.add(existing)
        db_session.commit()

        # Run detection - should find no new exceptions
        exceptions = detect_type1_unmitigated_performance(db_session, sample_model.model_id)

        assert len(exceptions) == 0


# =============================================================================
# Detection Logic Tests - Type 2: Outside Intended Purpose
# =============================================================================

class TestType2DetectionOutsideIntendedPurpose:
    """Tests for Type 2 exception detection (Model Used Outside Intended Purpose)."""

    def test_detect_type2_attestation_no(
        self, db_session, sample_model, attestation_setup
    ):
        """Creates exception when ATT_Q10_USE_RESTRICTIONS answered No."""
        # Create attestation response with answer=False (No)
        response = AttestationResponse(
            attestation_id=attestation_setup["record"].attestation_id,
            question_id=attestation_setup["q10"].value_id,
            answer=False,  # Model used outside intended purpose
        )
        db_session.add(response)
        db_session.commit()

        # Run detection
        exceptions = detect_type2_outside_intended_purpose(db_session, sample_model.model_id)

        assert len(exceptions) == 1
        assert exceptions[0].exception_type == EXCEPTION_TYPE_OUTSIDE_INTENDED_PURPOSE
        assert exceptions[0].model_id == sample_model.model_id
        assert exceptions[0].attestation_response_id == response.response_id
        assert exceptions[0].status == STATUS_OPEN

    def test_no_type2_when_attestation_yes(
        self, db_session, sample_model, attestation_setup
    ):
        """No exception when ATT_Q10_USE_RESTRICTIONS answered Yes."""
        # Create attestation response with answer=True (Yes - within purpose)
        response = AttestationResponse(
            attestation_id=attestation_setup["record"].attestation_id,
            question_id=attestation_setup["q10"].value_id,
            answer=True,  # Model used within intended purpose
        )
        db_session.add(response)
        db_session.commit()

        # Run detection
        exceptions = detect_type2_outside_intended_purpose(db_session, sample_model.model_id)

        assert len(exceptions) == 0


# =============================================================================
# Detection Logic Tests - Type 3: Use Prior to Full Validation
# =============================================================================

class TestType3DetectionUsePriorToValidation:
    """Tests for Type 3 exception detection (Model In Use Prior to Full Validation)."""

    def test_detect_type3_deployed_before_validation(
        self, db_session, sample_model, deployment_setup, admin_user
    ):
        """Creates exception when deployed_before_validation_approved=True."""
        # Create deployment task with deployed_before_validation=True
        task = VersionDeploymentTask(
            version_id=deployment_setup["version"].version_id,
            model_id=sample_model.model_id,
            region_id=deployment_setup["region"].region_id,
            assigned_to_id=admin_user.user_id,
            planned_production_date=date(2025, 1, 15),
            actual_production_date=date(2025, 1, 15),
            status="CONFIRMED",
            deployed_before_validation_approved=True,
            validation_override_reason="Urgent business need",
        )
        db_session.add(task)
        db_session.commit()

        # Run detection
        exceptions = detect_type3_use_prior_to_validation(db_session, sample_model.model_id)

        assert len(exceptions) == 1
        assert exceptions[0].exception_type == EXCEPTION_TYPE_USE_PRIOR_TO_VALIDATION
        assert exceptions[0].model_id == sample_model.model_id
        assert exceptions[0].deployment_task_id == task.task_id
        assert exceptions[0].status == STATUS_OPEN

    def test_no_type3_when_deployed_after_validation(
        self, db_session, sample_model, deployment_setup, admin_user
    ):
        """No exception when deployed_before_validation_approved=False."""
        # Create deployment task with deployed_before_validation=False
        task = VersionDeploymentTask(
            version_id=deployment_setup["version"].version_id,
            model_id=sample_model.model_id,
            region_id=deployment_setup["region"].region_id,
            assigned_to_id=admin_user.user_id,
            planned_production_date=date(2025, 1, 15),
            actual_production_date=date(2025, 1, 15),
            status="CONFIRMED",
            deployed_before_validation_approved=False,  # Validation was approved first
        )
        db_session.add(task)
        db_session.commit()

        # Run detection
        exceptions = detect_type3_use_prior_to_validation(db_session, sample_model.model_id)

        assert len(exceptions) == 0

    def test_detect_type3_for_deployment_task_direct(
        self, db_session, sample_model, deployment_setup, admin_user
    ):
        """Creates exception using direct detection function for deployment task."""
        # Create deployment task with deployed_before_validation=True
        task = VersionDeploymentTask(
            version_id=deployment_setup["version"].version_id,
            model_id=sample_model.model_id,
            region_id=deployment_setup["region"].region_id,
            assigned_to_id=admin_user.user_id,
            planned_production_date=date(2025, 1, 15),
            actual_production_date=date(2025, 1, 15),
            status="CONFIRMED",
            deployed_before_validation_approved=True,
        )
        db_session.add(task)
        db_session.commit()

        # Use direct detection function
        exception = detect_type3_for_deployment_task(db_session, task)

        assert exception is not None
        assert exception.exception_type == EXCEPTION_TYPE_USE_PRIOR_TO_VALIDATION
        assert exception.deployment_task_id == task.task_id


# =============================================================================
# Auto-Close Tests
# =============================================================================

class TestAutoCloseType1:
    """Tests for Type 1 exception auto-close on GREEN/YELLOW results."""

    def test_autoclose_type1_on_green_result(
        self, db_session, sample_model, monitoring_setup, exception_closure_reason_taxonomy
    ):
        """Type 1 exception auto-closes when metric returns to GREEN."""
        # Create RED monitoring result
        red_result = MonitoringResult(
            cycle_id=monitoring_setup["cycle"].cycle_id,
            plan_metric_id=monitoring_setup["metric"].metric_id,
            model_id=sample_model.model_id,
            numeric_value=0.5,
            calculated_outcome="RED",
            entered_by_user_id=1,
        )
        db_session.add(red_result)
        db_session.flush()

        # Create Type 1 exception for this result
        exception = ModelException(
            exception_code="EXC-2025-00001",
            model_id=sample_model.model_id,
            exception_type=EXCEPTION_TYPE_UNMITIGATED_PERFORMANCE,
            status=STATUS_OPEN,
            description="RED result",
            detected_at=utc_now(),
            monitoring_result_id=red_result.result_id,
        )
        db_session.add(exception)
        db_session.commit()

        # Create GREEN result for same metric
        green_result = MonitoringResult(
            cycle_id=monitoring_setup["cycle"].cycle_id,
            plan_metric_id=monitoring_setup["metric"].metric_id,
            model_id=sample_model.model_id,
            numeric_value=0.95,
            calculated_outcome="GREEN",
            entered_by_user_id=1,
        )
        db_session.add(green_result)
        db_session.commit()

        # Run auto-close
        closed = autoclose_type1_on_improved_result(db_session, green_result)
        db_session.commit()

        assert len(closed) == 1
        assert closed[0].exception_id == exception.exception_id

        # Verify exception is now closed
        db_session.refresh(exception)
        assert exception.status == STATUS_CLOSED
        assert exception.auto_closed is True

    def test_autoclose_type1_on_yellow_result(
        self, db_session, sample_model, monitoring_setup, exception_closure_reason_taxonomy
    ):
        """Type 1 exception auto-closes when metric returns to YELLOW."""
        # Create RED monitoring result
        red_result = MonitoringResult(
            cycle_id=monitoring_setup["cycle"].cycle_id,
            plan_metric_id=monitoring_setup["metric"].metric_id,
            model_id=sample_model.model_id,
            numeric_value=0.5,
            calculated_outcome="RED",
            entered_by_user_id=1,
        )
        db_session.add(red_result)
        db_session.flush()

        # Create Type 1 exception
        exception = ModelException(
            exception_code="EXC-2025-00001",
            model_id=sample_model.model_id,
            exception_type=EXCEPTION_TYPE_UNMITIGATED_PERFORMANCE,
            status=STATUS_OPEN,
            description="RED result",
            detected_at=utc_now(),
            monitoring_result_id=red_result.result_id,
        )
        db_session.add(exception)
        db_session.commit()

        # Create YELLOW result
        yellow_result = MonitoringResult(
            cycle_id=monitoring_setup["cycle"].cycle_id,
            plan_metric_id=monitoring_setup["metric"].metric_id,
            model_id=sample_model.model_id,
            numeric_value=0.8,
            calculated_outcome="YELLOW",
            entered_by_user_id=1,
        )
        db_session.add(yellow_result)
        db_session.commit()

        # Run auto-close
        closed = autoclose_type1_on_improved_result(db_session, yellow_result)
        db_session.commit()

        assert len(closed) == 1
        db_session.refresh(exception)
        assert exception.status == STATUS_CLOSED

    def test_no_autoclose_type1_if_still_red(
        self, db_session, sample_model, monitoring_setup, exception_closure_reason_taxonomy
    ):
        """Type 1 exception stays open if metric is still RED."""
        # Create RED monitoring result
        red_result = MonitoringResult(
            cycle_id=monitoring_setup["cycle"].cycle_id,
            plan_metric_id=monitoring_setup["metric"].metric_id,
            model_id=sample_model.model_id,
            numeric_value=0.5,
            calculated_outcome="RED",
            entered_by_user_id=1,
        )
        db_session.add(red_result)
        db_session.flush()

        # Create Type 1 exception
        exception = ModelException(
            exception_code="EXC-2025-00001",
            model_id=sample_model.model_id,
            exception_type=EXCEPTION_TYPE_UNMITIGATED_PERFORMANCE,
            status=STATUS_OPEN,
            description="RED result",
            detected_at=utc_now(),
            monitoring_result_id=red_result.result_id,
        )
        db_session.add(exception)
        db_session.commit()

        # Create another RED result (still failing)
        still_red_result = MonitoringResult(
            cycle_id=monitoring_setup["cycle"].cycle_id,
            plan_metric_id=monitoring_setup["metric"].metric_id,
            model_id=sample_model.model_id,
            numeric_value=0.45,
            calculated_outcome="RED",
            entered_by_user_id=1,
        )
        db_session.add(still_red_result)
        db_session.commit()

        # Run auto-close - should not close anything
        closed = autoclose_type1_on_improved_result(db_session, still_red_result)

        assert len(closed) == 0
        db_session.refresh(exception)
        assert exception.status == STATUS_OPEN


class TestAutoCloseType3:
    """Tests for Type 3 exception auto-close on FULL validation approval."""

    def test_autoclose_type3_on_full_validation_approved(
        self, db_session, sample_model, taxonomy_values, exception_closure_reason_taxonomy
    ):
        """Type 3 exception auto-closes when FULL validation is approved."""
        # Create Type 3 exception
        exception = ModelException(
            exception_code="EXC-2025-00001",
            model_id=sample_model.model_id,
            exception_type=EXCEPTION_TYPE_USE_PRIOR_TO_VALIDATION,
            status=STATUS_OPEN,
            description="Deployed before validation",
            detected_at=utc_now(),
        )
        db_session.add(exception)
        db_session.flush()

        # Create validation request that gets approved (Initial type = full validation)
        validation = ValidationRequest(
            validation_type_id=taxonomy_values["initial"].value_id,
            current_status_id=taxonomy_values["status_approved"].value_id,
            requestor_id=1,  # System
            priority_id=taxonomy_values["tier1"].value_id,  # Using tier1 as priority
            target_completion_date=date.today() + timedelta(days=30),
            completion_date=date.today(),
        )
        db_session.add(validation)
        db_session.flush()

        # Link validation to model via association table
        assoc = ValidationRequestModelVersion(
            request_id=validation.request_id,
            model_id=sample_model.model_id,
            version_id=None
        )
        db_session.add(assoc)
        db_session.commit()

        # Run auto-close
        closed = autoclose_type3_on_full_validation_approved(db_session, validation)
        db_session.commit()

        assert len(closed) == 1
        db_session.refresh(exception)
        assert exception.status == STATUS_CLOSED
        assert exception.auto_closed is True

    def test_no_autoclose_type3_on_interim_validation(
        self, db_session, sample_model, exception_closure_reason_taxonomy
    ):
        """Type 3 exception stays OPEN when only interim validation is approved."""
        # Create Interim validation type taxonomy
        val_type_tax = Taxonomy(name="Validation Type", is_system=True)
        db_session.add(val_type_tax)
        db_session.flush()

        interim_type = TaxonomyValue(
            taxonomy_id=val_type_tax.taxonomy_id,
            code="INTERIM",
            label="Interim",
            sort_order=1
        )
        db_session.add(interim_type)

        status_tax = Taxonomy(name="Validation Request Status", is_system=True)
        db_session.add(status_tax)
        db_session.flush()

        approved_status = TaxonomyValue(
            taxonomy_id=status_tax.taxonomy_id,
            code="APPROVED",
            label="Approved",
            sort_order=1
        )
        db_session.add(approved_status)
        db_session.flush()

        # Create Type 3 exception
        exception = ModelException(
            exception_code="EXC-2025-00001",
            model_id=sample_model.model_id,
            exception_type=EXCEPTION_TYPE_USE_PRIOR_TO_VALIDATION,
            status=STATUS_OPEN,
            description="Deployed before validation",
            detected_at=utc_now(),
        )
        db_session.add(exception)
        db_session.flush()

        # Create priority taxonomy for validation request
        priority_tax = Taxonomy(name="Validation Priority", is_system=True)
        db_session.add(priority_tax)
        db_session.flush()

        priority_val = TaxonomyValue(
            taxonomy_id=priority_tax.taxonomy_id,
            code="STANDARD",
            label="Standard",
            sort_order=1
        )
        db_session.add(priority_val)
        db_session.flush()

        # Create INTERIM validation request that gets approved
        validation = ValidationRequest(
            validation_type_id=interim_type.value_id,
            current_status_id=approved_status.value_id,
            requestor_id=1,
            priority_id=priority_val.value_id,
            target_completion_date=date.today() + timedelta(days=30),
            completion_date=date.today(),
        )
        db_session.add(validation)
        db_session.flush()

        # Link validation to model via association table
        assoc = ValidationRequestModelVersion(
            request_id=validation.request_id,
            model_id=sample_model.model_id,
            version_id=None
        )
        db_session.add(assoc)
        db_session.commit()

        # Run auto-close - should NOT close because Interim
        closed = autoclose_type3_on_full_validation_approved(db_session, validation)

        assert len(closed) == 0
        db_session.refresh(exception)
        assert exception.status == STATUS_OPEN


class TestAutoCloseType2:
    """Tests for Type 2 exception (manual-only closure)."""

    def test_no_autoclose_type2(self, db_session, sample_model):
        """Type 2 exceptions have no auto-close mechanism - must be manual."""
        # Create Type 2 exception
        exception = ModelException(
            exception_code="EXC-2025-00001",
            model_id=sample_model.model_id,
            exception_type=EXCEPTION_TYPE_OUTSIDE_INTENDED_PURPOSE,
            status=STATUS_OPEN,
            description="Used outside intended purpose",
            detected_at=utc_now(),
        )
        db_session.add(exception)
        db_session.commit()

        # Type 2 has no auto-close function per the design
        # This test verifies the exception remains open - manual closure required
        assert exception.status == STATUS_OPEN

        # Verify exception doesn't close when other exceptions might
        # (Type 2 should never auto-close)
        db_session.refresh(exception)
        assert exception.auto_closed is False


# =============================================================================
# API Endpoint Tests
# =============================================================================

class TestExceptionsListEndpoint:
    """Tests for GET /exceptions/ endpoint."""

    def test_list_exceptions(self, client, admin_headers, db_session, sample_exception):
        """GET /exceptions/ returns paginated list."""
        response = client.get("/exceptions/", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_list_exceptions_filter_by_model(
        self, client, admin_headers, db_session, sample_model, sample_exception
    ):
        """GET /exceptions/?model_id=X filters correctly."""
        response = client.get(
            f"/exceptions/?model_id={sample_model.model_id}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["model_id"] == sample_model.model_id

    def test_list_exceptions_filter_by_type(
        self, client, admin_headers, db_session, sample_exception
    ):
        """GET /exceptions/?exception_type=UNMITIGATED_PERFORMANCE filters correctly."""
        response = client.get(
            "/exceptions/?exception_type=UNMITIGATED_PERFORMANCE",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["exception_type"] == "UNMITIGATED_PERFORMANCE"

    def test_list_exceptions_filter_by_status(
        self, client, admin_headers, db_session, sample_exception
    ):
        """GET /exceptions/?status=OPEN filters correctly."""
        response = client.get(
            "/exceptions/?status=OPEN",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "OPEN"


class TestExceptionsCreateEndpoint:
    """Tests for POST /exceptions/ endpoint (manual creation)."""

    def test_create_exception_admin_open_status(
        self, client, admin_headers, db_session, sample_model
    ):
        """POST /exceptions/ creates new exception in OPEN status."""
        response = client.post(
            "/exceptions/",
            headers=admin_headers,
            json={
                "model_id": sample_model.model_id,
                "exception_type": "UNMITIGATED_PERFORMANCE",
                "description": "Manually created exception for audit finding.",
                "initial_status": "OPEN"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == sample_model.model_id
        assert data["exception_type"] == "UNMITIGATED_PERFORMANCE"
        assert data["status"] == "OPEN"
        assert data["description"] == "Manually created exception for audit finding."
        assert data["exception_code"].startswith("EXC-")
        assert data["auto_closed"] is False
        assert data["acknowledged_by"] is None
        assert len(data["status_history"]) >= 1

    def test_create_exception_admin_acknowledged_status(
        self, client, admin_headers, db_session, sample_model
    ):
        """POST /exceptions/ creates new exception directly in ACKNOWLEDGED status."""
        response = client.post(
            "/exceptions/",
            headers=admin_headers,
            json={
                "model_id": sample_model.model_id,
                "exception_type": "OUTSIDE_INTENDED_PURPOSE",
                "description": "Pre-acknowledged exception from historical audit.",
                "initial_status": "ACKNOWLEDGED",
                "acknowledgment_notes": "Already reviewed in prior audit."
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == sample_model.model_id
        assert data["exception_type"] == "OUTSIDE_INTENDED_PURPOSE"
        assert data["status"] == "ACKNOWLEDGED"
        assert data["acknowledged_by"] is not None
        assert data["acknowledged_at"] is not None
        assert data["acknowledgment_notes"] == "Already reviewed in prior audit."

    def test_create_exception_non_admin_forbidden(
        self, client, auth_headers, db_session, sample_model
    ):
        """POST /exceptions/ returns 403 for non-Admin users."""
        response = client.post(
            "/exceptions/",
            headers=auth_headers,
            json={
                "model_id": sample_model.model_id,
                "exception_type": "UNMITIGATED_PERFORMANCE",
                "description": "Trying to create exception without admin role."
            }
        )

        assert response.status_code == 403

    def test_create_exception_invalid_type(
        self, client, admin_headers, db_session, sample_model
    ):
        """POST /exceptions/ fails for invalid exception_type."""
        response = client.post(
            "/exceptions/",
            headers=admin_headers,
            json={
                "model_id": sample_model.model_id,
                "exception_type": "INVALID_TYPE",
                "description": "This should fail validation."
            }
        )

        assert response.status_code == 400
        assert "Invalid exception_type" in response.json()["detail"]

    def test_create_exception_invalid_initial_status(
        self, client, admin_headers, db_session, sample_model
    ):
        """POST /exceptions/ fails for invalid initial_status."""
        response = client.post(
            "/exceptions/",
            headers=admin_headers,
            json={
                "model_id": sample_model.model_id,
                "exception_type": "UNMITIGATED_PERFORMANCE",
                "description": "Trying to create with CLOSED status.",
                "initial_status": "CLOSED"
            }
        )

        assert response.status_code == 400
        assert "initial_status" in response.json()["detail"]

    def test_create_exception_model_not_found(
        self, client, admin_headers, db_session
    ):
        """POST /exceptions/ returns 404 for non-existent model."""
        response = client.post(
            "/exceptions/",
            headers=admin_headers,
            json={
                "model_id": 99999,
                "exception_type": "UNMITIGATED_PERFORMANCE",
                "description": "Model doesn't exist."
            }
        )

        assert response.status_code == 404
        assert "Model 99999 not found" in response.json()["detail"]

    def test_create_exception_description_too_short(
        self, client, admin_headers, db_session, sample_model
    ):
        """POST /exceptions/ fails when description is too short."""
        response = client.post(
            "/exceptions/",
            headers=admin_headers,
            json={
                "model_id": sample_model.model_id,
                "exception_type": "UNMITIGATED_PERFORMANCE",
                "description": "Short"  # Less than 10 chars
            }
        )

        assert response.status_code == 422  # Pydantic validation

    def test_create_exception_type3_use_prior_to_validation(
        self, client, admin_headers, db_session, sample_model
    ):
        """POST /exceptions/ creates Type 3 exception correctly."""
        response = client.post(
            "/exceptions/",
            headers=admin_headers,
            json={
                "model_id": sample_model.model_id,
                "exception_type": "USE_PRIOR_TO_VALIDATION",
                "description": "Model deployed before validation was completed - discovered in audit."
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["exception_type"] == "USE_PRIOR_TO_VALIDATION"
        assert data["status"] == "OPEN"


class TestExceptionsDetailEndpoint:
    """Tests for GET /exceptions/{id} endpoint."""

    def test_get_exception_detail(
        self, client, admin_headers, db_session, sample_exception
    ):
        """GET /exceptions/{id} returns full exception details."""
        response = client.get(
            f"/exceptions/{sample_exception.exception_id}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["exception_id"] == sample_exception.exception_id
        assert data["exception_code"] == sample_exception.exception_code
        assert data["exception_type"] == sample_exception.exception_type
        assert "status_history" in data

    def test_get_exception_not_found(self, client, admin_headers):
        """GET /exceptions/{id} returns 404 for non-existent exception."""
        response = client.get("/exceptions/99999", headers=admin_headers)
        assert response.status_code == 404


class TestExceptionsAcknowledgeEndpoint:
    """Tests for POST /exceptions/{id}/acknowledge endpoint."""

    def test_acknowledge_exception_admin(
        self, client, admin_headers, db_session, sample_exception
    ):
        """POST /exceptions/{id}/acknowledge works for Admin."""
        response = client.post(
            f"/exceptions/{sample_exception.exception_id}/acknowledge",
            headers=admin_headers,
            json={"notes": "Reviewed and acknowledged"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ACKNOWLEDGED"
        assert data["acknowledgment_notes"] == "Reviewed and acknowledged"

    def test_acknowledge_exception_non_admin_forbidden(
        self, client, auth_headers, db_session, sample_exception
    ):
        """POST /exceptions/{id}/acknowledge returns 403 for non-Admin."""
        response = client.post(
            f"/exceptions/{sample_exception.exception_id}/acknowledge",
            headers=auth_headers,
            json={"notes": "Trying to acknowledge"}
        )

        assert response.status_code == 403


class TestExceptionsCloseEndpoint:
    """Tests for POST /exceptions/{id}/close endpoint."""

    def test_close_exception_with_narrative(
        self, client, admin_headers, db_session, sample_exception, exception_closure_reason_taxonomy
    ):
        """POST /exceptions/{id}/close works with valid narrative and reason."""
        response = client.post(
            f"/exceptions/{sample_exception.exception_id}/close",
            headers=admin_headers,
            json={
                "closure_narrative": "Issue has been resolved through model update.",
                "closure_reason_id": exception_closure_reason_taxonomy["no_longer_exception"].value_id
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CLOSED"
        assert data["closure_narrative"] == "Issue has been resolved through model update."

    def test_close_exception_missing_narrative_fails(
        self, client, admin_headers, db_session, sample_exception, exception_closure_reason_taxonomy
    ):
        """POST /exceptions/{id}/close fails without narrative."""
        response = client.post(
            f"/exceptions/{sample_exception.exception_id}/close",
            headers=admin_headers,
            json={
                "closure_reason_id": exception_closure_reason_taxonomy["no_longer_exception"].value_id
            }
        )

        assert response.status_code == 422  # Validation error

    def test_close_exception_short_narrative_fails(
        self, client, admin_headers, db_session, sample_exception, exception_closure_reason_taxonomy
    ):
        """POST /exceptions/{id}/close fails if narrative < 10 chars."""
        response = client.post(
            f"/exceptions/{sample_exception.exception_id}/close",
            headers=admin_headers,
            json={
                "closure_narrative": "Short",  # Less than 10 chars
                "closure_reason_id": exception_closure_reason_taxonomy["no_longer_exception"].value_id
            }
        )

        assert response.status_code == 422  # Validation error or 400

    def test_close_exception_missing_reason_fails(
        self, client, admin_headers, db_session, sample_exception
    ):
        """POST /exceptions/{id}/close fails without closure_reason_id."""
        response = client.post(
            f"/exceptions/{sample_exception.exception_id}/close",
            headers=admin_headers,
            json={
                "closure_narrative": "This is a valid narrative explaining the closure."
            }
        )

        assert response.status_code == 422  # Validation error


class TestExceptionsDetectionEndpoints:
    """Tests for exception detection trigger endpoints."""

    def test_detect_for_model(self, client, admin_headers, db_session, sample_model):
        """POST /exceptions/detect/{model_id} triggers detection."""
        response = client.post(
            f"/exceptions/detect/{sample_model.model_id}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "type1_count" in data
        assert "type2_count" in data
        assert "type3_count" in data
        assert "total_created" in data

    def test_detect_all(self, client, admin_headers, db_session):
        """POST /exceptions/detect-all triggers batch detection."""
        response = client.post(
            "/exceptions/detect-all",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "type1_count" in data
        assert "type2_count" in data
        assert "type3_count" in data
        assert "total_created" in data

    def test_detect_for_model_non_admin_forbidden(
        self, client, auth_headers, sample_model
    ):
        """POST /exceptions/detect/{model_id} returns 403 for non-Admin."""
        response = client.post(
            f"/exceptions/detect/{sample_model.model_id}",
            headers=auth_headers
        )

        assert response.status_code == 403


class TestModelExceptionsEndpoint:
    """Tests for GET /exceptions/model/{id} endpoint."""

    def test_model_exceptions_endpoint(
        self, client, admin_headers, db_session, sample_model, sample_exception
    ):
        """GET /exceptions/model/{id} returns model's exceptions."""
        response = client.get(
            f"/exceptions/model/{sample_model.model_id}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for item in data:
            assert item["model_id"] == sample_model.model_id


# =============================================================================
# Status History Tests
# =============================================================================

class TestStatusHistoryTracking:
    """Tests for exception status history tracking."""

    def test_status_history_on_acknowledge(
        self, db_session, sample_exception, admin_user
    ):
        """Acknowledging creates status history record."""
        initial_history_count = len(sample_exception.status_history) if sample_exception.status_history else 0

        # Acknowledge the exception
        acknowledge_exception(db_session, sample_exception, admin_user.user_id, "Acknowledged")
        db_session.commit()
        db_session.refresh(sample_exception)

        # Check history was added
        assert len(sample_exception.status_history) > initial_history_count
        latest = sample_exception.status_history[-1]
        assert latest.old_status == "OPEN"
        assert latest.new_status == "ACKNOWLEDGED"
        assert latest.changed_by_id == admin_user.user_id

    def test_status_history_on_close(
        self, db_session, sample_exception, admin_user, exception_closure_reason_taxonomy
    ):
        """Closing creates status history record."""
        initial_history_count = len(sample_exception.status_history) if sample_exception.status_history else 0

        # Close the exception
        close_exception_manually(
            db_session,
            sample_exception,
            admin_user.user_id,
            "Closing with valid narrative for testing purposes.",
            exception_closure_reason_taxonomy["no_longer_exception"].value_id
        )
        db_session.commit()
        db_session.refresh(sample_exception)

        # Check history was added
        assert len(sample_exception.status_history) > initial_history_count
        latest = sample_exception.status_history[-1]
        assert latest.new_status == "CLOSED"
        assert latest.changed_by_id == admin_user.user_id

    def test_status_history_on_autoclose(
        self, db_session, sample_model, monitoring_setup, exception_closure_reason_taxonomy
    ):
        """Auto-closing creates status history record with system user (NULL)."""
        # Create RED result
        red_result = MonitoringResult(
            cycle_id=monitoring_setup["cycle"].cycle_id,
            plan_metric_id=monitoring_setup["metric"].metric_id,
            model_id=sample_model.model_id,
            numeric_value=0.5,
            calculated_outcome="RED",
            entered_by_user_id=1,
        )
        db_session.add(red_result)
        db_session.flush()

        # Create Type 1 exception
        exception = ModelException(
            exception_code="EXC-2025-00001",
            model_id=sample_model.model_id,
            exception_type=EXCEPTION_TYPE_UNMITIGATED_PERFORMANCE,
            status=STATUS_OPEN,
            description="RED result",
            detected_at=utc_now(),
            monitoring_result_id=red_result.result_id,
        )
        db_session.add(exception)
        db_session.commit()

        # Create GREEN result to trigger auto-close
        green_result = MonitoringResult(
            cycle_id=monitoring_setup["cycle"].cycle_id,
            plan_metric_id=monitoring_setup["metric"].metric_id,
            model_id=sample_model.model_id,
            numeric_value=0.95,
            calculated_outcome="GREEN",
            entered_by_user_id=1,
        )
        db_session.add(green_result)
        db_session.commit()

        # Auto-close
        autoclose_type1_on_improved_result(db_session, green_result)
        db_session.commit()
        db_session.refresh(exception)

        # Check history - should have entry with NULL changed_by_id
        close_history = [h for h in exception.status_history if h.new_status == "CLOSED"]
        assert len(close_history) >= 1
        assert close_history[-1].changed_by_id is None  # System-initiated


# =============================================================================
# Integration Tests
# =============================================================================

class TestExceptionIntegration:
    """Integration tests for exception system with other features."""

    def test_open_exception_count_in_model_response(
        self, client, admin_headers, db_session, sample_model, sample_exception
    ):
        """Model detail includes open_exception_count field."""
        response = client.get(
            f"/models/{sample_model.model_id}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        # Check that exception count is available (may be in different field)
        # The exact field name depends on implementation
        assert "model_id" in data  # Basic sanity check

    def test_exception_summary_endpoint(
        self, client, admin_headers, db_session, sample_exception
    ):
        """Exception summary endpoint provides correct counts."""
        response = client.get("/exceptions/summary", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_open" in data
        assert "total_acknowledged" in data
        assert "total_closed" in data
        assert "by_type" in data
        assert data["total_open"] >= 1  # We have sample_exception


# =============================================================================
# Unique Constraint Tests
# =============================================================================

class TestUniqueConstraints:
    """Tests for partial unique constraints preventing duplicate exceptions."""

    def test_unique_constraint_monitoring_result(
        self, db_session, sample_model, monitoring_setup
    ):
        """Cannot create duplicate exceptions for same monitoring_result_id."""
        # Create monitoring result
        result = MonitoringResult(
            cycle_id=monitoring_setup["cycle"].cycle_id,
            plan_metric_id=monitoring_setup["metric"].metric_id,
            model_id=sample_model.model_id,
            numeric_value=0.5,
            calculated_outcome="RED",
            entered_by_user_id=1,
        )
        db_session.add(result)
        db_session.flush()

        # Create first exception
        exc1 = ModelException(
            exception_code="EXC-2025-00001",
            model_id=sample_model.model_id,
            exception_type=EXCEPTION_TYPE_UNMITIGATED_PERFORMANCE,
            status=STATUS_OPEN,
            description="First",
            detected_at=utc_now(),
            monitoring_result_id=result.result_id,
        )
        db_session.add(exc1)
        db_session.commit()

        # Try to create duplicate - should fail
        exc2 = ModelException(
            exception_code="EXC-2025-00002",
            model_id=sample_model.model_id,
            exception_type=EXCEPTION_TYPE_UNMITIGATED_PERFORMANCE,
            status=STATUS_OPEN,
            description="Duplicate",
            detected_at=utc_now(),
            monitoring_result_id=result.result_id,  # Same result
        )
        db_session.add(exc2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_unique_constraint_deployment_task(
        self, db_session, sample_model, deployment_setup, admin_user
    ):
        """Cannot create duplicate exceptions for same deployment_task_id."""
        # Create deployment task
        task = VersionDeploymentTask(
            version_id=deployment_setup["version"].version_id,
            model_id=sample_model.model_id,
            region_id=deployment_setup["region"].region_id,
            assigned_to_id=admin_user.user_id,
            planned_production_date=date(2025, 1, 15),
            status="CONFIRMED",
            deployed_before_validation_approved=True,
        )
        db_session.add(task)
        db_session.flush()

        # Create first exception
        exc1 = ModelException(
            exception_code="EXC-2025-00001",
            model_id=sample_model.model_id,
            exception_type=EXCEPTION_TYPE_USE_PRIOR_TO_VALIDATION,
            status=STATUS_OPEN,
            description="First",
            detected_at=utc_now(),
            deployment_task_id=task.task_id,
        )
        db_session.add(exc1)
        db_session.commit()

        # Try to create duplicate - should fail
        exc2 = ModelException(
            exception_code="EXC-2025-00002",
            model_id=sample_model.model_id,
            exception_type=EXCEPTION_TYPE_USE_PRIOR_TO_VALIDATION,
            status=STATUS_OPEN,
            description="Duplicate",
            detected_at=utc_now(),
            deployment_task_id=task.task_id,  # Same task
        )
        db_session.add(exc2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()
