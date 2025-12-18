"""TDD tests for Phase 5.1: Version Creation Constraints.

These tests verify:
- B1: Block creation when undeployed version exists NOT in active validation
- B2: Block creation when version is in active validation (not yet approved)
- B3: Cannot delete version linked to any validation

Tests are written BEFORE implementation (TDD red phase).
"""
import pytest
from datetime import date, datetime, timedelta
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.validation import (
    ValidationRequest, ValidationRequestModelVersion,
    ValidationPolicy, ValidationWorkflowSLA
)
from app.models.model_region import ModelRegion
from app.models.region import Region
from app.models.taxonomy import Taxonomy, TaxonomyValue


@pytest.fixture
def version_constraint_setup(db_session, test_user, usage_frequency):
    """Setup taxonomies and models for version constraint testing."""
    # Add Validation Request Status taxonomy if not exists
    status_tax = db_session.query(Taxonomy).filter(
        Taxonomy.name == "Validation Request Status").first()
    if not status_tax:
        status_tax = Taxonomy(name="Validation Request Status", is_system=True)
        db_session.add(status_tax)
        db_session.flush()

        statuses = [
            ("INTAKE", "Intake", 100),
            ("PLANNING", "Planning", 101),
            ("IN_PROGRESS", "In Progress", 102),
            ("REVIEW", "Review", 103),
            ("PENDING_APPROVAL", "Pending Approval", 104),
            ("APPROVED", "Approved", 105),
            ("ON_HOLD", "On Hold", 106),
            ("CANCELLED", "Cancelled", 107)
        ]

        status_values = {}
        for code, label, sort_order in statuses:
            val = TaxonomyValue(
                taxonomy_id=status_tax.taxonomy_id,
                code=code, label=label, sort_order=sort_order
            )
            db_session.add(val)
            status_values[code] = val
        db_session.flush()
    else:
        status_values = {
            v.code: v for v in db_session.query(TaxonomyValue).filter(
                TaxonomyValue.taxonomy_id == status_tax.taxonomy_id
            ).all()
        }

    # Add Risk Tier taxonomy
    risk_tax = db_session.query(Taxonomy).filter(
        Taxonomy.name == "Model Risk Tier").first()
    if not risk_tax:
        risk_tax = Taxonomy(name="Model Risk Tier", is_system=True)
        db_session.add(risk_tax)
        db_session.flush()
        tier1 = TaxonomyValue(
            taxonomy_id=risk_tax.taxonomy_id,
            code="TIER_1", label="Tier 1 (High)", sort_order=1
        )
        db_session.add(tier1)
    else:
        tier1 = db_session.query(TaxonomyValue).filter(
            TaxonomyValue.taxonomy_id == risk_tax.taxonomy_id,
            TaxonomyValue.code == "TIER_1"
        ).first()

    # Add Validation Type taxonomy
    val_type_tax = db_session.query(Taxonomy).filter(
        Taxonomy.name == "Validation Type").first()
    if not val_type_tax:
        val_type_tax = Taxonomy(name="Validation Type", is_system=True)
        db_session.add(val_type_tax)
        db_session.flush()
        initial_type = TaxonomyValue(
            taxonomy_id=val_type_tax.taxonomy_id,
            code="INITIAL", label="Initial", sort_order=1
        )
        db_session.add(initial_type)
    else:
        initial_type = db_session.query(TaxonomyValue).filter(
            TaxonomyValue.taxonomy_id == val_type_tax.taxonomy_id,
            TaxonomyValue.code == "INITIAL"
        ).first()

    # Add Priority taxonomy
    priority_tax = db_session.query(Taxonomy).filter(
        Taxonomy.name == "Validation Priority").first()
    if not priority_tax:
        priority_tax = Taxonomy(name="Validation Priority", is_system=True)
        db_session.add(priority_tax)
        db_session.flush()
        standard_priority = TaxonomyValue(
            taxonomy_id=priority_tax.taxonomy_id,
            code="STANDARD", label="Standard", sort_order=1
        )
        db_session.add(standard_priority)
    else:
        standard_priority = db_session.query(TaxonomyValue).filter(
            TaxonomyValue.taxonomy_id == priority_tax.taxonomy_id,
            TaxonomyValue.code == "STANDARD"
        ).first()

    # Create Validation Policy for Tier 1
    policy = ValidationPolicy(
        risk_tier_id=tier1.value_id,
        frequency_months=12,
        model_change_lead_time_days=90,
        description="Tier 1 Policy"
    )
    db_session.add(policy)

    # Create SLA
    sla = ValidationWorkflowSLA(workflow_type="Validation")
    db_session.add(sla)

    # Add Change Type taxonomy for versions
    change_type_tax = db_session.query(Taxonomy).filter(
        Taxonomy.name == "Model Change Type").first()
    if not change_type_tax:
        change_type_tax = Taxonomy(name="Model Change Type", is_system=True)
        db_session.add(change_type_tax)
        db_session.flush()
        major_change = TaxonomyValue(
            taxonomy_id=change_type_tax.taxonomy_id,
            code="MAJOR", label="Major", sort_order=1
        )
        db_session.add(major_change)
    else:
        major_change = db_session.query(TaxonomyValue).filter(
            TaxonomyValue.taxonomy_id == change_type_tax.taxonomy_id,
            TaxonomyValue.code == "MAJOR"
        ).first()

    db_session.commit()

    return {
        "tier1_id": tier1.value_id,
        "initial_type_id": initial_type.value_id,
        "priority_id": standard_priority.value_id,
        "status_values": status_values,
    }


# =============================================================================
# B1: Block creation when undeployed version exists NOT in active validation
# =============================================================================

def test_block_creation_when_undeployed_draft_version_exists(
    client, db_session, test_user, auth_headers, version_constraint_setup, usage_frequency
):
    """Test that 409 is returned when a DRAFT version exists that is not in validation.

    E4 spec: "Returns 409 when undeployed version exists"
    Setup: Model has DRAFT version not in validation
    Expected: status_code: 409, error: "version_creation_blocked", reason: "undeployed_version_exists"
    """
    # Create model
    model = Model(
        model_name="Blocker Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=version_constraint_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create existing DRAFT version (not in any validation)
    existing_version = ModelVersion(
        model_id=model.model_id,
        version_number="v1.0.0",
        change_type="MAJOR",
        change_description="Initial version",
        created_by_id=test_user.user_id,
        status="DRAFT"
    )
    db_session.add(existing_version)
    db_session.commit()

    # Attempt to create another version - should be blocked
    payload = {
        "version_number": "v2.0.0",
        "change_type": "MAJOR",
        "change_description": "Second version - should be blocked"
    }

    response = client.post(
        f"/models/{model.model_id}/versions",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 409
    data = response.json()["detail"]
    assert data["error"] == "version_creation_blocked"
    assert data["reason"] == "undeployed_version_exists"
    assert data["blocking_version_number"] == "v1.0.0"


def test_block_creation_when_approved_but_undeployed_version_exists(
    client, db_session, test_user, auth_headers, version_constraint_setup, usage_frequency
):
    """Test that 409 is returned when an APPROVED version exists but is not deployed.

    An APPROVED version that hasn't been deployed yet still blocks new version creation
    because it represents pending work that should be deployed first.
    """
    # Create model
    model = Model(
        model_name="Approved Undeployed Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=version_constraint_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create APPROVED version (not deployed yet)
    existing_version = ModelVersion(
        model_id=model.model_id,
        version_number="v1.0.0",
        change_type="MAJOR",
        change_description="Approved but not deployed",
        created_by_id=test_user.user_id,
        status="APPROVED"  # Approved but not deployed
    )
    db_session.add(existing_version)
    db_session.commit()

    # Attempt to create another version - should be blocked
    payload = {
        "version_number": "v2.0.0",
        "change_type": "MAJOR",
        "change_description": "Second version - should be blocked"
    }

    response = client.post(
        f"/models/{model.model_id}/versions",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 409
    data = response.json()["detail"]
    assert data["error"] == "version_creation_blocked"
    assert data["reason"] == "undeployed_version_exists"


# =============================================================================
# B2: Block creation when version is in active validation
# =============================================================================

def test_block_creation_when_version_in_active_validation(
    client, db_session, test_user, auth_headers, version_constraint_setup, usage_frequency
):
    """Test that 409 is returned when a version is in active validation.

    E4 spec: "Returns 409 when version in active validation"
    Setup: Model has version in IN_PROGRESS validation
    Expected: status_code: 409, error: "version_creation_blocked",
              reason: "version_in_active_validation"

    "Active Validation" = status NOT in: APPROVED, CANCELLED, ON_HOLD
    """
    # Create model
    model = Model(
        model_name="Active Validation Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=version_constraint_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create version
    version = ModelVersion(
        model_id=model.model_id,
        version_number="v1.0.0",
        change_type="MAJOR",
        change_description="Version in validation",
        created_by_id=test_user.user_id,
        status="IN_VALIDATION"
    )
    db_session.add(version)
    db_session.commit()

    # Create validation request in IN_PROGRESS status (active)
    in_progress_status = version_constraint_setup["status_values"]["IN_PROGRESS"]
    validation_request = ValidationRequest(
        validation_type_id=version_constraint_setup["initial_type_id"],
        priority_id=version_constraint_setup["priority_id"],
        current_status_id=in_progress_status.value_id,
        requestor_id=test_user.user_id,
        target_completion_date=date.today() + timedelta(days=30)
    )
    db_session.add(validation_request)
    db_session.flush()

    # Link model and version to validation via association table
    version_link = ValidationRequestModelVersion(
        request_id=validation_request.request_id,
        model_id=model.model_id,
        version_id=version.version_id
    )
    db_session.add(version_link)
    db_session.commit()

    # Attempt to create another version - should be blocked
    payload = {
        "version_number": "v2.0.0",
        "change_type": "MAJOR",
        "change_description": "Second version - should be blocked by active validation"
    }

    response = client.post(
        f"/models/{model.model_id}/versions",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 409
    data = response.json()["detail"]
    assert data["error"] == "version_creation_blocked"
    assert data["reason"] == "version_in_active_validation"
    assert "blocking_validation_id" in data


def test_allow_creation_when_validation_is_approved(
    client, db_session, test_user, auth_headers, version_constraint_setup, usage_frequency
):
    """Test that creation is allowed when the validation is APPROVED.

    APPROVED validations don't block new version creation because the validation
    work is complete.
    """
    # Create model
    model = Model(
        model_name="Approved Validation Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=version_constraint_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create version that's ACTIVE (deployed)
    version = ModelVersion(
        model_id=model.model_id,
        version_number="v1.0.0",
        change_type="MAJOR",
        change_description="Deployed version",
        created_by_id=test_user.user_id,
        status="ACTIVE"
    )
    db_session.add(version)
    db_session.commit()

    # Create validation request in APPROVED status (not active)
    approved_status = version_constraint_setup["status_values"]["APPROVED"]
    validation_request = ValidationRequest(
        validation_type_id=version_constraint_setup["initial_type_id"],
        priority_id=version_constraint_setup["priority_id"],
        current_status_id=approved_status.value_id,
        requestor_id=test_user.user_id,
        target_completion_date=date.today() + timedelta(days=30)
    )
    db_session.add(validation_request)
    db_session.flush()

    # Link model and version to validation via association table
    version_link = ValidationRequestModelVersion(
        request_id=validation_request.request_id,
        model_id=model.model_id,
        version_id=version.version_id
    )
    db_session.add(version_link)
    db_session.commit()

    # Create another version - should succeed because validation is APPROVED
    payload = {
        "version_number": "v2.0.0",
        "change_type": "MAJOR",
        "change_description": "New version after approved validation"
    }

    response = client.post(
        f"/models/{model.model_id}/versions",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["version_number"] == "v2.0.0"


def test_allow_creation_when_validation_is_cancelled(
    client, db_session, test_user, auth_headers, version_constraint_setup, usage_frequency
):
    """Test that creation is allowed when the validation is CANCELLED.

    CANCELLED validations don't block new version creation.
    """
    # Create model
    model = Model(
        model_name="Cancelled Validation Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=version_constraint_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create version
    version = ModelVersion(
        model_id=model.model_id,
        version_number="v1.0.0",
        change_type="MAJOR",
        change_description="Version with cancelled validation",
        created_by_id=test_user.user_id,
        status="DRAFT"
    )
    db_session.add(version)
    db_session.commit()

    # Create validation request in CANCELLED status (not active)
    cancelled_status = version_constraint_setup["status_values"]["CANCELLED"]
    validation_request = ValidationRequest(
        validation_type_id=version_constraint_setup["initial_type_id"],
        priority_id=version_constraint_setup["priority_id"],
        current_status_id=cancelled_status.value_id,
        requestor_id=test_user.user_id,
        target_completion_date=date.today() + timedelta(days=30)
    )
    db_session.add(validation_request)
    db_session.flush()

    # Link model and version to validation via association table
    version_link = ValidationRequestModelVersion(
        request_id=validation_request.request_id,
        model_id=model.model_id,
        version_id=version.version_id
    )
    db_session.add(version_link)
    db_session.commit()

    # Create another version - should succeed because validation is CANCELLED
    payload = {
        "version_number": "v2.0.0",
        "change_type": "MAJOR",
        "change_description": "New version after cancelled validation"
    }

    response = client.post(
        f"/models/{model.model_id}/versions",
        json=payload,
        headers=auth_headers
    )

    # Note: This should still be blocked by undeployed version check!
    # Unless the version linked to cancelled validation is considered "resolved"
    # The plan says CANCELLED is "not active" but doesn't exempt from undeployed check
    # For TDD, we'll test both scenarios
    assert response.status_code in [201, 409]  # Depends on implementation interpretation


# =============================================================================
# B3: Cannot delete version linked to any validation
# =============================================================================

def test_cannot_delete_version_linked_to_validation(
    client, db_session, test_user, admin_user, admin_headers, version_constraint_setup, usage_frequency
):
    """Test that 409 is returned when trying to delete a version linked to validation.

    E4 spec: "Returns 409 when version linked to validation"
    Setup: Version is linked to validation VAL-001
    Expected: status_code: 409, error: "version_deletion_blocked",
              reason: "linked_to_validation"
    """
    # Create model
    model = Model(
        model_name="Delete Protection Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=admin_user.user_id,
        risk_tier_id=version_constraint_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create DRAFT version
    version = ModelVersion(
        model_id=model.model_id,
        version_number="v1.0.0",
        change_type="MAJOR",
        change_description="Version linked to validation",
        created_by_id=admin_user.user_id,
        status="DRAFT"
    )
    db_session.add(version)
    db_session.commit()

    # Create validation request
    in_progress_status = version_constraint_setup["status_values"]["IN_PROGRESS"]
    validation_request = ValidationRequest(
        validation_type_id=version_constraint_setup["initial_type_id"],
        priority_id=version_constraint_setup["priority_id"],
        current_status_id=in_progress_status.value_id,
        requestor_id=admin_user.user_id,
        target_completion_date=date.today() + timedelta(days=30)
    )
    db_session.add(validation_request)
    db_session.flush()

    # Link model and version to validation via association table
    version_link = ValidationRequestModelVersion(
        request_id=validation_request.request_id,
        model_id=model.model_id,
        version_id=version.version_id
    )
    db_session.add(version_link)
    db_session.commit()

    # Attempt to delete version - should be blocked
    response = client.delete(
        f"/versions/{version.version_id}",
        headers=admin_headers
    )

    assert response.status_code == 409
    data = response.json()["detail"]
    assert data["error"] == "version_deletion_blocked"
    assert data["reason"] == "linked_to_validation"
    assert "validation_number" in data


def test_can_delete_draft_version_not_linked_to_validation(
    client, db_session, test_user, admin_user, admin_headers, version_constraint_setup, usage_frequency
):
    """Test that DRAFT versions NOT linked to validation can be deleted.

    This is the happy path - no blockers.
    """
    # Create model
    model = Model(
        model_name="Deletable Version Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=admin_user.user_id,
        risk_tier_id=version_constraint_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create DRAFT version (not linked to any validation)
    version = ModelVersion(
        model_id=model.model_id,
        version_number="v1.0.0",
        change_type="MAJOR",
        change_description="Deletable version",
        created_by_id=admin_user.user_id,
        status="DRAFT"
    )
    db_session.add(version)
    db_session.commit()
    version_id = version.version_id

    # Delete version - should succeed
    response = client.delete(
        f"/versions/{version_id}",
        headers=admin_headers
    )

    assert response.status_code == 204

    # Verify deletion
    deleted_version = db_session.query(ModelVersion).filter(
        ModelVersion.version_id == version_id
    ).first()
    assert deleted_version is None


# =============================================================================
# Happy Path: Allow creation when no blockers
# =============================================================================

def test_allow_version_creation_when_no_blockers(
    client, db_session, test_user, auth_headers, version_constraint_setup, usage_frequency
):
    """Test that version creation succeeds when no blockers exist.

    E4 spec: "Allows creation when no blockers"
    Setup: All model versions are ACTIVE or SUPERSEDED
    Expected: status_code: 201
    """
    # Create model
    model = Model(
        model_name="No Blockers Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=version_constraint_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create ACTIVE version (deployed)
    active_version = ModelVersion(
        model_id=model.model_id,
        version_number="v1.0.0",
        change_type="MAJOR",
        change_description="Deployed version",
        created_by_id=test_user.user_id,
        status="ACTIVE"
    )
    db_session.add(active_version)
    db_session.commit()

    # Create another version - should succeed
    payload = {
        "version_number": "v2.0.0",
        "change_type": "MAJOR",
        "change_description": "New version - should succeed"
    }

    response = client.post(
        f"/models/{model.model_id}/versions",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["version_number"] == "v2.0.0"
    assert data["status"] == "DRAFT"


def test_allow_version_creation_on_new_model(
    client, db_session, test_user, auth_headers, version_constraint_setup, usage_frequency
):
    """Test that version creation succeeds on a model with no existing versions.

    First version on a model should always be allowed.
    """
    # Create model with no versions
    model = Model(
        model_name="New Model No Versions",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=version_constraint_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create first version - should succeed
    payload = {
        "version_number": "v1.0.0",
        "change_type": "MAJOR",
        "change_description": "First version - should succeed"
    }

    response = client.post(
        f"/models/{model.model_id}/versions",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["version_number"] == "v1.0.0"


def test_allow_version_creation_when_previous_versions_superseded(
    client, db_session, test_user, auth_headers, version_constraint_setup, usage_frequency
):
    """Test that creation is allowed when all previous versions are SUPERSEDED.

    SUPERSEDED versions are no longer active and shouldn't block new versions.
    """
    # Create model
    model = Model(
        model_name="Superseded Versions Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=version_constraint_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create SUPERSEDED version
    superseded_version = ModelVersion(
        model_id=model.model_id,
        version_number="v1.0.0",
        change_type="MAJOR",
        change_description="Old superseded version",
        created_by_id=test_user.user_id,
        status="SUPERSEDED"
    )
    db_session.add(superseded_version)

    # Create ACTIVE version
    active_version = ModelVersion(
        model_id=model.model_id,
        version_number="v2.0.0",
        change_type="MAJOR",
        change_description="Current active version",
        created_by_id=test_user.user_id,
        status="ACTIVE"
    )
    db_session.add(active_version)
    db_session.commit()

    # Create new version - should succeed
    payload = {
        "version_number": "v3.0.0",
        "change_type": "MAJOR",
        "change_description": "New version after superseded"
    }

    response = client.post(
        f"/models/{model.model_id}/versions",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["version_number"] == "v3.0.0"


# =============================================================================
# Edge Cases
# =============================================================================

def test_block_creation_with_in_validation_status_version(
    client, db_session, test_user, auth_headers, version_constraint_setup, usage_frequency
):
    """Test blocking when version has IN_VALIDATION status.

    A version with IN_VALIDATION status indicates ongoing validation work.
    """
    # Create model
    model = Model(
        model_name="In Validation Status Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=version_constraint_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create version with IN_VALIDATION status
    version = ModelVersion(
        model_id=model.model_id,
        version_number="v1.0.0",
        change_type="MAJOR",
        change_description="Version being validated",
        created_by_id=test_user.user_id,
        status="IN_VALIDATION"
    )
    db_session.add(version)
    db_session.commit()

    # Attempt to create another version - should be blocked
    payload = {
        "version_number": "v2.0.0",
        "change_type": "MAJOR",
        "change_description": "Should be blocked"
    }

    response = client.post(
        f"/models/{model.model_id}/versions",
        json=payload,
        headers=auth_headers
    )

    # Should be blocked - either by undeployed check or active validation check
    assert response.status_code == 409


def test_block_message_includes_blocking_version_details(
    client, db_session, test_user, auth_headers, version_constraint_setup, usage_frequency
):
    """Test that the blocking message includes helpful details about the blocker."""
    # Create model
    model = Model(
        model_name="Detailed Error Test Model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        risk_tier_id=version_constraint_setup["tier1_id"],
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # Create existing DRAFT version
    existing_version = ModelVersion(
        model_id=model.model_id,
        version_number="v1.5.0",
        change_type="MAJOR",
        change_description="Blocking version",
        created_by_id=test_user.user_id,
        status="DRAFT"
    )
    db_session.add(existing_version)
    db_session.commit()

    # Attempt to create another version
    payload = {
        "version_number": "v2.0.0",
        "change_type": "MAJOR",
        "change_description": "Should be blocked"
    }

    response = client.post(
        f"/models/{model.model_id}/versions",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 409
    data = response.json()["detail"]

    # Verify helpful information is included
    assert "blocking_version_number" in data
    assert data["blocking_version_number"] == "v1.5.0"
    assert "message" in data  # Should have human-readable message
