"""Tests for model authorization and audit logging."""
import pytest
from app.models.audit_log import AuditLog


class TestModelAuthorization:
    """Test authorization for model update and delete operations."""

    def test_owner_can_update_own_model(self, client, auth_headers, sample_model):
        """Model owner can update their own model."""
        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={"model_name": "Updated by Owner"}
        )
        assert response.status_code == 200
        assert response.json()["model_name"] == "Updated by Owner"

    def test_non_owner_cannot_update_model(self, client, second_user_headers, sample_model):
        """Non-owner user cannot update someone else's model (RLS returns 404)."""
        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=second_user_headers,
            json={"model_name": "Updated by Non-Owner"}
        )
        # RLS returns 404 to hide existence of inaccessible models
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_admin_can_update_any_model(self, client, admin_headers, sample_model):
        """Admin user can update any model."""
        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=admin_headers,
            json={"model_name": "Updated by Admin"}
        )
        assert response.status_code == 200
        assert response.json()["model_name"] == "Updated by Admin"

    def test_owner_can_delete_own_model(self, client, auth_headers, sample_model):
        """Model owner can delete their own model."""
        response = client.delete(
            f"/models/{sample_model.model_id}",
            headers=auth_headers
        )
        assert response.status_code == 204

    def test_non_owner_cannot_delete_model(self, client, second_user_headers, sample_model):
        """Non-owner user cannot delete someone else's model (RLS returns 404)."""
        response = client.delete(
            f"/models/{sample_model.model_id}",
            headers=second_user_headers
        )
        # RLS returns 404 to hide existence of inaccessible models
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_admin_can_delete_any_model(self, client, admin_headers, sample_model):
        """Admin user can delete any model."""
        response = client.delete(
            f"/models/{sample_model.model_id}",
            headers=admin_headers
        )
        assert response.status_code == 204


class TestAuditLogging:
    """Test audit logging for model operations."""

    def test_create_model_creates_audit_log(self, client, auth_headers, test_user, db_session):
        """Creating a model creates an audit log entry."""
        response = client.post(
            "/models/",
            headers=auth_headers,
            json={
                "model_name": "Audit Test Model",
                "development_type": "In-House",
                "status": "In Development",
                "owner_id": test_user.user_id,
                "user_ids": [test_user.user_id]
            }
        )
        assert response.status_code == 201
        model_id = response.json()["model_id"]

        # Check audit log was created
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "Model",
            AuditLog.entity_id == model_id,
            AuditLog.action == "CREATE"
        ).first()

        assert audit_log is not None
        assert audit_log.user_id == test_user.user_id
        assert audit_log.changes["model_name"] == "Audit Test Model"
        assert audit_log.changes["status"] == "In Development"
        assert audit_log.changes["development_type"] == "In-House"

    def test_update_model_creates_audit_log(self, client, auth_headers, sample_model, test_user, db_session):
        """Updating a model creates an audit log entry with changes."""
        old_name = sample_model.model_name
        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={"model_name": "Updated Model Name", "status": "Active"}
        )
        assert response.status_code == 200

        # Check audit log was created
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "Model",
            AuditLog.entity_id == sample_model.model_id,
            AuditLog.action == "UPDATE"
        ).first()

        assert audit_log is not None
        assert audit_log.user_id == test_user.user_id
        assert "model_name" in audit_log.changes
        assert audit_log.changes["model_name"]["old"] == old_name
        assert audit_log.changes["model_name"]["new"] == "Updated Model Name"
        assert "status" in audit_log.changes
        assert audit_log.changes["status"]["old"] == "In Development"
        assert audit_log.changes["status"]["new"] == "Active"

    def test_delete_model_creates_audit_log(self, client, auth_headers, sample_model, test_user, db_session):
        """Deleting a model creates an audit log entry."""
        model_id = sample_model.model_id
        model_name = sample_model.model_name

        response = client.delete(
            f"/models/{model_id}",
            headers=auth_headers
        )
        assert response.status_code == 204

        # Check audit log was created
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "Model",
            AuditLog.entity_id == model_id,
            AuditLog.action == "DELETE"
        ).first()

        assert audit_log is not None
        assert audit_log.user_id == test_user.user_id
        assert audit_log.changes["model_name"] == model_name

    def test_update_no_changes_no_audit_log(self, client, auth_headers, sample_model, db_session):
        """Updating a model with no actual changes creates no audit log."""
        # Send same values
        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={"model_name": sample_model.model_name}
        )
        assert response.status_code == 200

        # Check no audit log was created (no actual changes)
        audit_logs = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "Model",
            AuditLog.entity_id == sample_model.model_id,
            AuditLog.action == "UPDATE"
        ).all()

        assert len(audit_logs) == 0

    def test_audit_log_tracks_user_ids_modification(self, client, auth_headers, sample_model, second_user, db_session):
        """Audit log tracks when model users are modified."""
        response = client.patch(
            f"/models/{sample_model.model_id}",
            headers=auth_headers,
            json={"user_ids": [second_user.user_id]}
        )
        assert response.status_code == 200

        # Check audit log was created
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "Model",
            AuditLog.entity_id == sample_model.model_id,
            AuditLog.action == "UPDATE"
        ).first()

        assert audit_log is not None
        assert "user_ids" in audit_log.changes
        assert audit_log.changes["user_ids"] == "modified"
