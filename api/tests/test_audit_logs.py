"""Tests for audit log endpoints."""
import pytest
from app.models.audit_log import AuditLog


class TestAuditLogs:
    """Test audit log listing and filtering."""

    def test_list_audit_logs_empty(self, client, auth_headers, db_session):
        """Test listing audit logs when empty."""
        response = client.get("/audit-logs/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_audit_logs_with_data(self, client, auth_headers, test_user, db_session):
        """Test listing audit logs with data."""
        # Create some audit logs
        log1 = AuditLog(
            entity_type="Model",
            entity_id=1,
            action="CREATE",
            user_id=test_user.user_id,
            changes={"model_name": "Test Model"}
        )
        log2 = AuditLog(
            entity_type="Vendor",
            entity_id=2,
            action="UPDATE",
            user_id=test_user.user_id,
            changes={"name": {"old": "Old", "new": "New"}}
        )
        db_session.add_all([log1, log2])
        db_session.commit()

        response = client.get("/audit-logs/", headers=auth_headers)
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 2
        # Most recent first
        assert logs[0]["entity_type"] == "Vendor"
        assert logs[1]["entity_type"] == "Model"

    def test_filter_by_entity_type(self, client, auth_headers, test_user, db_session):
        """Test filtering audit logs by entity type."""
        log1 = AuditLog(
            entity_type="Model",
            entity_id=1,
            action="CREATE",
            user_id=test_user.user_id
        )
        log2 = AuditLog(
            entity_type="Vendor",
            entity_id=2,
            action="CREATE",
            user_id=test_user.user_id
        )
        db_session.add_all([log1, log2])
        db_session.commit()

        response = client.get("/audit-logs/?entity_type=Model", headers=auth_headers)
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 1
        assert logs[0]["entity_type"] == "Model"

    def test_filter_by_entity_id(self, client, auth_headers, test_user, db_session):
        """Test filtering audit logs by entity ID."""
        log1 = AuditLog(
            entity_type="Model",
            entity_id=1,
            action="CREATE",
            user_id=test_user.user_id
        )
        log2 = AuditLog(
            entity_type="Model",
            entity_id=2,
            action="UPDATE",
            user_id=test_user.user_id
        )
        db_session.add_all([log1, log2])
        db_session.commit()

        response = client.get("/audit-logs/?entity_id=1", headers=auth_headers)
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 1
        assert logs[0]["entity_id"] == 1

    def test_filter_by_action(self, client, auth_headers, test_user, db_session):
        """Test filtering audit logs by action."""
        log1 = AuditLog(
            entity_type="Model",
            entity_id=1,
            action="CREATE",
            user_id=test_user.user_id
        )
        log2 = AuditLog(
            entity_type="Model",
            entity_id=2,
            action="UPDATE",
            user_id=test_user.user_id
        )
        log3 = AuditLog(
            entity_type="Model",
            entity_id=3,
            action="DELETE",
            user_id=test_user.user_id
        )
        db_session.add_all([log1, log2, log3])
        db_session.commit()

        response = client.get("/audit-logs/?action=UPDATE", headers=auth_headers)
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 1
        assert logs[0]["action"] == "UPDATE"

    def test_filter_by_user_id(self, client, auth_headers, test_user, second_user, db_session):
        """Test filtering audit logs by user ID."""
        log1 = AuditLog(
            entity_type="Model",
            entity_id=1,
            action="CREATE",
            user_id=test_user.user_id
        )
        log2 = AuditLog(
            entity_type="Model",
            entity_id=2,
            action="CREATE",
            user_id=second_user.user_id
        )
        db_session.add_all([log1, log2])
        db_session.commit()

        response = client.get(f"/audit-logs/?user_id={second_user.user_id}", headers=auth_headers)
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 1
        assert logs[0]["user_id"] == second_user.user_id

    def test_combined_filters(self, client, auth_headers, test_user, db_session):
        """Test combining multiple filters."""
        log1 = AuditLog(
            entity_type="Model",
            entity_id=1,
            action="CREATE",
            user_id=test_user.user_id
        )
        log2 = AuditLog(
            entity_type="Model",
            entity_id=2,
            action="UPDATE",
            user_id=test_user.user_id
        )
        log3 = AuditLog(
            entity_type="Vendor",
            entity_id=1,
            action="UPDATE",
            user_id=test_user.user_id
        )
        db_session.add_all([log1, log2, log3])
        db_session.commit()

        response = client.get("/audit-logs/?entity_type=Model&action=UPDATE", headers=auth_headers)
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 1
        assert logs[0]["entity_type"] == "Model"
        assert logs[0]["action"] == "UPDATE"

    def test_pagination_limit(self, client, auth_headers, test_user, db_session):
        """Test pagination limit."""
        # Create 5 logs
        for i in range(5):
            log = AuditLog(
                entity_type="Model",
                entity_id=i,
                action="CREATE",
                user_id=test_user.user_id
            )
            db_session.add(log)
        db_session.commit()

        response = client.get("/audit-logs/?limit=2", headers=auth_headers)
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 2

    def test_pagination_offset(self, client, auth_headers, test_user, db_session):
        """Test pagination offset."""
        # Create 5 logs with different entity_ids
        for i in range(5):
            log = AuditLog(
                entity_type="Model",
                entity_id=i,
                action="CREATE",
                user_id=test_user.user_id
            )
            db_session.add(log)
        db_session.commit()

        response = client.get("/audit-logs/?limit=2&offset=2", headers=auth_headers)
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 2

    def test_audit_log_includes_user_details(self, client, auth_headers, test_user, db_session):
        """Test that audit logs include user details."""
        log = AuditLog(
            entity_type="Model",
            entity_id=1,
            action="CREATE",
            user_id=test_user.user_id,
            changes={"model_name": "Test"}
        )
        db_session.add(log)
        db_session.commit()

        response = client.get("/audit-logs/", headers=auth_headers)
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 1
        assert "user" in logs[0]
        assert logs[0]["user"]["email"] == test_user.email
        assert logs[0]["user"]["full_name"] == test_user.full_name

    def test_audit_log_changes_field(self, client, auth_headers, test_user, db_session):
        """Test that changes field is properly returned."""
        changes = {
            "model_name": {"old": "Old Name", "new": "New Name"},
            "status": {"old": "Draft", "new": "Active"}
        }
        log = AuditLog(
            entity_type="Model",
            entity_id=1,
            action="UPDATE",
            user_id=test_user.user_id,
            changes=changes
        )
        db_session.add(log)
        db_session.commit()

        response = client.get("/audit-logs/", headers=auth_headers)
        assert response.status_code == 200
        logs = response.json()
        assert logs[0]["changes"] == changes

    def test_get_entity_types(self, client, auth_headers, test_user, db_session):
        """Test getting unique entity types."""
        log1 = AuditLog(
            entity_type="Model",
            entity_id=1,
            action="CREATE",
            user_id=test_user.user_id
        )
        log2 = AuditLog(
            entity_type="Vendor",
            entity_id=1,
            action="CREATE",
            user_id=test_user.user_id
        )
        log3 = AuditLog(
            entity_type="Model",
            entity_id=2,
            action="UPDATE",
            user_id=test_user.user_id
        )
        db_session.add_all([log1, log2, log3])
        db_session.commit()

        response = client.get("/audit-logs/entity-types", headers=auth_headers)
        assert response.status_code == 200
        entity_types = response.json()
        assert set(entity_types) == {"Model", "Vendor"}

    def test_get_actions(self, client, auth_headers, test_user, db_session):
        """Test getting unique actions."""
        log1 = AuditLog(
            entity_type="Model",
            entity_id=1,
            action="CREATE",
            user_id=test_user.user_id
        )
        log2 = AuditLog(
            entity_type="Model",
            entity_id=2,
            action="UPDATE",
            user_id=test_user.user_id
        )
        log3 = AuditLog(
            entity_type="Model",
            entity_id=3,
            action="DELETE",
            user_id=test_user.user_id
        )
        db_session.add_all([log1, log2, log3])
        db_session.commit()

        response = client.get("/audit-logs/actions", headers=auth_headers)
        assert response.status_code == 200
        actions = response.json()
        assert set(actions) == {"CREATE", "UPDATE", "DELETE"}

    def test_unauthenticated_access_denied(self, client, db_session):
        """Test that unauthenticated requests are denied."""
        response = client.get("/audit-logs/")
        assert response.status_code == 403
