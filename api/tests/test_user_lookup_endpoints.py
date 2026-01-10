"""Tests for scoped user lookup endpoints."""
from datetime import date, timedelta

from app.core.security import create_access_token, get_password_hash
from app.core.roles import RoleCode
from app.core.time import utc_now
from app.models.role import Role
from app.models.user import User
from app.models.model import Model
from app.models.model_delegate import ModelDelegate
from app.models.model_region import ModelRegion
from app.models.region import Region
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.validation import (
    ValidationRequest,
    ValidationRequestModelVersion,
    ValidationAssignment
)


def _role_id(db_session, role_code: str) -> int:
    return db_session.query(Role).filter(Role.code == role_code).first().role_id


def _create_user(db_session, email: str, name: str, role_code: str, lob_id: int) -> User:
    user = User(
        email=email,
        full_name=name,
        password_hash=get_password_hash("testpass123"),
        role_id=_role_id(db_session, role_code),
        lob_id=lob_id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _validation_taxonomies(db_session):
    priority_tax = Taxonomy(name="Validation Priority", is_system=True)
    status_tax = Taxonomy(name="Validation Request Status", is_system=True)
    type_tax = Taxonomy(name="Validation Type", is_system=True)
    db_session.add_all([priority_tax, status_tax, type_tax])
    db_session.flush()

    priority = TaxonomyValue(
        taxonomy_id=priority_tax.taxonomy_id, code="STANDARD", label="Standard", sort_order=1
    )
    status = TaxonomyValue(
        taxonomy_id=status_tax.taxonomy_id, code="INTAKE", label="Intake", sort_order=1
    )
    val_type = TaxonomyValue(
        taxonomy_id=type_tax.taxonomy_id, code="INITIAL", label="Initial Validation", sort_order=1
    )
    db_session.add_all([priority, status, val_type])
    db_session.commit()

    return priority, status, val_type


def test_assignable_validators_admin_access(client, admin_headers, validator_user, admin_user, test_user):
    response = client.get("/validation-workflow/assignable-validators", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    returned_ids = {item["user_id"] for item in data}
    returned_roles = {item["role_code"] for item in data}

    assert admin_user.user_id in returned_ids
    assert validator_user.user_id in returned_ids
    assert test_user.user_id not in returned_ids
    assert returned_roles.issubset({RoleCode.ADMIN.value, RoleCode.VALIDATOR.value})


def test_assignable_validators_validator_access(client, validator_headers):
    response = client.get("/validation-workflow/assignable-validators", headers=validator_headers)
    assert response.status_code == 200


def test_assignable_validators_user_forbidden(client, auth_headers):
    response = client.get("/validation-workflow/assignable-validators", headers=auth_headers)
    assert response.status_code == 403


def test_model_assignees_endpoint(client, db_session, auth_headers, test_user, second_user, validator_user, usage_frequency, lob_hierarchy):
    shared_owner = _create_user(
        db_session, "shared_owner@example.com", "Shared Owner", RoleCode.USER.value, lob_hierarchy["retail"].lob_id
    )
    shared_developer = _create_user(
        db_session, "shared_dev@example.com", "Shared Developer", RoleCode.USER.value, lob_hierarchy["retail"].lob_id
    )
    delegate_user = _create_user(
        db_session, "delegate@example.com", "Delegate User", RoleCode.USER.value, lob_hierarchy["wholesale"].lob_id
    )
    regional_owner = _create_user(
        db_session, "regional_owner@example.com", "Regional Owner", RoleCode.USER.value, lob_hierarchy["credit"].lob_id
    )

    model = Model(
        model_name="Assignee Model",
        description="Model for assignee lookup",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id,
        developer_id=second_user.user_id,
        shared_owner_id=shared_owner.user_id,
        shared_developer_id=shared_developer.user_id,
        row_approval_status=None,
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)

    delegate = ModelDelegate(
        model_id=model.model_id,
        user_id=delegate_user.user_id,
        delegated_by_id=test_user.user_id,
        can_submit_changes=True
    )
    db_session.add(delegate)

    region = Region(code="NA", name="North America")
    db_session.add(region)
    db_session.flush()
    db_session.add(ModelRegion(
        model_id=model.model_id,
        region_id=region.region_id,
        shared_model_owner_id=regional_owner.user_id
    ))

    priority, status, val_type = _validation_taxonomies(db_session)
    request = ValidationRequest(
        request_date=date.today(),
        requestor_id=test_user.user_id,
        validation_type_id=val_type.value_id,
        priority_id=priority.value_id,
        target_completion_date=date.today() + timedelta(days=30),
        current_status_id=status.value_id,
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db_session.add(request)
    db_session.flush()
    db_session.add(ValidationRequestModelVersion(
        request_id=request.request_id,
        model_id=model.model_id
    ))
    db_session.add(ValidationAssignment(
        request_id=request.request_id,
        validator_id=validator_user.user_id,
        is_primary=True,
        independence_attestation=True
    ))
    db_session.commit()

    response = client.get(f"/models/{model.model_id}/assignees", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    returned_ids = {item["user_id"] for item in data}

    assert returned_ids.issuperset({
        test_user.user_id,
        second_user.user_id,
        shared_owner.user_id,
        shared_developer.user_id,
        delegate_user.user_id,
        regional_owner.user_id,
        validator_user.user_id
    })


def test_model_assignees_unauthorized(client, db_session, test_user, usage_frequency, lob_hierarchy):
    model = Model(
        model_name="Restricted Model",
        description="Restricted model",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id,
        row_approval_status=None,
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)

    outsider = _create_user(
        db_session, "outsider@example.com", "Outsider User", RoleCode.USER.value, lob_hierarchy["wholesale"].lob_id
    )
    token = create_access_token(data={"sub": outsider.email})
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(f"/models/{model.model_id}/assignees", headers=headers)
    assert response.status_code == 404


def test_user_search_by_email(client, auth_headers, second_user):
    response = client.get("/users/search", headers=auth_headers, params={"email": "developer"})
    assert response.status_code == 200
    data = response.json()
    emails = {item["email"] for item in data}
    assert second_user.email in emails
