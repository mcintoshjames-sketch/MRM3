"""Tests for Conditional Model Use Approvals feature."""
import pytest
from datetime import date, datetime
from app.models.conditional_approval import ApproverRole, ConditionalApprovalRule, RuleRequiredApprover
from app.models.validation import ValidationRequest, ValidationApproval
from app.models.region import Region
from app.models.model import Model
from app.models.model_region import ModelRegion
from app.core.rule_evaluation import get_required_approver_roles


class TestApproverRoleCRUD:
    """Test ApproverRole CRUD operations."""

    def test_list_approver_roles_when_empty(self, client, admin_headers):
        """List approver roles when database is empty."""
        response = client.get("/approver-roles/", headers=admin_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_approver_roles_with_data(self, client, db_session, admin_headers):
        """List approver roles with existing data."""
        role1 = ApproverRole(role_name="US MRM Committee", description="US committee")
        role2 = ApproverRole(role_name="EU MRM Committee", description="EU committee")
        db_session.add_all([role1, role2])
        db_session.commit()

        response = client.get("/approver-roles/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Check both roles exist (order-agnostic)
        role_names = {r["role_name"] for r in data}
        assert "US MRM Committee" in role_names
        assert "EU MRM Committee" in role_names

    def test_list_approver_roles_filtered_by_active(self, client, db_session, admin_headers):
        """List approver roles filtered by is_active."""
        role1 = ApproverRole(role_name="Active Role", is_active=True)
        role2 = ApproverRole(role_name="Inactive Role", is_active=False)
        db_session.add_all([role1, role2])
        db_session.commit()

        response = client.get("/approver-roles/?is_active=true", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["role_name"] == "Active Role"

    def test_list_approver_roles_includes_rules_count(self, client, db_session, admin_headers):
        """List approver roles includes count of rules using each role."""
        role = ApproverRole(role_name="Test Role")
        db_session.add(role)
        db_session.flush()

        rule = ConditionalApprovalRule(rule_name="Test Rule", is_active=True)
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        response = client.get("/approver-roles/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["rules_count"] == 1

    def test_create_approver_role_as_admin_succeeds(self, client, admin_headers):
        """Create approver role as Admin succeeds."""
        payload = {
            "role_name": "New Committee",
            "description": "Test description",
            "is_active": True
        }
        response = client.post("/approver-roles/", json=payload, headers=admin_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["role_name"] == "New Committee"
        assert data["description"] == "Test description"
        assert data["is_active"] is True

    def test_create_approver_role_as_non_admin_fails(self, client, auth_headers):
        """Create approver role as non-Admin fails with 403."""
        payload = {"role_name": "New Committee"}
        response = client.post("/approver-roles/", json=payload, headers=auth_headers)
        assert response.status_code == 403

    def test_create_approver_role_with_duplicate_name_fails(self, client, db_session, admin_headers):
        """Create approver role with duplicate name fails with 400."""
        role = ApproverRole(role_name="Existing Role")
        db_session.add(role)
        db_session.commit()

        payload = {"role_name": "Existing Role"}
        response = client.post("/approver-roles/", json=payload, headers=admin_headers)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_update_approver_role_as_admin_succeeds(self, client, db_session, admin_headers):
        """Update approver role as Admin succeeds."""
        role = ApproverRole(role_name="Old Name", description="Old description")
        db_session.add(role)
        db_session.commit()

        payload = {"description": "New description", "is_active": False}
        response = client.patch(f"/approver-roles/{role.role_id}", json=payload, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "New description"
        assert data["is_active"] is False

    def test_soft_delete_approver_role(self, client, db_session, admin_headers):
        """Soft delete approver role sets is_active=false."""
        role = ApproverRole(role_name="Role to Delete", is_active=True)
        db_session.add(role)
        db_session.commit()

        response = client.delete(f"/approver-roles/{role.role_id}", headers=admin_headers)
        assert response.status_code == 200

        db_session.refresh(role)
        assert role.is_active is False

    def test_cannot_delete_approver_role_used_in_active_rules(self, client, db_session, admin_headers):
        """Cannot delete approver role if used in active rules."""
        role = ApproverRole(role_name="Active Role")
        db_session.add(role)
        db_session.flush()

        rule = ConditionalApprovalRule(rule_name="Active Rule", is_active=True)
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        response = client.delete(f"/approver-roles/{role.role_id}", headers=admin_headers)
        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "active rule" in detail or "cannot delete" in detail


class TestConditionalApprovalRuleCRUD:
    """Test ConditionalApprovalRule CRUD operations."""

    def test_list_rules_when_empty(self, client, admin_headers):
        """List rules when database is empty."""
        response = client.get("/conditional-approval-rules/", headers=admin_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_rules_with_data(self, client, db_session, admin_headers):
        """List rules with data includes required approver roles."""
        role = ApproverRole(role_name="Test Role")
        db_session.add(role)
        db_session.flush()

        rule = ConditionalApprovalRule(rule_name="Test Rule", validation_type_ids="1,2")
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        response = client.get("/conditional-approval-rules/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["rule_name"] == "Test Rule"
        # List endpoint uses different schema with summary fields
        assert "Test Role" in data[0]["required_approver_names"]

    def test_list_rules_filtered_by_active(self, client, db_session, admin_headers):
        """List rules filtered by is_active."""
        rule1 = ConditionalApprovalRule(rule_name="Active Rule", is_active=True)
        rule2 = ConditionalApprovalRule(rule_name="Inactive Rule", is_active=False)
        db_session.add_all([rule1, rule2])
        db_session.commit()

        response = client.get("/conditional-approval-rules/?is_active=true", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["rule_name"] == "Active Rule"

    def test_create_rule_with_all_dimensions_specified(self, client, db_session, admin_headers):
        """Create rule with all dimensions specified."""
        role = ApproverRole(role_name="Test Role")
        db_session.add(role)
        db_session.commit()

        payload = {
            "rule_name": "Complete Rule",
            "description": "Test rule with all dimensions",
            "validation_type_ids": [1, 2],
            "risk_tier_ids": [1],
            "governance_region_ids": [1],
            "deployed_region_ids": [1, 2],
            "required_approver_role_ids": [role.role_id]
        }
        response = client.post("/conditional-approval-rules/", json=payload, headers=admin_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["rule_name"] == "Complete Rule"
        assert data["validation_type_ids"] == [1, 2]
        assert data["risk_tier_ids"] == [1]

    def test_create_rule_with_empty_dimensions(self, client, db_session, admin_headers):
        """Create rule with empty dimensions (matches ANY)."""
        role = ApproverRole(role_name="Test Role")
        db_session.add(role)
        db_session.commit()

        payload = {
            "rule_name": "Match Any Rule",
            "validation_type_ids": None,
            "risk_tier_ids": None,
            "governance_region_ids": None,
            "deployed_region_ids": None,
            "required_approver_role_ids": [role.role_id]
        }
        response = client.post("/conditional-approval-rules/", json=payload, headers=admin_headers)
        assert response.status_code == 201
        data = response.json()
        # Empty dimensions return as empty lists
        assert data["validation_type_ids"] == []
        assert data["risk_tier_ids"] == []

    def test_create_rule_with_multiple_required_approver_roles(self, client, db_session, admin_headers):
        """Create rule with multiple required approver roles."""
        role1 = ApproverRole(role_name="Role 1")
        role2 = ApproverRole(role_name="Role 2")
        db_session.add_all([role1, role2])
        db_session.commit()

        payload = {
            "rule_name": "Multi-Approver Rule",
            "required_approver_role_ids": [role1.role_id, role2.role_id]
        }
        response = client.post("/conditional-approval-rules/", json=payload, headers=admin_headers)
        assert response.status_code == 201
        data = response.json()
        assert len(data["required_approver_roles"]) == 2

    def test_create_rule_as_non_admin_fails(self, client, db_session, auth_headers):
        """Create rule as non-Admin fails with 403."""
        role = ApproverRole(role_name="Test Role")
        db_session.add(role)
        db_session.commit()

        payload = {
            "rule_name": "Test Rule",
            "required_approver_role_ids": [role.role_id]
        }
        response = client.post("/conditional-approval-rules/", json=payload, headers=auth_headers)
        assert response.status_code == 403

    def test_update_rule_dimensions(self, client, db_session, admin_headers):
        """Update rule dimensions."""
        role = ApproverRole(role_name="Test Role")
        db_session.add(role)
        db_session.flush()

        rule = ConditionalApprovalRule(rule_name="Test Rule", validation_type_ids="1")
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        payload = {
            "validation_type_ids": [1, 2, 3],
            "risk_tier_ids": [1]
        }
        response = client.patch(f"/conditional-approval-rules/{rule.rule_id}", json=payload, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["validation_type_ids"] == [1, 2, 3]
        assert data["risk_tier_ids"] == [1]

    def test_update_rule_required_approver_roles(self, client, db_session, admin_headers):
        """Update rule required approver roles."""
        role1 = ApproverRole(role_name="Role 1")
        role2 = ApproverRole(role_name="Role 2")
        db_session.add_all([role1, role2])
        db_session.flush()

        rule = ConditionalApprovalRule(rule_name="Test Rule")
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role1.role_id)
        db_session.add(assoc)
        db_session.commit()

        payload = {"required_approver_role_ids": [role2.role_id]}
        response = client.patch(f"/conditional-approval-rules/{rule.rule_id}", json=payload, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["required_approver_roles"]) == 1
        assert data["required_approver_roles"][0]["role_id"] == role2.role_id

    def test_soft_delete_rule(self, client, db_session, admin_headers):
        """Soft delete rule sets is_active=false."""
        role = ApproverRole(role_name="Test Role")
        db_session.add(role)
        db_session.flush()

        rule = ConditionalApprovalRule(rule_name="Rule to Delete", is_active=True)
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        response = client.delete(f"/conditional-approval-rules/{rule.rule_id}", headers=admin_headers)
        assert response.status_code == 200

        db_session.refresh(rule)
        assert rule.is_active is False

    def test_preview_rule_translation_endpoint(self, client, db_session, admin_headers, taxonomy_values):
        """Preview rule translation endpoint returns English description."""
        role = ApproverRole(role_name="US MRM Committee")
        db_session.add(role)
        db_session.commit()

        payload = {
            "validation_type_ids": [taxonomy_values["initial"].value_id],
            "risk_tier_ids": [taxonomy_values["tier1"].value_id],
            "governance_region_ids": None,
            "deployed_region_ids": None,
            "required_approver_role_ids": [role.role_id]
        }
        response = client.post("/conditional-approval-rules/preview", json=payload, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "translation" in data
        assert "US MRM Committee" in data["translation"]

    def test_preview_handles_empty_dimensions_correctly(self, client, db_session, admin_headers):
        """Preview handles empty dimensions correctly (matches ANY)."""
        role = ApproverRole(role_name="Global Officer")
        db_session.add(role)
        db_session.commit()

        payload = {
            "validation_type_ids": None,
            "risk_tier_ids": None,
            "governance_region_ids": None,
            "deployed_region_ids": None,
            "required_approver_role_ids": [role.role_id]
        }
        response = client.post("/conditional-approval-rules/preview", json=payload, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "Global Officer" in data["translation"]


class TestRuleEvaluationLogic:
    """Test rule evaluation logic."""

    def test_no_rules_configured_returns_empty(self, db_session, test_user, taxonomy_values):
        """No rules configured returns empty required roles."""
        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id,
            risk_tier_id=taxonomy_values["tier1"].value_id
        )
        db_session.add(model)
        db_session.flush()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        validation_request.models = [model]
        db_session.add(validation_request)
        db_session.commit()

        result = get_required_approver_roles(db_session, validation_request, model)
        assert result["required_roles"] == []

    def test_single_matching_rule_returns_one_role(self, db_session, test_user, taxonomy_values):
        """Single matching rule returns one required role."""
        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        rule = ConditionalApprovalRule(
            rule_name="Test Rule",
            validation_type_ids=str(taxonomy_values["initial"].value_id),
            risk_tier_ids=str(taxonomy_values["tier1"].value_id),
            is_active=True
        )
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id,
            risk_tier_id=taxonomy_values["tier1"].value_id
        )
        db_session.add(model)
        db_session.flush()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        validation_request.models = [model]
        db_session.add(validation_request)
        db_session.commit()

        result = get_required_approver_roles(db_session, validation_request, model)
        assert len(result["required_roles"]) == 1
        assert result["required_roles"][0]["role_name"] == "Test Committee"

    def test_multiple_matching_rules_return_deduplicated_roles(self, db_session, test_user, taxonomy_values):
        """Multiple matching rules return deduplicated roles."""
        role = ApproverRole(role_name="Shared Committee")
        db_session.add(role)
        db_session.flush()

        rule1 = ConditionalApprovalRule(
            rule_name="Rule 1",
            validation_type_ids=str(taxonomy_values["initial"].value_id),
            is_active=True
        )
        rule2 = ConditionalApprovalRule(
            rule_name="Rule 2",
            risk_tier_ids=str(taxonomy_values["tier1"].value_id),
            is_active=True
        )
        db_session.add_all([rule1, rule2])
        db_session.flush()

        assoc1 = RuleRequiredApprover(rule_id=rule1.rule_id, approver_role_id=role.role_id)
        assoc2 = RuleRequiredApprover(rule_id=rule2.rule_id, approver_role_id=role.role_id)
        db_session.add_all([assoc1, assoc2])
        db_session.commit()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id,
            risk_tier_id=taxonomy_values["tier1"].value_id
        )
        db_session.add(model)
        db_session.flush()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        validation_request.models = [model]
        db_session.add(validation_request)
        db_session.commit()

        result = get_required_approver_roles(db_session, validation_request, model)
        assert len(result["required_roles"]) == 1  # Deduplicated

    def test_rule_matches_when_all_non_empty_dimensions_match(self, db_session, test_user, taxonomy_values):
        """Rule matches when all non-empty dimensions match."""
        region = Region(name="US", code="US")
        db_session.add(region)
        db_session.flush()

        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        rule = ConditionalApprovalRule(
            rule_name="Multi-Dimension Rule",
            validation_type_ids=str(taxonomy_values["initial"].value_id),
            risk_tier_ids=str(taxonomy_values["tier1"].value_id),
            governance_region_ids=str(region.region_id),
            is_active=True
        )
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id,
            risk_tier_id=taxonomy_values["tier1"].value_id,
            wholly_owned_region_id=region.region_id
        )
        db_session.add(model)
        db_session.flush()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        validation_request.models = [model]
        db_session.add(validation_request)
        db_session.commit()

        result = get_required_approver_roles(db_session, validation_request, model)
        assert len(result["required_roles"]) == 1

    def test_rule_does_not_match_when_one_dimension_fails(self, db_session, test_user, taxonomy_values):
        """Rule does not match when one dimension fails."""
        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        rule = ConditionalApprovalRule(
            rule_name="Strict Rule",
            validation_type_ids=str(taxonomy_values["initial"].value_id),
            risk_tier_ids=str(taxonomy_values["tier1"].value_id),
            is_active=True
        )
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id,
            risk_tier_id=taxonomy_values["tier2"].value_id  # Doesn't match tier1
        )
        db_session.add(model)
        db_session.flush()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        validation_request.models = [model]
        db_session.add(validation_request)
        db_session.commit()

        result = get_required_approver_roles(db_session, validation_request, model)
        assert len(result["required_roles"]) == 0

    def test_empty_validation_type_ids_matches_any_validation_type(self, db_session, test_user, taxonomy_values):
        """Empty validation_type_ids matches ANY validation type."""
        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        rule = ConditionalApprovalRule(
            rule_name="Any Validation Type Rule",
            validation_type_ids=None,  # Empty = matches ANY
            risk_tier_ids=str(taxonomy_values["tier1"].value_id),
            is_active=True
        )
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id,
            risk_tier_id=taxonomy_values["tier1"].value_id
        )
        db_session.add(model)
        db_session.flush()

        # Should match both initial and annual
        for val_type in [taxonomy_values["initial"], taxonomy_values["annual"]]:
            validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
                validation_type_id=val_type.value_id,
                priority_id=val_type.value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
            )
            validation_request.models = [model]
            db_session.add(validation_request)
            db_session.commit()

            result = get_required_approver_roles(db_session, validation_request, model)
            assert len(result["required_roles"]) == 1
            db_session.delete(validation_request)
            db_session.commit()

    def test_empty_risk_tier_ids_matches_any_risk_tier(self, db_session, test_user, taxonomy_values):
        """Empty risk_tier_ids matches ANY risk tier."""
        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        rule = ConditionalApprovalRule(
            rule_name="Any Risk Tier Rule",
            validation_type_ids=str(taxonomy_values["initial"].value_id),
            risk_tier_ids=None,  # Empty = matches ANY
            is_active=True
        )
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        db_session.add(validation_request)
        db_session.flush()

        # Should match both tier1 and tier2
        for tier in [taxonomy_values["tier1"], taxonomy_values["tier2"]]:
            model = Model(
                model_name=f"Model {tier.code}",
                owner_id=test_user.user_id,
                risk_tier_id=tier.value_id
            )
            db_session.add(model)
            db_session.flush()

            validation_request.models = [model]
            result = get_required_approver_roles(db_session, validation_request, model)
            assert len(result["required_roles"]) == 1
            db_session.delete(model)
            db_session.commit()

    def test_empty_governance_region_ids_matches_any_governance_region(self, db_session, test_user, taxonomy_values):
        """Empty governance_region_ids matches ANY governance region."""
        region1 = Region(name="US", code="US")
        region2 = Region(name="EU", code="EU")
        db_session.add_all([region1, region2])
        db_session.flush()

        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        rule = ConditionalApprovalRule(
            rule_name="Any Region Rule",
            validation_type_ids=str(taxonomy_values["initial"].value_id),
            governance_region_ids=None,  # Empty = matches ANY
            is_active=True
        )
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        db_session.add(validation_request)
        db_session.flush()

        # Should match both US and EU
        for region in [region1, region2]:
            model = Model(
                model_name=f"Model {region.code}",
                owner_id=test_user.user_id,
                wholly_owned_region_id=region.region_id
            )
            db_session.add(model)
            db_session.flush()

            validation_request.models = [model]
            result = get_required_approver_roles(db_session, validation_request, model)
            assert len(result["required_roles"]) == 1
            db_session.delete(model)
            db_session.commit()

    def test_empty_deployed_region_ids_matches_any_deployed_regions(self, db_session, test_user, taxonomy_values):
        """Empty deployed_region_ids matches ANY deployed regions."""
        region1 = Region(name="US", code="US")
        region2 = Region(name="EU", code="EU")
        db_session.add_all([region1, region2])
        db_session.flush()

        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        rule = ConditionalApprovalRule(
            rule_name="Any Deployed Region Rule",
            validation_type_ids=str(taxonomy_values["initial"].value_id),
            deployed_region_ids=None,  # Empty = matches ANY
            is_active=True
        )
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id
        )
        db_session.add(model)
        db_session.flush()

        # Add model region
        model_region = ModelRegion(model_id=model.model_id, region_id=region1.region_id)
        db_session.add(model_region)
        db_session.commit()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        validation_request.models = [model]
        db_session.add(validation_request)
        db_session.commit()

        result = get_required_approver_roles(db_session, validation_request, model)
        assert len(result["required_roles"]) == 1

    def test_deployed_regions_any_overlap_triggers_rule(self, db_session, test_user, taxonomy_values):
        """Deployed regions: ANY overlap triggers rule."""
        region1 = Region(name="US", code="US")
        region2 = Region(name="EU", code="EU")
        region3 = Region(name="UK", code="UK")
        db_session.add_all([region1, region2, region3])
        db_session.flush()

        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        # Rule requires US or EU
        rule = ConditionalApprovalRule(
            rule_name="US/EU Rule",
            validation_type_ids=str(taxonomy_values["initial"].value_id),
            deployed_region_ids=f"{region1.region_id},{region2.region_id}",
            is_active=True
        )
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id
        )
        db_session.add(model)
        db_session.flush()

        # Model deployed to US and UK
        model_region1 = ModelRegion(model_id=model.model_id, region_id=region1.region_id)
        model_region2 = ModelRegion(model_id=model.model_id, region_id=region3.region_id)
        db_session.add_all([model_region1, model_region2])
        db_session.commit()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        validation_request.models = [model]
        db_session.add(validation_request)
        db_session.commit()

        result = get_required_approver_roles(db_session, validation_request, model)
        assert len(result["required_roles"]) == 1  # Triggered because US overlaps

    def test_deployed_regions_no_overlap_does_not_trigger_rule(self, db_session, test_user, taxonomy_values):
        """Deployed regions: no overlap does not trigger rule."""
        region1 = Region(name="US", code="US")
        region2 = Region(name="EU", code="EU")
        region3 = Region(name="UK", code="UK")
        db_session.add_all([region1, region2, region3])
        db_session.flush()

        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        # Rule requires US or EU
        rule = ConditionalApprovalRule(
            rule_name="US/EU Rule",
            validation_type_ids=str(taxonomy_values["initial"].value_id),
            deployed_region_ids=f"{region1.region_id},{region2.region_id}",
            is_active=True
        )
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id
        )
        db_session.add(model)
        db_session.flush()

        # Model only deployed to UK (no overlap)
        model_region = ModelRegion(model_id=model.model_id, region_id=region3.region_id)
        db_session.add(model_region)
        db_session.commit()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        validation_request.models = [model]
        db_session.add(validation_request)
        db_session.commit()

        result = get_required_approver_roles(db_session, validation_request, model)
        assert len(result["required_roles"]) == 0  # No overlap, rule doesn't apply

    def test_existing_approval_prevents_duplicate_requirement_creation(self, db_session, test_user, taxonomy_values):
        """Existing approval prevents duplicate requirement creation."""
        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        rule = ConditionalApprovalRule(
            rule_name="Test Rule",
            validation_type_ids=str(taxonomy_values["initial"].value_id),
            is_active=True
        )
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id
        )
        db_session.add(model)
        db_session.flush()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        db_session.add(validation_request)
        db_session.flush()

        # Create association record (models relationship is viewonly)
        from app.models.validation import ValidationRequestModelVersion
        assoc = ValidationRequestModelVersion(
            request_id=validation_request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(assoc)
        db_session.flush()

        # Create existing approval
        approval = ValidationApproval(
            request_id=validation_request.request_id,
            approver_role_id=role.role_id,
            approver_id=test_user.user_id,
            approval_status="Pending",
            approver_role="Admin",
        )
        db_session.add(approval)
        db_session.commit()

        result = get_required_approver_roles(db_session, validation_request, model)
        assert len(result["required_roles"]) == 1
        assert result["required_roles"][0]["approval_id"] is not None

    def test_voided_approval_does_not_prevent_re_evaluation(self, db_session, test_user, admin_user, taxonomy_values):
        """Voided approval does not prevent re-evaluation."""
        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        rule = ConditionalApprovalRule(
            rule_name="Test Rule",
            validation_type_ids=str(taxonomy_values["initial"].value_id),
            is_active=True
        )
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id
        )
        db_session.add(model)
        db_session.flush()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        db_session.add(validation_request)
        db_session.flush()

        # Create association record (models relationship is viewonly)
        from app.models.validation import ValidationRequestModelVersion
        assoc = ValidationRequestModelVersion(
            request_id=validation_request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(assoc)
        db_session.flush()

        # Create voided approval
        approval = ValidationApproval(
            request_id=validation_request.request_id,
            approver_role_id=role.role_id,
            approver_id=admin_user.user_id,
            approval_status="Pending",
            approver_role="Admin",
            voided_by_id=admin_user.user_id,
            void_reason="Test void",
            voided_at=datetime.now()
        )
        db_session.add(approval)
        db_session.commit()

        result = get_required_approver_roles(db_session, validation_request, model)
        assert len(result["required_roles"]) == 1
        assert result["required_roles"][0]["approval_id"] is None  # Voided approval ignored

    def test_english_translation_includes_all_matching_dimensions(self, db_session, test_user, taxonomy_values):
        """English translation includes all matching dimensions."""
        region = Region(name="United States", code="US")
        db_session.add(region)
        db_session.flush()

        role = ApproverRole(role_name="US MRM Committee")
        db_session.add(role)
        db_session.flush()

        rule = ConditionalApprovalRule(
            rule_name="Complete Rule",
            validation_type_ids=str(taxonomy_values["initial"].value_id),
            risk_tier_ids=str(taxonomy_values["tier1"].value_id),
            governance_region_ids=str(region.region_id),
            is_active=True
        )
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id,
            risk_tier_id=taxonomy_values["tier1"].value_id,
            wholly_owned_region_id=region.region_id
        )
        db_session.add(model)
        db_session.flush()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        validation_request.models = [model]
        db_session.add(validation_request)
        db_session.commit()

        result = get_required_approver_roles(db_session, validation_request, model)
        explanation = result["rules_applied"][0]["explanation"]
        assert "US MRM Committee" in explanation
        assert "Initial" in explanation or "validation type" in explanation.lower()
        assert "Tier 1" in explanation or "risk tier" in explanation.lower()
        assert "United States" in explanation or "governance region" in explanation.lower()

    def test_english_translation_handles_or_within_dimensions_correctly(self, db_session, test_user, taxonomy_values):
        """English translation handles OR within dimensions correctly."""
        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        rule = ConditionalApprovalRule(
            rule_name="Multi-Value Rule",
            validation_type_ids=f"{taxonomy_values['initial'].value_id},{taxonomy_values['annual'].value_id}",
            is_active=True
        )
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id
        )
        db_session.add(model)
        db_session.flush()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        validation_request.models = [model]
        db_session.add(validation_request)
        db_session.commit()

        result = get_required_approver_roles(db_session, validation_request, model)
        explanation = result["rules_applied"][0]["explanation"]
        # Should indicate OR logic
        assert "one of" in explanation.lower() or "," in explanation


class TestApprovalWorkflowIntegration:
    """Test approval workflow integration."""

    def test_rule_evaluation_on_validation_request_creation(self, client, db_session, test_user, admin_user, admin_headers, taxonomy_values):
        """Rule evaluation happens when validation request is created."""
        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        rule = ConditionalApprovalRule(
            rule_name="Test Rule",
            validation_type_ids=str(taxonomy_values["initial"].value_id),
            is_active=True
        )
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id,
            row_approval_status="approved"
        )
        db_session.add(model)
        db_session.commit()

        payload = {
            "validation_type_id": taxonomy_values["initial"].value_id,
            "priority_id": taxonomy_values["priority_high"].value_id,
            "model_ids": [model.model_id],
            "target_completion_date": "2025-12-31"
        }
        response = client.post("/validation-workflow/requests/", json=payload, headers=admin_headers)
        assert response.status_code == 201

        request_id = response.json()["request_id"]

        # Check that approval was created
        approval = db_session.query(ValidationApproval).filter(
            ValidationApproval.request_id == request_id,
            ValidationApproval.approver_role_id == role.role_id
        ).first()
        assert approval is not None
        assert approval.approval_status == "Pending"

    def test_rule_re_evaluation_when_moving_to_pending_approval_status(self, client, db_session, test_user, admin_user, admin_headers, taxonomy_values, validator_user):
        """Rule re-evaluation happens when moving to Pending Approval status."""
        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        rule = ConditionalApprovalRule(
            rule_name="Test Rule",
            risk_tier_ids=str(taxonomy_values["tier1"].value_id),
            is_active=True
        )
        db_session.add(rule)
        db_session.flush()

        assoc = RuleRequiredApprover(rule_id=rule.rule_id, approver_role_id=role.role_id)
        db_session.add(assoc)
        db_session.commit()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id,
            risk_tier_id=None,  # Initially null
            row_approval_status="approved"
        )
        db_session.add(model)
        db_session.commit()

        # Create validation request
        payload = {
            "validation_type_id": taxonomy_values["initial"].value_id,
            "priority_id": taxonomy_values["priority_high"].value_id,
            "model_ids": [model.model_id],
            "target_completion_date": "2025-12-31"
        }
        response = client.post("/validation-workflow/requests/", json=payload, headers=admin_headers)
        assert response.status_code == 201
        request_id = response.json()["request_id"]

        # Assign primary validator (required for moving to PLANNING)
        from app.models.validation import ValidationAssignment
        assignment = ValidationAssignment(
            request_id=request_id,
            validator_id=validator_user.user_id,
            is_primary=True,
            assignment_date=date.today()
        )
        db_session.add(assignment)
        db_session.commit()

        # Update model risk tier
        model.risk_tier_id = taxonomy_values["tier1"].value_id
        db_session.commit()

        # Progress through workflow states: INTAKE → PLANNING → IN_PROGRESS → REVIEW → PENDING_APPROVAL
        for status_name in ["status_planning", "status_in_progress", "status_review", "status_pending_approval"]:
            status_payload = {
                "new_status_id": taxonomy_values[status_name].value_id,
                "reason": f"Moving to {status_name}"
            }
            response = client.patch(f"/validation-workflow/requests/{request_id}/status", json=status_payload, headers=admin_headers)
            if response.status_code != 200:
                print(f"ERROR at {status_name}: {response.status_code} - {response.json()}")
            assert response.status_code == 200

        # Check that approval was created during re-evaluation
        approval = db_session.query(ValidationApproval).filter(
            ValidationApproval.request_id == request_id,
            ValidationApproval.approver_role_id == role.role_id
        ).first()
        assert approval is not None

    def test_submit_conditional_approval_as_admin_with_evidence(self, client, db_session, test_user, admin_user, admin_headers, taxonomy_values):
        """Submit conditional approval as Admin with evidence."""
        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id,
            row_approval_status="approved"
        )
        db_session.add(model)
        db_session.flush()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        db_session.add(validation_request)
        db_session.flush()

        # Create association record (models relationship is viewonly)
        from app.models.validation import ValidationRequestModelVersion
        assoc = ValidationRequestModelVersion(
            request_id=validation_request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(assoc)
        db_session.flush()

        approval = ValidationApproval(
            request_id=validation_request.request_id,
            approver_role_id=role.role_id,
            approver_id=admin_user.user_id,
            approval_status="Pending",
            approver_role="Admin",
        )
        db_session.add(approval)
        db_session.commit()

        payload = {
            "approver_role_id": role.role_id,
            "approval_status": "Approved",
            "approval_evidence": "Approved via MRM Committee meeting minutes 2025-11-23",
            "comments": "All conditions met"
        }
        response = client.post(f"/validation-workflow/approvals/{approval.approval_id}/submit-conditional", json=payload, headers=admin_headers)
        assert response.status_code == 200

        db_session.refresh(approval)
        assert approval.approval_status == "Approved"
        assert approval.approval_evidence == "Approved via MRM Committee meeting minutes 2025-11-23"
        assert approval.approver_id == admin_user.user_id

    def test_submit_conditional_approval_as_non_admin_fails(self, client, db_session, test_user, admin_user, auth_headers, taxonomy_values):
        """Submit conditional approval as non-Admin fails with 403."""
        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id,
            row_approval_status="approved"
        )
        db_session.add(model)
        db_session.flush()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        db_session.add(validation_request)
        db_session.flush()

        # Create association record (models relationship is viewonly)
        from app.models.validation import ValidationRequestModelVersion
        assoc = ValidationRequestModelVersion(
            request_id=validation_request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(assoc)
        db_session.flush()

        approval = ValidationApproval(
            request_id=validation_request.request_id,
            approver_role_id=role.role_id,
            approver_id=admin_user.user_id,
            approval_status="Pending",
            approver_role="Admin",
        )
        db_session.add(approval)
        db_session.commit()

        payload = {
            "approver_role_id": role.role_id,
            "approval_status": "Approved",
            "approval_evidence": "Test evidence"
        }
        response = client.post(f"/validation-workflow/approvals/{approval.approval_id}/submit-conditional", json=payload, headers=auth_headers)
        assert response.status_code == 403

    def test_submit_approval_updates_model_use_approval_date_when_all_complete(self, client, db_session, test_user, admin_user, admin_headers, taxonomy_values):
        """Submit approval updates Model.use_approval_date when all complete."""
        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id,
            row_approval_status="approved",
            use_approval_date=None
        )
        db_session.add(model)
        db_session.flush()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        db_session.add(validation_request)
        db_session.flush()

        # Create association record (models relationship is viewonly)
        from app.models.validation import ValidationRequestModelVersion
        assoc = ValidationRequestModelVersion(
            request_id=validation_request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(assoc)
        db_session.flush()

        approval = ValidationApproval(
            request_id=validation_request.request_id,
            approver_role_id=role.role_id,
            approver_id=admin_user.user_id,
            approval_status="Pending",
            approver_role="Admin",
        )
        db_session.add(approval)
        db_session.commit()

        assert model.use_approval_date is None

        payload = {
            "approver_role_id": role.role_id,
            "approval_status": "Approved",
            "approval_evidence": "Test evidence"
        }
        response = client.post(f"/validation-workflow/approvals/{approval.approval_id}/submit-conditional", json=payload, headers=admin_headers)
        assert response.status_code == 200

        db_session.refresh(model)
        assert model.use_approval_date is not None

    def test_void_approval_requirement_with_reason(self, client, db_session, test_user, admin_user, admin_headers, taxonomy_values):
        """Void approval requirement with reason."""
        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id,
            row_approval_status="approved"
        )
        db_session.add(model)
        db_session.flush()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        db_session.add(validation_request)
        db_session.flush()

        # Create association record (models relationship is viewonly)
        from app.models.validation import ValidationRequestModelVersion
        assoc = ValidationRequestModelVersion(
            request_id=validation_request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(assoc)
        db_session.flush()

        approval = ValidationApproval(
            request_id=validation_request.request_id,
            approver_role_id=role.role_id,
            approver_id=admin_user.user_id,
            approval_status="Pending",
            approver_role="Admin",
        )
        db_session.add(approval)
        db_session.commit()

        payload = {"void_reason": "Rule no longer applies due to scope change"}
        response = client.post(f"/validation-workflow/approvals/{approval.approval_id}/void", json=payload, headers=admin_headers)
        assert response.status_code == 200

        db_session.refresh(approval)
        assert approval.voided_by_id == admin_user.user_id
        assert approval.void_reason == "Rule no longer applies due to scope change"
        assert approval.voided_at is not None

    def test_void_approval_creates_audit_log(self, client, db_session, test_user, admin_user, admin_headers, taxonomy_values):
        """Void approval creates audit log with CONDITIONAL_APPROVAL_VOID action."""
        from app.models.audit_log import AuditLog

        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id,
            row_approval_status="approved"
        )
        db_session.add(model)
        db_session.flush()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        db_session.add(validation_request)
        db_session.flush()

        # Create association record (models relationship is viewonly)
        from app.models.validation import ValidationRequestModelVersion
        assoc = ValidationRequestModelVersion(
            request_id=validation_request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(assoc)
        db_session.flush()

        approval = ValidationApproval(
            request_id=validation_request.request_id,
            approver_role_id=role.role_id,
            approver_id=admin_user.user_id,
            approval_status="Pending",
            approver_role="Admin",
        )
        db_session.add(approval)
        db_session.commit()

        payload = {"void_reason": "Test void reason"}
        response = client.post(f"/validation-workflow/approvals/{approval.approval_id}/void", json=payload, headers=admin_headers)
        assert response.status_code == 200

        # Check audit log
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.action == "CONDITIONAL_APPROVAL_VOID",
            AuditLog.entity_type == "ValidationApproval",
            AuditLog.entity_id == approval.approval_id
        ).first()
        assert audit_log is not None
        assert audit_log.user_id == admin_user.user_id

    def test_submit_approval_creates_audit_log(self, client, db_session, test_user, admin_user, admin_headers, taxonomy_values):
        """Submit approval creates audit log with CONDITIONAL_APPROVAL_SUBMIT action."""
        from app.models.audit_log import AuditLog

        role = ApproverRole(role_name="Test Committee")
        db_session.add(role)
        db_session.flush()

        model = Model(
            model_name="Test Model",
            owner_id=test_user.user_id,
            row_approval_status="approved"
        )
        db_session.add(model)
        db_session.flush()

        validation_request = ValidationRequest(
            requestor_id=test_user.user_id,
            validation_type_id=taxonomy_values["initial"].value_id,
            priority_id=taxonomy_values["initial"].value_id,
            target_completion_date=date(2025, 12, 31),
            current_status_id=1
        )
        db_session.add(validation_request)
        db_session.flush()

        # Create association record (models relationship is viewonly)
        from app.models.validation import ValidationRequestModelVersion
        assoc = ValidationRequestModelVersion(
            request_id=validation_request.request_id,
            model_id=model.model_id,
            version_id=None
        )
        db_session.add(assoc)
        db_session.flush()

        approval = ValidationApproval(
            request_id=validation_request.request_id,
            approver_role_id=role.role_id,
            approver_id=admin_user.user_id,
            approval_status="Pending",
            approver_role="Admin",
        )
        db_session.add(approval)
        db_session.commit()

        payload = {
            "approver_role_id": role.role_id,
            "approval_status": "Approved",
            "approval_evidence": "Test evidence"
        }
        response = client.post(f"/validation-workflow/approvals/{approval.approval_id}/submit-conditional", json=payload, headers=admin_headers)
        assert response.status_code == 200

        # Check audit log
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.action == "CONDITIONAL_APPROVAL_SUBMIT",
            AuditLog.entity_type == "ValidationApproval",
            AuditLog.entity_id == approval.approval_id
        ).first()
        assert audit_log is not None
        assert audit_log.user_id == admin_user.user_id
