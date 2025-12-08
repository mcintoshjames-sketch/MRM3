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
