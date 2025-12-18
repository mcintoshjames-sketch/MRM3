import pytest
from datetime import date, datetime, timedelta
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.validation import ValidationPolicy, ValidationWorkflowSLA, ValidationRequest, ValidationRequestModelVersion
from app.models.taxonomy import Taxonomy, TaxonomyValue

# Setup fixtures for this test module


@pytest.fixture
def validation_setup(db_session, taxonomy_values):
    """Setup taxonomies and policies for validation testing."""
    # Add Validation Request Status taxonomy if not exists
    status_tax = db_session.query(Taxonomy).filter(
        Taxonomy.name == "Validation Request Status").first()
    if not status_tax:
        status_tax = Taxonomy(name="Validation Request Status", is_system=True)
        db_session.add(status_tax)
        db_session.flush()

        statuses = [
            ("INTAKE", "Intake"),
            ("PLANNING", "Planning"),
            ("IN_PROGRESS", "In Progress"),
            ("REVIEW", "Review"),
            ("PENDING_APPROVAL", "Pending Approval"),
            ("APPROVED", "Approved"),
            ("ON_HOLD", "On Hold"),
            ("CANCELLED", "Cancelled")
        ]

        for i, (code, label) in enumerate(statuses):
            val = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id,
                                code=code, label=label, sort_order=i+1)
            db_session.add(val)

    # Add Priority taxonomy if not exists
    priority_tax = db_session.query(Taxonomy).filter(
        Taxonomy.name == "Priority").first()
    if not priority_tax:
        priority_tax = Taxonomy(name="Priority", is_system=True)
        db_session.add(priority_tax)
        db_session.flush()

        priorities = [("HIGH", "High"), ("MEDIUM", "Medium"), ("LOW", "Low")]
        for i, (code, label) in enumerate(priorities):
            val = TaxonomyValue(
                taxonomy_id=priority_tax.taxonomy_id, code=code, label=label, sort_order=i+1)
            db_session.add(val)

    # Create Validation Policy for Tier 1
    policy = ValidationPolicy(
        risk_tier_id=taxonomy_values["tier1"].value_id,
        frequency_months=12,
        model_change_lead_time_days=90,
        description="Tier 1 Policy"
    )
    db_session.add(policy)

    # Create SLA (model_change_lead_time_days is now on ValidationPolicy, not SLA)
    sla = ValidationWorkflowSLA(
        workflow_type="Validation"
    )
    db_session.add(sla)

    db_session.commit()

    # Return useful IDs
    return {
        "tier1_id": taxonomy_values["tier1"].value_id,
        "initial_type_id": taxonomy_values["initial"].value_id,
        "priority_id": db_session.query(TaxonomyValue).filter(TaxonomyValue.code == "MEDIUM").first().value_id
    }


def test_implementation_date_error(client, db_session, test_user, auth_headers, validation_setup, usage_frequency):
    """Test that an error is generated when target date is after implementation date."""
    # Create model
    model = Model(
        model_name="Impl Date Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=validation_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create version with implementation date 10 days from now
    impl_date = date.today() + timedelta(days=10)
    version = ModelVersion(
        model_id=model.model_id,
        version_number="1.0",
        change_type="MAJOR",
        change_type_id=1,
        change_description="Initial version",
        created_by_id=test_user.user_id,
        production_date=impl_date,
        status="DRAFT"
    )
    db_session.add(version)
    db_session.commit()

    # Target completion date = 20 days from now (AFTER implementation)
    target_date = date.today() + timedelta(days=20)

    payload = {
        "model_ids": [model.model_id],
        "validation_type_id": validation_setup["initial_type_id"],
        "priority_id": validation_setup["priority_id"],
        "target_completion_date": target_date.isoformat(),
        "model_versions": {str(model.model_id): version.version_id},
        "check_warnings": True
    }

    response = client.post(
        "/validation-workflow/requests/check-warnings", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["has_warnings"] is True
    assert data["can_proceed"] is False  # Blocking error

    warning = next(
        (w for w in data["warnings"] if w["warning_type"] == "IMPLEMENTATION_DATE"), None)
    assert warning is not None
    assert warning["severity"] == "ERROR"
    assert "after the implementation date" in warning["message"]


def test_create_request_with_versions(client, db_session, test_user, auth_headers, validation_setup, usage_frequency):
    """Test creating a validation request with specific model versions."""
    # Create model
    model = Model(
        model_name="Version Tracking Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=validation_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create version
    version = ModelVersion(
        model_id=model.model_id,
        version_number="1.0",
        change_type="MAJOR",
        change_type_id=1,
        change_description="Initial version",
        created_by_id=test_user.user_id,
        status="DRAFT"
    )
    db_session.add(version)
    db_session.commit()

    target_date = date.today() + timedelta(days=30)

    payload = {
        "model_ids": [model.model_id],
        "validation_type_id": validation_setup["initial_type_id"],
        "priority_id": validation_setup["priority_id"],
        "target_completion_date": target_date.isoformat(),
        "model_versions": {str(model.model_id): version.version_id},
        "check_warnings": False
    }

    response = client.post("/validation-workflow/requests/",
                           json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()

    request_id = data["request_id"]

    # Verify database records
    assoc = db_session.query(ValidationRequestModelVersion).filter(
        ValidationRequestModelVersion.request_id == request_id,
        ValidationRequestModelVersion.model_id == model.model_id
    ).first()

    assert assoc is not None
    assert assoc.version_id == version.version_id


def test_check_warnings_flag_in_create(client, db_session, test_user, auth_headers, validation_setup, usage_frequency):
    """Test that check_warnings=True in create endpoint returns warnings and does NOT create request."""
    # Create model
    model = Model(
        model_name="Flag Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=validation_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create version with implementation date conflict
    impl_date = date.today()
    version = ModelVersion(
        model_id=model.model_id,
        version_number="1.0",
        change_type="MAJOR",
        change_type_id=1,
        change_description="Initial version",
        created_by_id=test_user.user_id,
        production_date=impl_date,
        status="DRAFT"
    )
    db_session.add(version)
    db_session.commit()

    # Target date after implementation
    target_date = date.today() + timedelta(days=10)

    payload = {
        "model_ids": [model.model_id],
        "validation_type_id": validation_setup["initial_type_id"],
        "priority_id": validation_setup["priority_id"],
        "target_completion_date": target_date.isoformat(),
        "model_versions": {str(model.model_id): version.version_id},
        "check_warnings": True
    }

    # Call create endpoint
    response = client.post("/validation-workflow/requests/",
                           json=payload, headers=auth_headers)
    # It returns 201 but with warning response schema
    assert response.status_code == 201
    data = response.json()

    # Should return warnings response, not request response
    assert "has_warnings" in data
    assert data["has_warnings"] is True
    assert "request_id" not in data

    # Verify no request was created in DB
    count = db_session.query(ValidationRequest).count()
    assert count == 0


# ============================================================================
# Phase 5.2: Additional TDD Tests for Validation Workflow Warnings
# ============================================================================

def test_lead_time_warning(client, db_session, test_user, auth_headers, validation_setup, usage_frequency):
    """
    TDD Test: LEAD_TIME warning should be generated when target completion date
    does not meet the model_change_lead_time_days requirement from ValidationPolicy.

    Scenario: Policy requires 90 days lead time, but target is only 30 days out.
    Expected: WARNING (not blocking) with LEAD_TIME type.
    """
    # Create model with Tier 1 risk (90 day lead time in policy)
    model = Model(
        model_name="Lead Time Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=validation_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create version with implementation date 60 days out
    impl_date = date.today() + timedelta(days=60)
    version = ModelVersion(
        model_id=model.model_id,
        version_number="1.0",
        change_type="MAJOR",
        change_type_id=1,
        change_description="Initial version",
        created_by_id=test_user.user_id,
        production_date=impl_date,
        status="DRAFT"
    )
    db_session.add(version)
    db_session.commit()

    # Target completion = 30 days (policy requires 90 days lead time before production)
    # Production is 60 days out, so validation should complete at least 90 days before = impossible
    # Therefore, target of 30 days violates the lead time requirement
    target_date = date.today() + timedelta(days=30)

    payload = {
        "model_ids": [model.model_id],
        "validation_type_id": validation_setup["initial_type_id"],
        "priority_id": validation_setup["priority_id"],
        "target_completion_date": target_date.isoformat(),
        "model_versions": {str(model.model_id): version.version_id},
        "check_warnings": True
    }

    response = client.post(
        "/validation-workflow/requests/check-warnings", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["has_warnings"] is True
    # Lead time is a warning, not a blocking error
    assert data["can_proceed"] is True

    warning = next(
        (w for w in data["warnings"] if w["warning_type"] == "LEAD_TIME"), None)
    assert warning is not None
    assert warning["severity"] == "WARNING"
    assert warning["model_id"] == model.model_id
    assert "lead time" in warning["message"].lower()
    assert warning["details"]["required_lead_time_days"] == 90


def test_revalidation_overdue_warning(client, db_session, test_user, auth_headers, validation_setup, usage_frequency):
    """
    TDD Test: REVALIDATION_OVERDUE warning when target completion date would cause
    the model to be overdue for its periodic revalidation.

    Scenario: Model had validation 11 months ago, policy requires 12 months,
    target completion 3 months away would make it overdue.
    """
    # Create model with Tier 1 risk (12 month revalidation frequency)
    model = Model(
        model_name="Revalidation Test Model",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id,
        risk_tier_id=validation_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Get APPROVED status
    approved_status = db_session.query(TaxonomyValue).filter(
        TaxonomyValue.code == "APPROVED").first()

    # Create a previous approved validation that completed 11 months ago
    from app.core.time import utc_now
    past_date = utc_now() - timedelta(days=330)  # ~11 months ago

    prior_request = ValidationRequest(
        validation_type_id=validation_setup["initial_type_id"],
        priority_id=validation_setup["priority_id"],
        current_status_id=approved_status.value_id,
        target_completion_date=past_date.date(),
        completion_date=past_date.date(),
        requestor_id=test_user.user_id
    )
    db_session.add(prior_request)
    db_session.flush()

    # Update timestamps to simulate past approval
    prior_request.created_at = past_date
    prior_request.updated_at = past_date

    # Link model to prior request
    db_session.execute(
        ValidationRequestModelVersion.__table__.insert().values(
            request_id=prior_request.request_id,
            model_id=model.model_id,
            version_id=None
        )
    )
    db_session.commit()

    # Target completion = 90 days from now
    # Last validation was 330 days ago
    # Policy requires 12 months (360 days) + 30 day grace = 390 days
    # At target completion (330 + 90 = 420 days since last), it would be overdue
    target_date = date.today() + timedelta(days=90)

    payload = {
        "model_ids": [model.model_id],
        "validation_type_id": validation_setup["initial_type_id"],
        "priority_id": validation_setup["priority_id"],
        "target_completion_date": target_date.isoformat(),
        "check_warnings": True
    }

    response = client.post(
        "/validation-workflow/requests/check-warnings", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["has_warnings"] is True
    assert data["can_proceed"] is True  # WARNING, not ERROR

    warning = next(
        (w for w in data["warnings"] if w["warning_type"] == "REVALIDATION_OVERDUE"), None)
    assert warning is not None
    assert warning["severity"] == "WARNING"
    assert warning["model_id"] == model.model_id
    assert "overdue" in warning["message"].lower()


def test_no_warnings_when_dates_valid(client, db_session, test_user, auth_headers, validation_setup, usage_frequency):
    """
    TDD Test: No warnings should be returned when all dates are valid.

    Scenario: Target completion is well before implementation date and meets lead time.
    Expected: has_warnings=False, can_proceed=True, empty warnings list.
    """
    # Create model
    model = Model(
        model_name="Valid Dates Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=validation_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create version with implementation date 180 days out (plenty of lead time)
    impl_date = date.today() + timedelta(days=180)
    version = ModelVersion(
        model_id=model.model_id,
        version_number="1.0",
        change_type="MAJOR",
        change_type_id=1,
        change_description="Initial version",
        created_by_id=test_user.user_id,
        production_date=impl_date,
        status="DRAFT"
    )
    db_session.add(version)
    db_session.commit()

    # Target completion = 60 days (well before 180 day implementation, meets 90 day lead time)
    target_date = date.today() + timedelta(days=60)

    payload = {
        "model_ids": [model.model_id],
        "validation_type_id": validation_setup["initial_type_id"],
        "priority_id": validation_setup["priority_id"],
        "target_completion_date": target_date.isoformat(),
        "model_versions": {str(model.model_id): version.version_id},
        "check_warnings": True
    }

    response = client.post(
        "/validation-workflow/requests/check-warnings", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["has_warnings"] is False
    assert data["can_proceed"] is True
    assert len(data["warnings"]) == 0


def test_multiple_warnings_returned(client, db_session, test_user, auth_headers, validation_setup, usage_frequency):
    """
    TDD Test: Multiple warnings can be returned for different issues.

    Scenario: Multiple models in request, each with different warning types.
    Expected: All warnings returned in the response.
    """
    # Create first model with implementation date conflict (ERROR)
    model1 = Model(
        model_name="Multi Warning Model 1",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=validation_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model1)
    db_session.commit()

    # Version with implementation date 10 days out (will conflict with 30 day target)
    impl_date1 = date.today() + timedelta(days=10)
    version1 = ModelVersion(
        model_id=model1.model_id,
        version_number="1.0",
        change_type="MAJOR",
        change_type_id=1,
        change_description="Initial version",
        created_by_id=test_user.user_id,
        production_date=impl_date1,
        status="DRAFT"
    )
    db_session.add(version1)

    # Create second model with lead time issue (WARNING)
    model2 = Model(
        model_name="Multi Warning Model 2",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=validation_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model2)
    db_session.commit()

    # Version with implementation date 45 days out (lead time violation with 30 day target)
    impl_date2 = date.today() + timedelta(days=45)
    version2 = ModelVersion(
        model_id=model2.model_id,
        version_number="1.0",
        change_type="MAJOR",
        change_type_id=1,
        change_description="Initial version",
        created_by_id=test_user.user_id,
        production_date=impl_date2,
        status="DRAFT"
    )
    db_session.add(version2)
    db_session.commit()

    # Target completion = 30 days
    target_date = date.today() + timedelta(days=30)

    payload = {
        "model_ids": [model1.model_id, model2.model_id],
        "validation_type_id": validation_setup["initial_type_id"],
        "priority_id": validation_setup["priority_id"],
        "target_completion_date": target_date.isoformat(),
        "model_versions": {
            str(model1.model_id): version1.version_id,
            str(model2.model_id): version2.version_id
        },
        "check_warnings": True
    }

    response = client.post(
        "/validation-workflow/requests/check-warnings", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["has_warnings"] is True
    # Model1 has ERROR (impl date conflict), so can_proceed should be False
    assert data["can_proceed"] is False

    # Should have at least 2 warnings (one per model)
    assert len(data["warnings"]) >= 2

    # Verify we have an IMPLEMENTATION_DATE error for model1
    impl_warning = next(
        (w for w in data["warnings"]
         if w["warning_type"] == "IMPLEMENTATION_DATE" and w["model_id"] == model1.model_id),
        None)
    assert impl_warning is not None
    assert impl_warning["severity"] == "ERROR"

    # Verify we have a LEAD_TIME warning for model2
    lead_warning = next(
        (w for w in data["warnings"]
         if w["warning_type"] == "LEAD_TIME" and w["model_id"] == model2.model_id),
        None)
    assert lead_warning is not None
    assert lead_warning["severity"] == "WARNING"


def test_can_proceed_true_with_only_warnings(client, db_session, test_user, auth_headers, validation_setup, usage_frequency):
    """
    TDD Test: can_proceed should be True when there are only WARNINGs (no ERRORs).

    This allows users to acknowledge warnings and proceed with request creation.
    """
    # Create model with lead time issue only (no implementation date conflict)
    model = Model(
        model_name="Warning Only Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=validation_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Version with implementation date 50 days out
    # Target of 40 days is before implementation (no ERROR)
    # But 50 - 40 = 10 days, less than 90 day lead time requirement (WARNING)
    impl_date = date.today() + timedelta(days=50)
    version = ModelVersion(
        model_id=model.model_id,
        version_number="1.0",
        change_type="MAJOR",
        change_type_id=1,
        change_description="Initial version",
        created_by_id=test_user.user_id,
        production_date=impl_date,
        status="DRAFT"
    )
    db_session.add(version)
    db_session.commit()

    # Target completion = 40 days (before 50 day implementation, but violates 90 day lead time)
    target_date = date.today() + timedelta(days=40)

    payload = {
        "model_ids": [model.model_id],
        "validation_type_id": validation_setup["initial_type_id"],
        "priority_id": validation_setup["priority_id"],
        "target_completion_date": target_date.isoformat(),
        "model_versions": {str(model.model_id): version.version_id},
        "check_warnings": True
    }

    response = client.post(
        "/validation-workflow/requests/check-warnings", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["has_warnings"] is True
    assert data["can_proceed"] is True  # Only warnings, no errors

    # Verify all warnings have severity WARNING, not ERROR
    for warning in data["warnings"]:
        assert warning["severity"] in ["WARNING", "INFO"], \
            f"Expected WARNING or INFO severity, got {warning['severity']}"


def test_force_create_with_warnings(client, db_session, test_user, auth_headers, validation_setup, usage_frequency):
    """
    TDD Test: Request can be created with force_create=True even when warnings exist.

    This allows users to acknowledge warnings and proceed with creation.
    Blocking ERRORs should still prevent creation even with force_create.
    """
    # Create model with lead time warning only (not blocking error)
    model = Model(
        model_name="Force Create Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=validation_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Version with implementation 50 days out, target 40 days (lead time warning)
    impl_date = date.today() + timedelta(days=50)
    version = ModelVersion(
        model_id=model.model_id,
        version_number="1.0",
        change_type="MAJOR",
        change_type_id=1,
        change_description="Initial version",
        created_by_id=test_user.user_id,
        production_date=impl_date,
        status="DRAFT"
    )
    db_session.add(version)
    db_session.commit()

    target_date = date.today() + timedelta(days=40)

    payload = {
        "model_ids": [model.model_id],
        "validation_type_id": validation_setup["initial_type_id"],
        "priority_id": validation_setup["priority_id"],
        "target_completion_date": target_date.isoformat(),
        "model_versions": {str(model.model_id): version.version_id},
        "check_warnings": False,
        "force_create": True  # Acknowledge warnings and proceed
    }

    response = client.post("/validation-workflow/requests/",
                           json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()

    # Should have created the request despite warnings
    assert "request_id" in data
    request_id = data["request_id"]

    # Verify request exists in database
    request = db_session.query(ValidationRequest).filter(
        ValidationRequest.request_id == request_id).first()
    assert request is not None


def test_force_create_blocked_by_error(client, db_session, test_user, auth_headers, validation_setup, usage_frequency):
    """
    TDD Test: Request creation should be blocked even with force_create when ERROR exists.

    IMPLEMENTATION_DATE errors are blocking and cannot be bypassed.
    """
    # Create model
    model = Model(
        model_name="Force Create Blocked Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=validation_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Version with implementation date 10 days out - target 30 days will be AFTER (ERROR)
    impl_date = date.today() + timedelta(days=10)
    version = ModelVersion(
        model_id=model.model_id,
        version_number="1.0",
        change_type="MAJOR",
        change_type_id=1,
        change_description="Initial version",
        created_by_id=test_user.user_id,
        production_date=impl_date,
        status="DRAFT"
    )
    db_session.add(version)
    db_session.commit()

    target_date = date.today() + timedelta(days=30)  # AFTER implementation

    payload = {
        "model_ids": [model.model_id],
        "validation_type_id": validation_setup["initial_type_id"],
        "priority_id": validation_setup["priority_id"],
        "target_completion_date": target_date.isoformat(),
        "model_versions": {str(model.model_id): version.version_id},
        "check_warnings": False,
        "force_create": True  # Try to force despite ERROR
    }

    response = client.post("/validation-workflow/requests/",
                           json=payload, headers=auth_headers)
    # Should be blocked - either 400 Bad Request or return warnings response
    assert response.status_code in [400, 201]  # 201 with warning response

    if response.status_code == 201:
        data = response.json()
        # Should return warnings response, not request
        assert "has_warnings" in data
        assert data["can_proceed"] is False
        assert "request_id" not in data
    else:
        data = response.json()
        assert "error" in data.get("detail", "").lower() or "blocking" in data.get("detail", "").lower()


def test_warnings_include_model_and_version_details(client, db_session, test_user, auth_headers, validation_setup, usage_frequency):
    """
    TDD Test: Warning responses should include complete model and version information.
    """
    model = Model(
        model_name="Detail Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=validation_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    impl_date = date.today() + timedelta(days=10)
    version = ModelVersion(
        model_id=model.model_id,
        version_number="2.5.1",
        change_type="MAJOR",
        change_type_id=1,
        change_description="Test version",
        created_by_id=test_user.user_id,
        production_date=impl_date,
        status="DRAFT"
    )
    db_session.add(version)
    db_session.commit()

    target_date = date.today() + timedelta(days=30)  # After implementation

    payload = {
        "model_ids": [model.model_id],
        "validation_type_id": validation_setup["initial_type_id"],
        "priority_id": validation_setup["priority_id"],
        "target_completion_date": target_date.isoformat(),
        "model_versions": {str(model.model_id): version.version_id},
        "check_warnings": True
    }

    response = client.post(
        "/validation-workflow/requests/check-warnings", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["has_warnings"] is True
    warning = data["warnings"][0]

    # Verify model details
    assert warning["model_id"] == model.model_id
    assert warning["model_name"] == "Detail Test Model"
    assert warning["version_number"] == "2.5.1"

    # Verify details dict contains useful information
    assert "details" in warning
    assert warning["details"] is not None