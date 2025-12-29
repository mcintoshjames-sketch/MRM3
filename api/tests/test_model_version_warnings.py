import pytest
from datetime import date, timedelta
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.validation import ValidationPolicy, ValidationWorkflowSLA
from app.models.taxonomy import Taxonomy, TaxonomyValue


@pytest.fixture
def version_warning_setup(db_session, taxonomy_values):
    """Setup taxonomies and policies for version warning testing."""
    # Ensure Validation Request Status taxonomy exists
    status_tax = db_session.query(Taxonomy).filter(
        Taxonomy.name == "Validation Request Status").first()
    if not status_tax:
        status_tax = Taxonomy(name="Validation Request Status", is_system=True)
        db_session.add(status_tax)
        db_session.flush()

        statuses = [("INTAKE", "Intake")]
        for i, (code, label) in enumerate(statuses):
            val = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id,
                                code=code, label=label, sort_order=i+1)
            db_session.add(val)

    # Create Validation Policy for Tier 1
    policy = ValidationPolicy(
        risk_tier_id=taxonomy_values["tier1"].value_id,
        frequency_months=12,
        model_change_lead_time_days=90,
        description="Tier 1 Policy"
    )
    db_session.add(policy)

    # Create SLA (note: complete_work_days and model_change_lead_time_days removed
    # - lead time now comes from ValidationPolicy per risk tier)
    sla = ValidationWorkflowSLA(
        workflow_type="Validation",
        assignment_days=5,
        begin_work_days=5,
        approval_days=5
    )
    db_session.add(sla)

    db_session.commit()

    return {
        "tier1_id": taxonomy_values["tier1"].value_id
    }


def test_create_version_lead_time_warning(client, db_session, test_user, auth_headers, version_warning_setup, usage_frequency):
    """Test that creating a version with insufficient lead time returns a warning."""
    # Create model
    model = Model(
        model_name="Version Warning Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=version_warning_setup["tier1_id"],
        usage_frequency_id=usage_frequency["monthly"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create version with production date 30 days from now (Policy requires 90 + SLA buffers)
    prod_date = date.today() + timedelta(days=30)

    payload = {
        "version_number": "1.0",
        "change_type": "MAJOR",
        "change_type_id": 1,
        "change_description": "Initial version",
        "production_date": prod_date.isoformat()
    }

    response = client.post(
        f"/models/{model.model_id}/versions", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()

    # Check for warning
    assert data["validation_warning"] is not None
    assert "Request submitted with insufficient lead time" in data[
        "validation_warning"]
    assert "105 days lead time" in data["validation_warning"]
    assert "30 days remain" in data["validation_warning"]


def test_create_version_sufficient_lead_time(client, db_session, test_user, auth_headers, version_warning_setup, usage_frequency):
    """Test that creating a version with sufficient lead time returns no warning."""
    # Create model
    model = Model(
        model_name="Version No Warning Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=version_warning_setup["tier1_id"],
        usage_frequency_id=usage_frequency["monthly"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create version with production date 130 days from now (beyond lead time + SLA window)
    prod_date = date.today() + timedelta(days=130)

    payload = {
        "version_number": "1.0",
        "change_type": "MAJOR",
        "change_type_id": 1,
        "change_description": "Initial version",
        "production_date": prod_date.isoformat()
    }

    response = client.post(
        f"/models/{model.model_id}/versions", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()

    # Check for NO warning
    assert data["validation_warning"] is None
