import pytest
from datetime import datetime
from app.models.model import Model, ModelStatus
from app.models.model_submission_comment import ModelSubmissionComment


def test_create_model_as_admin_auto_approved(client, admin_headers, sample_vendor):
    """Test that models created by admins are automatically approved."""
    response = client.post(
        "/models/",
        headers=admin_headers,
        json={
            "model_name": "Admin Created Model",
            "description": "Created by admin",
            "development_type": "In-House",
            "owner_id": 1,  # Assuming admin is user 1 or exists
            "status": "In Development",
            "user_ids": [1],
            "auto_create_validation": False
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["row_approval_status"] is None
    assert data["model_name"] == "Admin Created Model"


def test_create_model_as_user_pending_approval(client, auth_headers, test_user, sample_vendor):
    """Test that models created by non-admins are pending approval."""
    response = client.post(
        "/models/",
        headers=auth_headers,
        json={
            "model_name": "User Created Model",
            "description": "Created by user",
            "development_type": "In-House",
            "owner_id": test_user.user_id,
            "status": "In Development",
            "user_ids": [test_user.user_id],
            "auto_create_validation": False
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["row_approval_status"] == "pending"
    assert data["submitted_by_user_id"] == test_user.user_id
    assert data["submitted_at"] is not None


def test_user_can_edit_pending_model(client, auth_headers, test_user, db_session):
    """Test that users can edit their own pending models."""
    # Create a pending model directly in DB to save setup time/dependency
    model = Model(
        model_name="Pending Model",
        description="Original description",
        development_type="In-House",
        owner_id=test_user.user_id,
        status="In Development",
        row_approval_status="pending",
        submitted_by_user_id=test_user.user_id,
        submitted_at=datetime.utcnow()
    )
    db_session.add(model)
    db_session.commit()

    response = client.patch(
        f"/models/{model.model_id}",
        headers=auth_headers,
        json={
            "description": "Updated description"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated description"
    assert data["row_approval_status"] == "pending"


def test_user_edit_approved_model_creates_pending_edit(client, auth_headers, test_user, db_session):
    """
    Test that non-admin users editing approved models creates a pending edit
    that requires admin approval, rather than directly modifying the model.
    """
    # Create an approved model (row_approval_status=None)
    model = Model(
        model_name="Approved Model",
        description="Original description",
        development_type="In-House",
        owner_id=test_user.user_id,
        status="In Development",
        row_approval_status=None,  # Approved
        submitted_by_user_id=test_user.user_id
    )
    db_session.add(model)
    db_session.commit()

    # Attempt to edit as user - should create pending edit, not direct update
    response = client.patch(
        f"/models/{model.model_id}",
        headers=auth_headers,
        json={
            "description": "Updated description"
        }
    )

    # Non-admin editing approved model should return 202 Accepted
    # with info about the pending edit
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    assert "pending_edit_id" in data
    assert data["proposed_changes"]["description"] == "Updated description"
    assert data["model_id"] == model.model_id

    # Verify the model was NOT actually updated
    db_session.refresh(model)
    assert model.description == "Original description"


def test_admin_approve_model(client, admin_headers, test_user, db_session):
    """Test admin approving a pending model."""
    model = Model(
        model_name="Pending Model",
        owner_id=test_user.user_id,
        row_approval_status="pending",
        submitted_by_user_id=test_user.user_id
    )
    db_session.add(model)
    db_session.commit()

    response = client.post(
        f"/models/{model.model_id}/approve",
        headers=admin_headers,
        json={"comment": "Looks good"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["row_approval_status"] is None  # Approved


def test_admin_send_back_model(client, admin_headers, test_user, db_session):
    """Test admin sending back a model for revision."""
    model = Model(
        model_name="Pending Model",
        owner_id=test_user.user_id,
        row_approval_status="pending",
        submitted_by_user_id=test_user.user_id
    )
    db_session.add(model)
    db_session.commit()

    response = client.post(
        f"/models/{model.model_id}/send-back",
        headers=admin_headers,
        json={"comment": "Needs more details"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["row_approval_status"] == "needs_revision"


def test_user_resubmit_model(client, auth_headers, test_user, db_session):
    """Test user resubmitting a model that needed revision."""
    model = Model(
        model_name="Needs Revision Model",
        owner_id=test_user.user_id,
        row_approval_status="needs_revision",
        submitted_by_user_id=test_user.user_id
    )
    db_session.add(model)
    db_session.commit()

    response = client.post(
        f"/models/{model.model_id}/resubmit",
        headers=auth_headers,
        json={"comment": "Updated details"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["row_approval_status"] == "pending"


def test_rls_user_sees_own_pending_submissions(client, auth_headers, test_user, second_user, db_session):
    """Test that users can see their own pending submissions even if they are not the owner (if that case is possible) or just generally."""
    # Model 1: Pending, submitted by test_user
    model1 = Model(
        model_name="My Pending Model",
        owner_id=test_user.user_id,
        row_approval_status="pending",
        submitted_by_user_id=test_user.user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    # Model 2: Pending, submitted by second_user
    model2 = Model(
        model_name="Other Pending Model",
        owner_id=second_user.user_id,
        row_approval_status="pending",
        submitted_by_user_id=second_user.user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add_all([model1, model2])
    db_session.commit()

    response = client.get("/models/my-submissions", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    ids = [m["model_id"] for m in data]
    assert model1.model_id in ids
    assert model2.model_id not in ids


def test_submission_thread_retrieval(client, auth_headers, test_user, db_session):
    """Test retrieving the submission comment thread."""
    model = Model(
        model_name="Thread Model",
        owner_id=test_user.user_id,
        row_approval_status="pending",
        submitted_by_user_id=test_user.user_id
    )
    db_session.add(model)
    db_session.commit()

    # Add a comment (mocking the endpoint or DB)
    # Assuming endpoint exists
    client.post(
        f"/models/{model.model_id}/comments",
        headers=auth_headers,
        json={"comment_text": "Initial submission comment"}
    )

    response = client.get(
        f"/models/{model.model_id}/submission-thread", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["comment_text"] == "Initial submission comment"


def test_full_submission_workflow_integration(client, auth_headers, admin_headers, test_user, db_session):
    """
    Integration test covering the full lifecycle:
    Create -> Pending -> Admin Send Back -> Needs Revision -> User Edit -> Resubmit -> Pending -> Admin Approve -> Approved
    """
    # 1. User creates model
    create_resp = client.post(
        "/models/",
        headers=auth_headers,
        json={
            "model_name": "Workflow Model",
            "description": "Initial description",
            "development_type": "In-House",
            "owner_id": test_user.user_id,
            "status": "In Development",
            "user_ids": [test_user.user_id],
            "auto_create_validation": False
        }
    )
    assert create_resp.status_code == 201
    model_id = create_resp.json()["model_id"]
    assert create_resp.json()["row_approval_status"] == "pending"

    # 2. Admin reviews and sends back
    send_back_resp = client.post(
        f"/models/{model_id}/send-back",
        headers=admin_headers,
        json={"comment": "Please add more details to description"}
    )
    assert send_back_resp.status_code == 200
    assert send_back_resp.json()["row_approval_status"] == "needs_revision"

    # 3. User edits model
    edit_resp = client.patch(
        f"/models/{model_id}",
        headers=auth_headers,
        json={"description": "Updated description with more details"}
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()[
        "description"] == "Updated description with more details"

    # 4. User resubmits
    resubmit_resp = client.post(
        f"/models/{model_id}/resubmit",
        headers=auth_headers,
        json={"comment": "Updated as requested"}
    )
    assert resubmit_resp.status_code == 200
    assert resubmit_resp.json()["row_approval_status"] == "pending"

    # 5. Admin approves
    approve_resp = client.post(
        f"/models/{model_id}/approve",
        headers=admin_headers,
        json={"comment": "Approved now"}
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["row_approval_status"] is None

    # 6. Verify final state
    get_resp = client.get(f"/models/{model_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["row_approval_status"] is None


def test_user_cannot_approve_own_model(client, auth_headers, test_user, db_session):
    """Test that a user cannot approve their own model."""
    model = Model(
        model_name="My Pending Model",
        owner_id=test_user.user_id,
        row_approval_status="pending",
        submitted_by_user_id=test_user.user_id
    )
    db_session.add(model)
    db_session.commit()

    response = client.post(
        f"/models/{model.model_id}/approve",
        headers=auth_headers,
        json={"comment": "Self approval"}
    )
    assert response.status_code == 403


def test_dashboard_news_feed(client, auth_headers, test_user, db_session):
    """Test retrieving the news feed for the dashboard."""
    # Create some activity (comments, status changes)
    model = Model(
        model_name="Feed Model",
        owner_id=test_user.user_id,
        row_approval_status="pending",
        submitted_by_user_id=test_user.user_id
    )
    db_session.add(model)
    db_session.commit()

    # Add a comment to generate feed item
    client.post(
        f"/models/{model.model_id}/comments",
        headers=auth_headers,
        json={"comment_text": "New submission"}
    )

    response = client.get("/dashboard/news-feed", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    # Assuming list of feed items
    assert isinstance(data, list)


def test_create_model_enforces_user_inclusion(client, auth_headers, second_user):
    """Test that non-admins must include themselves as owner, developer, or model user."""
    # Try to create model where current user is not owner, developer, or in user_ids
    response = client.post(
        "/models/",
        headers=auth_headers,
        json={
            "model_name": "Invalid User Model",
            "description": "Created by user",
            "development_type": "In-House",
            "owner_id": second_user.user_id,  # Different user as owner
            "status": "In Development",
            "user_ids": [second_user.user_id],  # Only other user, not current user
            "auto_create_validation": False
        }
    )
    assert response.status_code == 400
    assert "must include yourself" in response.json()["detail"].lower()
