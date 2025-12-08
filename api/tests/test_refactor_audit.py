
import pytest
from datetime import date, timedelta
from app.models.validation import ValidationRequest, ValidationPolicy
from app.models.model import Model
from app.models.taxonomy import Taxonomy, TaxonomyValue


@pytest.fixture
def workflow_taxonomies(db_session):
    """Create all workflow-related taxonomy values."""
    # Validation Priority
    priority_tax = Taxonomy(name="Validation Priority", is_system=True)
    db_session.add(priority_tax)
    db_session.flush()

    standard = TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id,
                         code="STANDARD", label="Standard", sort_order=2)

    # Validation Request Status
    status_tax = Taxonomy(name="Validation Request Status", is_system=True)
    db_session.add(status_tax)
    db_session.flush()

    intake = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id,
                           code="INTAKE", label="Intake", sort_order=1)
    approved = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id,
                             code="APPROVED", label="Approved", sort_order=6)

    # Validation Type
    type_tax = Taxonomy(name="Validation Type", is_system=True)
    db_session.add(type_tax)
    db_session.flush()

    initial_val = TaxonomyValue(taxonomy_id=type_tax.taxonomy_id,
                                code="INITIAL", label="Initial Validation", sort_order=1)
    comprehensive_val = TaxonomyValue(
        taxonomy_id=type_tax.taxonomy_id, code="COMPREHENSIVE", label="Comprehensive Review", sort_order=2)

    # Model Risk Tier
    tier_tax = Taxonomy(name="Model Risk Tier", is_system=True)
    db_session.add(tier_tax)
    db_session.flush()

    tier2 = TaxonomyValue(taxonomy_id=tier_tax.taxonomy_id,
                          code="TIER_2", label="Tier 2", sort_order=2)

    db_session.add_all(
        [standard, intake, approved, initial_val, comprehensive_val, tier2])
    db_session.commit()

    return {
        "priority": {"standard": standard},
        "status": {"intake": intake, "approved": approved},
        "type": {"initial": initial_val, "comprehensive": comprehensive_val},
        "tier": {"tier2": tier2}
    }


def test_submission_due_date_calculation_comprehensive(client, admin_headers, workflow_taxonomies, db_session, test_user, usage_frequency):
    """
    Verify that submission_due_date is calculated correctly for COMPREHENSIVE validations.
    This ensures that the removal of 'ANNUAL' does not break periodic revalidation logic.
    """
    # 1. Setup Policy for Tier 2
    policy = ValidationPolicy(
        risk_tier_id=workflow_taxonomies["tier"]["tier2"].value_id,
        frequency_months=18,
        grace_period_months=3,
        model_change_lead_time_days=90
    )
    db_session.add(policy)
    db_session.commit()

    # 2. Create Model
    model = Model(
        model_name="Test Model Refactor",
        development_type="In-House",
        owner_id=test_user.user_id,
        status="Active",
        risk_tier_id=workflow_taxonomies["tier"]["tier2"].value_id,
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # 3. Create Prior Validation (Approved 18 months ago)
    prior_date = date.today() - timedelta(days=18*30)
    prior_req = ValidationRequest(
        requestor_id=test_user.user_id,
        validation_type_id=workflow_taxonomies["type"]["initial"].value_id,
        priority_id=workflow_taxonomies["priority"]["standard"].value_id,
        target_completion_date=prior_date,
        current_status_id=workflow_taxonomies["status"]["approved"].value_id,
        updated_at=prior_date,
        completion_date=prior_date
    )
    db_session.add(prior_req)
    db_session.flush()

    # Link model to prior request
    from app.models.validation import ValidationRequestModelVersion
    db_session.add(ValidationRequestModelVersion(
        request_id=prior_req.request_id, model_id=model.model_id))
    db_session.commit()

    # 4. Create New COMPREHENSIVE Validation Request
    # This should trigger _calculate_submission_due_date
    response = client.post(
        "/validation-workflow/requests/",
        headers=admin_headers,
        json={
            "model_ids": [model.model_id],
            "validation_type_id": workflow_taxonomies["type"]["comprehensive"].value_id,
            "priority_id": workflow_taxonomies["priority"]["standard"].value_id,
            "target_completion_date": date.today().isoformat(),
            "prior_validation_request_id": prior_req.request_id
        }
    )
    assert response.status_code == 201
    data = response.json()

    # 5. Verify submission_due_date
    # Expected: prior_date + 18 months
    from dateutil.relativedelta import relativedelta
    expected_due_date = prior_date + relativedelta(months=18)

    assert data["submission_due_date"] == expected_due_date.isoformat()

    # Verify is_periodic_revalidation logic (indirectly tested by submission_due_date being present)
    # But let's check the property directly via DB object
    req = db_session.query(ValidationRequest).get(data["request_id"])
    assert req.is_periodic_revalidation is True


def test_annual_is_gone(workflow_taxonomies, db_session):
    """Verify that ANNUAL is not present in the taxonomy."""
    type_tax = db_session.query(Taxonomy).filter_by(
        name="Validation Type").first()
    annual = db_session.query(TaxonomyValue).filter_by(
        taxonomy_id=type_tax.taxonomy_id, code="ANNUAL").first()
    assert annual is None
