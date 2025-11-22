"""
Regression tests for RLS and revalidation banners.

These tests ensure that:
1. Row-Level Security (RLS) is properly applied to all endpoints
2. Model owners can see revalidation status banners
3. The Promise.all batch endpoints all work together
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.models import User, Model, ValidationRequest, ValidationRequestModelVersion, TaxonomyValue
from app.core.security import get_password_hash
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from tests.test_validation_workflow import workflow_taxonomies  # Import fixture


@pytest.fixture
def emily_user(db_session):
    """Create Emily Davis test user."""
    user = User(
        email="emily.test@example.com",
        full_name="Emily Test",
        password_hash=get_password_hash("test123"),
        role="User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_model(db_session, emily_user):
    """Create a test model owned by Emily."""
    model = Model(
        model_name="RLS Test Model",
        description="Test model for RLS and banner regression tests",
        development_type="In-House",
        status="Active",
        owner_id=emily_user.user_id,
        risk_tier_id=None  # Not needed for RLS tests
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def overdue_validation(db_session, test_model, workflow_taxonomies):
    """Create an overdue validation request for the test model."""
    # Get taxonomy values from workflow_taxonomies fixture
    comprehensive = workflow_taxonomies['type']['comprehensive']
    approved_status = workflow_taxonomies['status']['approved']
    in_progress_status = workflow_taxonomies['status']['in_progress']

    # Create an old APPROVED validation
    old_validation = ValidationRequest(
        request_date=date.today() - timedelta(days=700),
        requestor_id=test_model.owner_id,
        validation_type_id=comprehensive.value_id,
        priority_id=comprehensive.value_id,  # Use any taxonomy value as priority
        target_completion_date=date.today() - timedelta(days=640),  # Was completed before this date
        current_status_id=approved_status.value_id,
        created_at=datetime.utcnow() - timedelta(days=700),
        updated_at=datetime.utcnow() - timedelta(days=650)
    )
    db_session.add(old_validation)
    db_session.commit()
    db_session.refresh(old_validation)

    # Associate with model
    assoc1 = ValidationRequestModelVersion(
        request_id=old_validation.request_id,
        model_id=test_model.model_id
    )
    db_session.add(assoc1)
    db_session.commit()

    # Create current IN_PROGRESS validation (overdue)
    current_validation = ValidationRequest(
        request_date=date.today() - timedelta(days=200),
        requestor_id=test_model.owner_id,
        validation_type_id=comprehensive.value_id,
        priority_id=comprehensive.value_id,
        target_completion_date=date.today() - timedelta(days=100),  # 100 days overdue
        current_status_id=in_progress_status.value_id,
        prior_validation_request_id=old_validation.request_id,
        submission_received_date=date.today() - timedelta(days=150),
        created_at=datetime.utcnow() - timedelta(days=200),
        updated_at=datetime.utcnow()
    )
    db_session.add(current_validation)
    db_session.commit()
    db_session.refresh(current_validation)

    # Associate with model
    assoc2 = ValidationRequestModelVersion(
        request_id=current_validation.request_id,
        model_id=test_model.model_id
    )
    db_session.add(assoc2)
    db_session.commit()

    return current_validation


def test_emily_can_access_her_model(client, emily_user, test_model):
    """Test that Emily can access her own model (RLS)."""
    # Login as Emily
    response = client.post("/auth/login", json={
        "email": emily_user.email,
        "password": "test123"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get model details
    response = client.get(f"/models/{test_model.model_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["model_name"] == "RLS Test Model"
    assert data["owner"]["email"] == emily_user.email


def test_emily_cannot_access_other_model(client, emily_user, db_session):
    """Test that Emily cannot access models she doesn't own (RLS)."""
    # Create another user and their model
    other_user = User(
        email="other@example.com",
        full_name="Other User",
        password_hash=get_password_hash("test123"),
        role="User"
    )
    db_session.add(other_user)
    db_session.commit()

    other_model = Model(
        model_name="Other's Model",
        description="Model owned by someone else",
        development_type="In-House",
        status="Active",
        owner_id=other_user.user_id
    )
    db_session.add(other_model)
    db_session.commit()

    # Login as Emily
    response = client.post("/auth/login", json={
        "email": emily_user.email,
        "password": "test123"
    })
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to access other user's model
    response = client.get(f"/models/{other_model.model_id}", headers=headers)
    assert response.status_code == 404  # RLS returns 404, not 403


def test_revalidation_status_endpoint(client, emily_user, test_model, overdue_validation):
    """Test that revalidation status endpoint returns correct data."""
    # Login as Emily
    response = client.post("/auth/login", json={
        "email": emily_user.email,
        "password": "test123"
    })
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get revalidation status
    response = client.get(f"/models/{test_model.model_id}/revalidation-status", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["model_id"] == test_model.model_id
    assert data["model_name"] == "RLS Test Model"
    assert data["status"] in ["Validation Overdue", "Validation In Progress"]
    assert data["days_until_validation_due"] is not None
    assert data["active_request_id"] == overdue_validation.request_id


def test_promise_all_endpoints_work_together(client, emily_user, test_model, overdue_validation):
    """
    CRITICAL REGRESSION TEST: All four endpoints in the frontend Promise.all must work.

    This test ensures that the frontend's model detail page can load all data
    without any endpoint failing, which would cause the banner to disappear.
    """
    # Login as Emily
    response = client.post("/auth/login", json={
        "email": emily_user.email,
        "password": "test123"
    })
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    model_id = test_model.model_id

    # Test all four endpoints that are called in Promise.all
    endpoints = [
        f"/validations/?model_id={model_id}",
        f"/validation-workflow/requests/?model_id={model_id}",
        f"/models/{model_id}/versions",
        f"/models/{model_id}/revalidation-status"
    ]

    for endpoint in endpoints:
        response = client.get(endpoint, headers=headers)
        assert response.status_code == 200, f"Endpoint {endpoint} failed with status {response.status_code}"

    # Specifically verify revalidation status contains banner data
    response = client.get(f"/models/{model_id}/revalidation-status", headers=headers)
    data = response.json()
    assert "status" in data
    assert "days_until_validation_due" in data
    assert "active_request_id" in data


def test_banner_trigger_conditions(client, emily_user, test_model, overdue_validation):
    """Test that banner trigger conditions are met for overdue validation."""
    # Login as Emily
    response = client.post("/auth/login", json={
        "email": emily_user.email,
        "password": "test123"
    })
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get revalidation status
    response = client.get(f"/models/{test_model.model_id}/revalidation-status", headers=headers)
    assert response.status_code == 200

    data = response.json()

    # Check banner trigger conditions
    # For RED banner: days_until_validation_due < 0 OR status contains "Overdue"
    has_overdue_status = "Overdue" in data["status"]
    has_negative_days = data["days_until_validation_due"] is not None and data["days_until_validation_due"] < 0

    assert has_overdue_status or has_negative_days, \
        f"Banner should trigger: status={data['status']}, days={data['days_until_validation_due']}"


def test_rls_on_all_model_endpoints(client, emily_user, test_model):
    """Test RLS on all model-related endpoints."""
    # Login as Emily
    response = client.post("/auth/login", json={
        "email": emily_user.email,
        "password": "test123"
    })
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    model_id = test_model.model_id

    # Test all endpoints that should respect RLS
    endpoints = [
        f"/models/{model_id}",
        f"/models/{model_id}/revalidation-status",
        f"/models/{model_id}/versions",
        f"/models/{model_id}/validation-suggestions",
        f"/models/{model_id}/versions/next-version?change_type=MAJOR",
        f"/models/{model_id}/versions/current",
    ]

    for endpoint in endpoints:
        response = client.get(endpoint, headers=headers)
        # Should succeed (200) or not exist yet (404), but not fail auth (401/403) or error (500)
        assert response.status_code in [200, 404], \
            f"RLS issue on {endpoint}: HTTP {response.status_code}"


def test_validation_requests_with_model_filter(client, emily_user, test_model, overdue_validation):
    """
    CRITICAL REGRESSION TEST: Validation requests endpoint with model_id filter.

    This was the endpoint that broke and caused banners to disappear.
    It must not have duplicate join errors.
    """
    # Login as Emily
    response = client.post("/auth/login", json={
        "email": emily_user.email,
        "password": "test123"
    })
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # This endpoint had a duplicate join error that broke Promise.all
    response = client.get(
        f"/validation-workflow/requests/?model_id={test_model.model_id}",
        headers=headers
    )

    assert response.status_code == 200, \
        f"Validation requests endpoint failed: {response.status_code}"

    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0  # Should have the validation we created
