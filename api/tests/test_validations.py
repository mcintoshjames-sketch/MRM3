"""Tests for validation endpoints."""
import pytest
from datetime import date, timedelta


class TestValidationsCRUD:
    """Test validation CRUD operations."""

    def test_list_validations_empty(self, client, auth_headers, taxonomy_values):
        """List validations when empty."""
        response = client.get("/validations/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_validations_without_auth(self, client):
        """List validations without auth returns 403."""
        response = client.get("/validations/")
        assert response.status_code == 403

    def test_create_validation_as_validator(self, client, validator_headers, sample_model, validator_user, taxonomy_values):
        """Validator can create validation."""
        data = {
            "model_id": sample_model.model_id,
            "validation_date": "2025-01-15",
            "validator_id": validator_user.user_id,
            "validation_type_id": taxonomy_values["initial"].value_id,
            "outcome_id": taxonomy_values["pass"].value_id,
            "scope_id": taxonomy_values["full_scope"].value_id,
            "findings_summary": "Model validated successfully",
            "report_reference": "VAL-2025-001"
        }
        response = client.post("/validations/", headers=validator_headers, json=data)
        assert response.status_code == 201
        result = response.json()
        assert result["model_id"] == sample_model.model_id
        assert result["validation_date"] == "2025-01-15"
        assert result["validator"]["user_id"] == validator_user.user_id
        assert result["validation_type"]["label"] == "Initial"
        assert result["outcome"]["label"] == "Pass"
        assert result["scope"]["label"] == "Full Scope"
        assert result["findings_summary"] == "Model validated successfully"
        assert result["report_reference"] == "VAL-2025-001"

    def test_create_validation_as_admin(self, client, admin_headers, sample_model, admin_user, taxonomy_values):
        """Admin can create validation."""
        data = {
            "model_id": sample_model.model_id,
            "validation_date": "2025-01-15",
            "validator_id": admin_user.user_id,
            "validation_type_id": taxonomy_values["annual"].value_id,
            "outcome_id": taxonomy_values["pass_with_findings"].value_id,
            "scope_id": taxonomy_values["full_scope"].value_id,
            "findings_summary": "Minor issues found"
        }
        response = client.post("/validations/", headers=admin_headers, json=data)
        assert response.status_code == 201

    def test_create_validation_as_regular_user_fails(self, client, auth_headers, sample_model, test_user, taxonomy_values):
        """Regular user cannot create validation."""
        data = {
            "model_id": sample_model.model_id,
            "validation_date": "2025-01-15",
            "validator_id": test_user.user_id,
            "validation_type_id": taxonomy_values["initial"].value_id,
            "outcome_id": taxonomy_values["pass"].value_id,
            "scope_id": taxonomy_values["full_scope"].value_id
        }
        response = client.post("/validations/", headers=auth_headers, json=data)
        assert response.status_code == 403
        assert "Validators or Admins" in response.json()["detail"]

    def test_create_validation_invalid_model(self, client, validator_headers, validator_user, taxonomy_values):
        """Create validation with non-existent model fails."""
        data = {
            "model_id": 9999,
            "validation_date": "2025-01-15",
            "validator_id": validator_user.user_id,
            "validation_type_id": taxonomy_values["initial"].value_id,
            "outcome_id": taxonomy_values["pass"].value_id,
            "scope_id": taxonomy_values["full_scope"].value_id
        }
        response = client.post("/validations/", headers=validator_headers, json=data)
        assert response.status_code == 404
        assert "Model not found" in response.json()["detail"]

    def test_create_validation_invalid_validator(self, client, validator_headers, sample_model, taxonomy_values):
        """Create validation with non-existent validator fails."""
        data = {
            "model_id": sample_model.model_id,
            "validation_date": "2025-01-15",
            "validator_id": 9999,
            "validation_type_id": taxonomy_values["initial"].value_id,
            "outcome_id": taxonomy_values["pass"].value_id,
            "scope_id": taxonomy_values["full_scope"].value_id
        }
        response = client.post("/validations/", headers=validator_headers, json=data)
        assert response.status_code == 404
        assert "Validator user not found" in response.json()["detail"]

    def test_create_validation_invalid_taxonomy(self, client, validator_headers, sample_model, validator_user, taxonomy_values):
        """Create validation with invalid taxonomy value fails."""
        data = {
            "model_id": sample_model.model_id,
            "validation_date": "2025-01-15",
            "validator_id": validator_user.user_id,
            "validation_type_id": 9999,
            "outcome_id": taxonomy_values["pass"].value_id,
            "scope_id": taxonomy_values["full_scope"].value_id
        }
        response = client.post("/validations/", headers=validator_headers, json=data)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_validation_by_id(self, client, validator_headers, sample_model, validator_user, taxonomy_values):
        """Get specific validation."""
        # Create validation first
        data = {
            "model_id": sample_model.model_id,
            "validation_date": "2025-01-15",
            "validator_id": validator_user.user_id,
            "validation_type_id": taxonomy_values["initial"].value_id,
            "outcome_id": taxonomy_values["pass"].value_id,
            "scope_id": taxonomy_values["full_scope"].value_id
        }
        create_resp = client.post("/validations/", headers=validator_headers, json=data)
        validation_id = create_resp.json()["validation_id"]

        response = client.get(f"/validations/{validation_id}", headers=validator_headers)
        assert response.status_code == 200
        assert response.json()["validation_id"] == validation_id

    def test_get_validation_not_found(self, client, auth_headers, taxonomy_values):
        """Get non-existent validation returns 404."""
        response = client.get("/validations/9999", headers=auth_headers)
        assert response.status_code == 404

    def test_update_validation_as_validator(self, client, validator_headers, sample_model, validator_user, taxonomy_values):
        """Validator can update validation."""
        # Create validation
        data = {
            "model_id": sample_model.model_id,
            "validation_date": "2025-01-15",
            "validator_id": validator_user.user_id,
            "validation_type_id": taxonomy_values["initial"].value_id,
            "outcome_id": taxonomy_values["pass"].value_id,
            "scope_id": taxonomy_values["full_scope"].value_id
        }
        create_resp = client.post("/validations/", headers=validator_headers, json=data)
        validation_id = create_resp.json()["validation_id"]

        # Update validation
        update_data = {
            "findings_summary": "Updated findings",
            "report_reference": "VAL-2025-002"
        }
        response = client.patch(f"/validations/{validation_id}", headers=validator_headers, json=update_data)
        assert response.status_code == 200
        assert response.json()["findings_summary"] == "Updated findings"
        assert response.json()["report_reference"] == "VAL-2025-002"

    def test_update_validation_as_regular_user_fails(self, client, auth_headers, validator_headers, sample_model, validator_user, taxonomy_values):
        """Regular user cannot update validation."""
        # Create validation as validator
        data = {
            "model_id": sample_model.model_id,
            "validation_date": "2025-01-15",
            "validator_id": validator_user.user_id,
            "validation_type_id": taxonomy_values["initial"].value_id,
            "outcome_id": taxonomy_values["pass"].value_id,
            "scope_id": taxonomy_values["full_scope"].value_id
        }
        create_resp = client.post("/validations/", headers=validator_headers, json=data)
        validation_id = create_resp.json()["validation_id"]

        # Try to update as regular user
        update_data = {"findings_summary": "Unauthorized update"}
        response = client.patch(f"/validations/{validation_id}", headers=auth_headers, json=update_data)
        assert response.status_code == 403

    def test_delete_validation_as_admin(self, client, admin_headers, validator_headers, sample_model, validator_user, taxonomy_values):
        """Admin can delete validation."""
        # Create validation
        data = {
            "model_id": sample_model.model_id,
            "validation_date": "2025-01-15",
            "validator_id": validator_user.user_id,
            "validation_type_id": taxonomy_values["initial"].value_id,
            "outcome_id": taxonomy_values["pass"].value_id,
            "scope_id": taxonomy_values["full_scope"].value_id
        }
        create_resp = client.post("/validations/", headers=validator_headers, json=data)
        validation_id = create_resp.json()["validation_id"]

        # Delete as admin
        response = client.delete(f"/validations/{validation_id}", headers=admin_headers)
        assert response.status_code == 204

        # Verify deletion
        get_resp = client.get(f"/validations/{validation_id}", headers=admin_headers)
        assert get_resp.status_code == 404

    def test_delete_validation_as_validator_fails(self, client, validator_headers, sample_model, validator_user, taxonomy_values):
        """Validator cannot delete validation (Admin only)."""
        # Create validation
        data = {
            "model_id": sample_model.model_id,
            "validation_date": "2025-01-15",
            "validator_id": validator_user.user_id,
            "validation_type_id": taxonomy_values["initial"].value_id,
            "outcome_id": taxonomy_values["pass"].value_id,
            "scope_id": taxonomy_values["full_scope"].value_id
        }
        create_resp = client.post("/validations/", headers=validator_headers, json=data)
        validation_id = create_resp.json()["validation_id"]

        # Try to delete as validator
        response = client.delete(f"/validations/{validation_id}", headers=validator_headers)
        assert response.status_code == 403
        assert "Only Admins" in response.json()["detail"]

    def test_delete_validation_not_found(self, client, admin_headers, taxonomy_values):
        """Delete non-existent validation returns 404."""
        response = client.delete("/validations/9999", headers=admin_headers)
        assert response.status_code == 404


class TestValidationFilters:
    """Test validation list filters."""

    def test_filter_by_model_id(self, client, validator_headers, sample_model, validator_user, taxonomy_values, db_session):
        """Filter validations by model ID."""
        # Create second model
        from app.models.model import Model
        model2 = Model(model_name="Model 2", development_type="In-House", owner_id=validator_user.user_id, status="Active")
        db_session.add(model2)
        db_session.commit()

        # Create validation for each model
        for model_id in [sample_model.model_id, model2.model_id]:
            data = {
                "model_id": model_id,
                "validation_date": "2025-01-15",
                "validator_id": validator_user.user_id,
                "validation_type_id": taxonomy_values["initial"].value_id,
                "outcome_id": taxonomy_values["pass"].value_id,
                "scope_id": taxonomy_values["full_scope"].value_id
            }
            client.post("/validations/", headers=validator_headers, json=data)

        # Filter by model_id
        response = client.get(f"/validations/?model_id={sample_model.model_id}", headers=validator_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["model_id"] == sample_model.model_id

    def test_filter_by_outcome_id(self, client, validator_headers, sample_model, validator_user, taxonomy_values):
        """Filter validations by outcome."""
        # Create validations with different outcomes
        for outcome in ["pass", "fail"]:
            data = {
                "model_id": sample_model.model_id,
                "validation_date": "2025-01-15",
                "validator_id": validator_user.user_id,
                "validation_type_id": taxonomy_values["initial"].value_id,
                "outcome_id": taxonomy_values[outcome].value_id,
                "scope_id": taxonomy_values["full_scope"].value_id
            }
            client.post("/validations/", headers=validator_headers, json=data)

        # Filter by outcome
        response = client.get(f"/validations/?outcome_id={taxonomy_values['fail'].value_id}", headers=validator_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["outcome"] == "Fail"

    def test_filter_by_date_range(self, client, validator_headers, sample_model, validator_user, taxonomy_values):
        """Filter validations by date range."""
        # Create validations with different dates
        for date_str in ["2025-01-10", "2025-01-20", "2025-02-01"]:
            data = {
                "model_id": sample_model.model_id,
                "validation_date": date_str,
                "validator_id": validator_user.user_id,
                "validation_type_id": taxonomy_values["initial"].value_id,
                "outcome_id": taxonomy_values["pass"].value_id,
                "scope_id": taxonomy_values["full_scope"].value_id
            }
            client.post("/validations/", headers=validator_headers, json=data)

        # Filter by date range
        response = client.get("/validations/?from_date=2025-01-15&to_date=2025-01-25", headers=validator_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["validation_date"] == "2025-01-20"

    def test_pagination(self, client, validator_headers, sample_model, validator_user, taxonomy_values):
        """Test pagination with limit and offset."""
        # Create 5 validations
        for i in range(5):
            data = {
                "model_id": sample_model.model_id,
                "validation_date": f"2025-01-{10+i:02d}",
                "validator_id": validator_user.user_id,
                "validation_type_id": taxonomy_values["initial"].value_id,
                "outcome_id": taxonomy_values["pass"].value_id,
                "scope_id": taxonomy_values["full_scope"].value_id
            }
            client.post("/validations/", headers=validator_headers, json=data)

        # Test limit
        response = client.get("/validations/?limit=2", headers=validator_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

        # Test offset
        response = client.get("/validations/?limit=2&offset=2", headers=validator_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestValidationPolicies:
    """Test validation policy endpoints."""

    def test_list_policies_empty(self, client, auth_headers, taxonomy_values):
        """List policies when empty."""
        response = client.get("/validations/policies/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_create_policy_as_admin(self, client, admin_headers, taxonomy_values):
        """Admin can create validation policy."""
        data = {
            "risk_tier_id": taxonomy_values["tier1"].value_id,
            "frequency_months": 6,
            "description": "High risk models require validation every 6 months"
        }
        response = client.post("/validations/policies/", headers=admin_headers, json=data)
        assert response.status_code == 201
        result = response.json()
        assert result["frequency_months"] == 6
        assert result["risk_tier"]["label"] == "Tier 1"

    def test_create_policy_as_validator_fails(self, client, validator_headers, taxonomy_values):
        """Validator cannot create policy."""
        data = {
            "risk_tier_id": taxonomy_values["tier1"].value_id,
            "frequency_months": 6
        }
        response = client.post("/validations/policies/", headers=validator_headers, json=data)
        assert response.status_code == 403
        assert "Only Admins" in response.json()["detail"]

    def test_create_policy_duplicate_tier_fails(self, client, admin_headers, taxonomy_values):
        """Cannot create duplicate policy for same risk tier."""
        data = {
            "risk_tier_id": taxonomy_values["tier1"].value_id,
            "frequency_months": 6
        }
        client.post("/validations/policies/", headers=admin_headers, json=data)

        # Try to create duplicate
        response = client.post("/validations/policies/", headers=admin_headers, json=data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_policy_invalid_tier(self, client, admin_headers):
        """Create policy with non-existent tier fails."""
        data = {
            "risk_tier_id": 9999,
            "frequency_months": 6
        }
        response = client.post("/validations/policies/", headers=admin_headers, json=data)
        assert response.status_code == 404

    def test_update_policy(self, client, admin_headers, taxonomy_values):
        """Admin can update policy."""
        # Create policy
        data = {
            "risk_tier_id": taxonomy_values["tier1"].value_id,
            "frequency_months": 6
        }
        create_resp = client.post("/validations/policies/", headers=admin_headers, json=data)
        policy_id = create_resp.json()["policy_id"]

        # Update policy
        update_data = {
            "frequency_months": 3,
            "description": "Updated to quarterly"
        }
        response = client.patch(f"/validations/policies/{policy_id}", headers=admin_headers, json=update_data)
        assert response.status_code == 200
        assert response.json()["frequency_months"] == 3
        assert response.json()["description"] == "Updated to quarterly"

    def test_update_policy_as_validator_fails(self, client, admin_headers, validator_headers, taxonomy_values):
        """Validator cannot update policy."""
        # Create policy as admin
        data = {
            "risk_tier_id": taxonomy_values["tier1"].value_id,
            "frequency_months": 6
        }
        create_resp = client.post("/validations/policies/", headers=admin_headers, json=data)
        policy_id = create_resp.json()["policy_id"]

        # Try to update as validator
        update_data = {"frequency_months": 3}
        response = client.patch(f"/validations/policies/{policy_id}", headers=validator_headers, json=update_data)
        assert response.status_code == 403

    def test_delete_policy(self, client, admin_headers, taxonomy_values):
        """Admin can delete policy."""
        # Create policy
        data = {
            "risk_tier_id": taxonomy_values["tier1"].value_id,
            "frequency_months": 6
        }
        create_resp = client.post("/validations/policies/", headers=admin_headers, json=data)
        policy_id = create_resp.json()["policy_id"]

        # Delete policy
        response = client.delete(f"/validations/policies/{policy_id}", headers=admin_headers)
        assert response.status_code == 204

        # Verify deletion
        list_resp = client.get("/validations/policies/", headers=admin_headers)
        assert len(list_resp.json()) == 0

    def test_delete_policy_not_found(self, client, admin_headers):
        """Delete non-existent policy returns 404."""
        response = client.delete("/validations/policies/9999", headers=admin_headers)
        assert response.status_code == 404


class TestValidationAuditLogs:
    """Test audit logging for validation operations."""

    def test_create_validation_creates_audit_log(self, client, validator_headers, sample_model, validator_user, taxonomy_values, db_session):
        """Creating validation creates audit log."""
        data = {
            "model_id": sample_model.model_id,
            "validation_date": "2025-01-15",
            "validator_id": validator_user.user_id,
            "validation_type_id": taxonomy_values["initial"].value_id,
            "outcome_id": taxonomy_values["pass"].value_id,
            "scope_id": taxonomy_values["full_scope"].value_id
        }
        response = client.post("/validations/", headers=validator_headers, json=data)
        validation_id = response.json()["validation_id"]

        # Check audit log
        audit_resp = client.get(f"/audit-logs/?entity_type=Validation&entity_id={validation_id}", headers=validator_headers)
        assert audit_resp.status_code == 200
        logs = audit_resp.json()
        assert len(logs) == 1
        assert logs[0]["action"] == "CREATE"
        assert logs[0]["changes"]["model_name"] == sample_model.model_name

    def test_update_validation_creates_audit_log(self, client, validator_headers, sample_model, validator_user, taxonomy_values):
        """Updating validation creates audit log with changes."""
        # Create validation
        data = {
            "model_id": sample_model.model_id,
            "validation_date": "2025-01-15",
            "validator_id": validator_user.user_id,
            "validation_type_id": taxonomy_values["initial"].value_id,
            "outcome_id": taxonomy_values["pass"].value_id,
            "scope_id": taxonomy_values["full_scope"].value_id,
            "findings_summary": "Initial findings"
        }
        create_resp = client.post("/validations/", headers=validator_headers, json=data)
        validation_id = create_resp.json()["validation_id"]

        # Update validation
        update_data = {"findings_summary": "Updated findings"}
        client.patch(f"/validations/{validation_id}", headers=validator_headers, json=update_data)

        # Check audit log
        audit_resp = client.get(f"/audit-logs/?entity_type=Validation&entity_id={validation_id}", headers=validator_headers)
        logs = audit_resp.json()
        assert len(logs) == 2
        update_log = next(log for log in logs if log["action"] == "UPDATE")
        assert update_log["changes"]["findings_summary"]["old"] == "Initial findings"
        assert update_log["changes"]["findings_summary"]["new"] == "Updated findings"

    def test_delete_validation_creates_audit_log(self, client, admin_headers, validator_headers, sample_model, validator_user, taxonomy_values):
        """Deleting validation creates audit log."""
        # Create validation
        data = {
            "model_id": sample_model.model_id,
            "validation_date": "2025-01-15",
            "validator_id": validator_user.user_id,
            "validation_type_id": taxonomy_values["initial"].value_id,
            "outcome_id": taxonomy_values["pass"].value_id,
            "scope_id": taxonomy_values["full_scope"].value_id
        }
        create_resp = client.post("/validations/", headers=validator_headers, json=data)
        validation_id = create_resp.json()["validation_id"]

        # Delete validation
        client.delete(f"/validations/{validation_id}", headers=admin_headers)

        # Check audit log
        audit_resp = client.get(f"/audit-logs/?entity_type=Validation&entity_id={validation_id}", headers=admin_headers)
        logs = audit_resp.json()
        delete_log = next(log for log in logs if log["action"] == "DELETE")
        assert delete_log["changes"]["model_name"] == sample_model.model_name


class TestDashboardEndpoints:
    """Test dashboard helper endpoints."""

    def test_overdue_models_admin_only(self, client, auth_headers, taxonomy_values):
        """Only admin can access overdue models endpoint."""
        response = client.get("/validations/dashboard/overdue", headers=auth_headers)
        assert response.status_code == 403

    def test_overdue_models_empty(self, client, admin_headers, taxonomy_values):
        """Get overdue models when no policies configured."""
        response = client.get("/validations/dashboard/overdue", headers=admin_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_pass_with_findings_admin_only(self, client, auth_headers, taxonomy_values):
        """Only admin can access pass-with-findings endpoint."""
        response = client.get("/validations/dashboard/pass-with-findings", headers=auth_headers)
        assert response.status_code == 403

    def test_pass_with_findings_returns_correct_validations(self, client, admin_headers, validator_headers, sample_model, validator_user, taxonomy_values):
        """Get validations with pass-with-findings outcome."""
        # Create validation with pass-with-findings
        data = {
            "model_id": sample_model.model_id,
            "validation_date": "2025-01-15",
            "validator_id": validator_user.user_id,
            "validation_type_id": taxonomy_values["initial"].value_id,
            "outcome_id": taxonomy_values["pass_with_findings"].value_id,
            "scope_id": taxonomy_values["full_scope"].value_id,
            "findings_summary": "Some issues found"
        }
        client.post("/validations/", headers=validator_headers, json=data)

        response = client.get("/validations/dashboard/pass-with-findings", headers=admin_headers)
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["findings_summary"] == "Some issues found"
        assert results[0]["has_recommendations"] is False
