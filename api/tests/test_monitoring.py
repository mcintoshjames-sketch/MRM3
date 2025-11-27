"""Tests for KPM Library and Monitoring Plans APIs."""
import pytest
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


class TestKpmCategories:
    """Tests for KPM Category CRUD operations."""

    def test_list_categories_empty(self, client, auth_headers, db_session):
        """List categories when none exist."""
        response = client.get("/kpm/categories", headers=auth_headers)
        # May have seeded data, so just check it returns successfully
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_categories_with_data(self, client, admin_headers, db_session):
        """List categories returns categories with their KPMs."""
        response = client.get("/kpm/categories", headers=admin_headers)
        assert response.status_code == 200
        # Check structure if any categories exist
        data = response.json()
        if len(data) > 0:
            assert "category_id" in data[0]
            assert "name" in data[0]
            assert "kpms" in data[0]

    def test_list_categories_active_only_filter(self, client, admin_headers):
        """Filter categories by active status."""
        response = client.get("/kpm/categories?active_only=true", headers=admin_headers)
        assert response.status_code == 200

    def test_create_category_admin(self, client, admin_headers):
        """Admin can create a KPM category."""
        response = client.post("/kpm/categories", headers=admin_headers, json={
            "code": "TEST_CAT",
            "name": "Test Category",
            "description": "Category for testing",
            "sort_order": 99
        })
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "TEST_CAT"
        assert data["name"] == "Test Category"

    def test_create_category_non_admin_fails(self, client, auth_headers):
        """Non-admin cannot create a KPM category."""
        response = client.post("/kpm/categories", headers=auth_headers, json={
            "code": "TEST_FAIL",
            "name": "Should Fail"
        })
        assert response.status_code == 403

    def test_create_category_duplicate_code_fails(self, client, admin_headers):
        """Cannot create category with duplicate code."""
        # First create
        client.post("/kpm/categories", headers=admin_headers, json={
            "code": "DUP_CAT",
            "name": "First Category"
        })
        # Second create with same code
        response = client.post("/kpm/categories", headers=admin_headers, json={
            "code": "DUP_CAT",
            "name": "Duplicate Category"
        })
        assert response.status_code == 400

    def test_get_category_by_id(self, client, admin_headers):
        """Get category with KPMs via list endpoint (filtered)."""
        # Create first
        create_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": "GET_CAT",
            "name": "Get Category"
        })
        cat_id = create_resp.json()["category_id"]

        # Get via list (API doesn't have individual category GET)
        response = client.get("/kpm/categories", headers=admin_headers)
        assert response.status_code == 200
        # Find our category in the list
        found = any(c["code"] == "GET_CAT" for c in response.json())
        assert found

    def test_update_nonexistent_category_not_found(self, client, admin_headers):
        """Update non-existent category returns 404."""
        response = client.patch("/kpm/categories/99999", headers=admin_headers, json={
            "name": "Updated"
        })
        assert response.status_code == 404

    def test_update_category(self, client, admin_headers):
        """Admin can update a KPM category."""
        # Create first
        create_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": "UPD_CAT",
            "name": "Update Category"
        })
        cat_id = create_resp.json()["category_id"]

        # Update
        response = client.patch(f"/kpm/categories/{cat_id}", headers=admin_headers, json={
            "name": "Updated Name",
            "description": "Updated description"
        })
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_delete_category(self, client, admin_headers):
        """Admin can delete a KPM category."""
        # Create first
        create_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": "DEL_CAT",
            "name": "Delete Category"
        })
        cat_id = create_resp.json()["category_id"]

        # Delete
        response = client.delete(f"/kpm/categories/{cat_id}", headers=admin_headers)
        assert response.status_code == 204


class TestKpms:
    """Tests for individual KPM CRUD operations."""

    def test_add_kpm_to_category(self, client, admin_headers):
        """Admin can add a KPM to a category."""
        # Create category first
        cat_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": "KPM_CAT",
            "name": "KPM Category"
        })
        cat_id = cat_resp.json()["category_id"]

        # Add KPM via POST /kpm/kpms with category_id in body
        response = client.post("/kpm/kpms", headers=admin_headers, json={
            "category_id": cat_id,
            "name": "Test Metric",
            "description": "A test metric",
            "calculation": "value / total",
            "interpretation": "Higher is better",
            "sort_order": 0,
            "is_active": True
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Metric"
        assert data["category_id"] == cat_id

    def test_add_kpm_non_admin_fails(self, client, auth_headers, admin_headers):
        """Non-admin cannot add a KPM."""
        # Create category first (as admin)
        cat_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": "KPM_CAT2",
            "name": "KPM Category 2"
        })
        cat_id = cat_resp.json()["category_id"]

        # Try to add KPM as non-admin
        response = client.post("/kpm/kpms", headers=auth_headers, json={
            "category_id": cat_id,
            "name": "Should Fail"
        })
        assert response.status_code == 403

    def test_update_kpm(self, client, admin_headers):
        """Admin can update a KPM."""
        # Create category and KPM
        cat_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": "KPM_UPD",
            "name": "Update KPM Category"
        })
        cat_id = cat_resp.json()["category_id"]

        kpm_resp = client.post("/kpm/kpms", headers=admin_headers, json={
            "category_id": cat_id,
            "name": "Original Name"
        })
        kpm_id = kpm_resp.json()["kpm_id"]

        # Update
        response = client.patch(f"/kpm/kpms/{kpm_id}", headers=admin_headers, json={
            "name": "Updated KPM Name",
            "is_active": False
        })
        assert response.status_code == 200
        assert response.json()["name"] == "Updated KPM Name"
        assert response.json()["is_active"] is False

    def test_delete_kpm(self, client, admin_headers):
        """Admin can delete a KPM."""
        # Create category and KPM
        cat_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": "KPM_DEL",
            "name": "Delete KPM Category"
        })
        cat_id = cat_resp.json()["category_id"]

        kpm_resp = client.post("/kpm/kpms", headers=admin_headers, json={
            "category_id": cat_id,
            "name": "Delete Me"
        })
        kpm_id = kpm_resp.json()["kpm_id"]

        # Delete
        response = client.delete(f"/kpm/kpms/{kpm_id}", headers=admin_headers)
        assert response.status_code == 204


class TestMonitoringTeams:
    """Tests for Monitoring Team CRUD operations."""

    def test_list_teams_empty(self, client, auth_headers):
        """List teams when none exist."""
        response = client.get("/monitoring/teams", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_team_admin(self, client, admin_headers):
        """Admin can create a monitoring team."""
        response = client.post("/monitoring/teams", headers=admin_headers, json={
            "name": "Test Monitoring Team",
            "description": "A test team"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Monitoring Team"
        assert data["is_active"] is True

    def test_create_team_non_admin_fails(self, client, auth_headers):
        """Non-admin cannot create a monitoring team."""
        response = client.post("/monitoring/teams", headers=auth_headers, json={
            "name": "Should Fail"
        })
        assert response.status_code == 403

    def test_create_team_duplicate_name_fails(self, client, admin_headers):
        """Cannot create team with duplicate name."""
        client.post("/monitoring/teams", headers=admin_headers, json={
            "name": "Duplicate Team"
        })
        response = client.post("/monitoring/teams", headers=admin_headers, json={
            "name": "Duplicate Team"
        })
        assert response.status_code == 400

    def test_create_team_with_members(self, client, admin_headers, test_user):
        """Create team with initial members."""
        response = client.post("/monitoring/teams", headers=admin_headers, json={
            "name": "Team With Members",
            "member_ids": [test_user.user_id]
        })
        assert response.status_code == 201
        data = response.json()
        assert len(data["members"]) == 1

    def test_get_team_by_id(self, client, admin_headers):
        """Get a specific team by ID."""
        create_resp = client.post("/monitoring/teams", headers=admin_headers, json={
            "name": "Get Team Test"
        })
        team_id = create_resp.json()["team_id"]

        response = client.get(f"/monitoring/teams/{team_id}", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Get Team Test"

    def test_get_team_not_found(self, client, admin_headers):
        """Get non-existent team returns 404."""
        response = client.get("/monitoring/teams/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_update_team(self, client, admin_headers):
        """Admin can update a monitoring team."""
        create_resp = client.post("/monitoring/teams", headers=admin_headers, json={
            "name": "Update Team Test"
        })
        team_id = create_resp.json()["team_id"]

        response = client.patch(f"/monitoring/teams/{team_id}", headers=admin_headers, json={
            "name": "Updated Team Name",
            "is_active": False
        })
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Team Name"
        assert response.json()["is_active"] is False

    def test_delete_team(self, client, admin_headers):
        """Admin can delete a monitoring team without plans."""
        create_resp = client.post("/monitoring/teams", headers=admin_headers, json={
            "name": "Delete Team Test"
        })
        team_id = create_resp.json()["team_id"]

        response = client.delete(f"/monitoring/teams/{team_id}", headers=admin_headers)
        assert response.status_code == 204

    def test_delete_team_with_plans_fails(self, client, admin_headers):
        """Cannot delete team that has active plans."""
        # Create team
        team_resp = client.post("/monitoring/teams", headers=admin_headers, json={
            "name": "Team With Plan"
        })
        team_id = team_resp.json()["team_id"]

        # Create plan for team
        client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Team",
            "frequency": "Quarterly",
            "monitoring_team_id": team_id
        })

        # Try to delete team
        response = client.delete(f"/monitoring/teams/{team_id}", headers=admin_headers)
        assert response.status_code == 409


class TestMonitoringPlans:
    """Tests for Monitoring Plan CRUD operations."""

    def test_list_plans_empty(self, client, auth_headers):
        """List plans when none exist."""
        response = client.get("/monitoring/plans", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_plan_admin(self, client, admin_headers):
        """Admin can create a monitoring plan."""
        response = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Test Plan",
            "description": "A test monitoring plan",
            "frequency": "Quarterly"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Plan"
        assert data["frequency"] == "Quarterly"
        assert data["next_submission_due_date"] is not None

    def test_create_plan_non_admin_fails(self, client, auth_headers):
        """Non-admin cannot create a monitoring plan."""
        response = client.post("/monitoring/plans", headers=auth_headers, json={
            "name": "Should Fail",
            "frequency": "Quarterly"
        })
        assert response.status_code == 403

    def test_create_plan_with_team(self, client, admin_headers):
        """Create plan with assigned team."""
        # Create team first
        team_resp = client.post("/monitoring/teams", headers=admin_headers, json={
            "name": "Plan Team"
        })
        team_id = team_resp.json()["team_id"]

        response = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan With Team",
            "frequency": "Monthly",
            "monitoring_team_id": team_id
        })
        assert response.status_code == 201
        assert response.json()["team"]["team_id"] == team_id

    def test_create_plan_with_models(self, client, admin_headers, sample_model):
        """Create plan with models in scope."""
        response = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan With Models",
            "frequency": "Quarterly",
            "model_ids": [sample_model.model_id]
        })
        assert response.status_code == 201
        assert len(response.json()["models"]) == 1

    def test_create_plan_date_calculation_quarterly(self, client, admin_headers):
        """Quarterly plan calculates next submission date +3 months."""
        response = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Quarterly Plan",
            "frequency": "Quarterly",
            "reporting_lead_days": 14
        })
        assert response.status_code == 201
        data = response.json()

        # Check that submission date is roughly 3 months from now
        submission_date = date.fromisoformat(data["next_submission_due_date"])
        expected_date = date.today() + relativedelta(months=3)
        assert submission_date == expected_date

    def test_create_plan_date_calculation_monthly(self, client, admin_headers):
        """Monthly plan calculates next submission date +1 month."""
        response = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Monthly Plan",
            "frequency": "Monthly"
        })
        assert response.status_code == 201
        submission_date = date.fromisoformat(response.json()["next_submission_due_date"])
        expected_date = date.today() + relativedelta(months=1)
        assert submission_date == expected_date

    def test_create_plan_report_due_calculation(self, client, admin_headers):
        """Report due date is submission date + lead days."""
        response = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Report Due Test",
            "frequency": "Quarterly",
            "reporting_lead_days": 30
        })
        assert response.status_code == 201
        data = response.json()

        submission_date = date.fromisoformat(data["next_submission_due_date"])
        report_date = date.fromisoformat(data["next_report_due_date"])
        assert report_date == submission_date + timedelta(days=30)

    def test_get_plan_by_id(self, client, admin_headers):
        """Get a specific plan by ID."""
        create_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Get Plan Test",
            "frequency": "Quarterly"
        })
        plan_id = create_resp.json()["plan_id"]

        response = client.get(f"/monitoring/plans/{plan_id}", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Get Plan Test"

    def test_get_plan_not_found(self, client, admin_headers):
        """Get non-existent plan returns 404."""
        response = client.get("/monitoring/plans/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_update_plan(self, client, admin_headers):
        """Admin can update a monitoring plan."""
        create_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Update Plan Test",
            "frequency": "Quarterly"
        })
        plan_id = create_resp.json()["plan_id"]

        response = client.patch(f"/monitoring/plans/{plan_id}", headers=admin_headers, json={
            "name": "Updated Plan Name",
            "frequency": "Monthly",
            "is_active": False
        })
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Plan Name"
        assert response.json()["frequency"] == "Monthly"
        assert response.json()["is_active"] is False

    def test_delete_plan(self, client, admin_headers):
        """Admin can delete a monitoring plan."""
        create_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Delete Plan Test",
            "frequency": "Quarterly"
        })
        plan_id = create_resp.json()["plan_id"]

        response = client.delete(f"/monitoring/plans/{plan_id}", headers=admin_headers)
        assert response.status_code == 204

    def test_advance_plan_cycle(self, client, admin_headers):
        """Advance plan to next monitoring cycle."""
        # Create plan
        create_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Advance Cycle Test",
            "frequency": "Quarterly"
        })
        plan_id = create_resp.json()["plan_id"]
        original_date = date.fromisoformat(create_resp.json()["next_submission_due_date"])

        # Advance cycle
        response = client.post(f"/monitoring/plans/{plan_id}/advance-cycle", headers=admin_headers)
        assert response.status_code == 200

        new_date = date.fromisoformat(response.json()["next_submission_due_date"])
        expected_date = original_date + relativedelta(months=3)
        assert new_date == expected_date


class TestMonitoringPlanMetrics:
    """Tests for Monitoring Plan Metric operations."""

    def test_add_metric_to_plan(self, client, admin_headers):
        """Admin can add a metric to a plan."""
        # Create category and KPM
        cat_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": "METRIC_CAT",
            "name": "Metric Category"
        })
        cat_id = cat_resp.json()["category_id"]

        kpm_resp = client.post("/kpm/kpms", headers=admin_headers, json={
            "category_id": cat_id,
            "name": "Test KPM for Metric"
        })
        kpm_id = kpm_resp.json()["kpm_id"]

        # Create plan
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Metrics",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        # Add metric
        response = client.post(f"/monitoring/plans/{plan_id}/metrics", headers=admin_headers, json={
            "kpm_id": kpm_id,
            "yellow_min": 0.8,
            "yellow_max": 0.9,
            "red_max": 0.7,
            "qualitative_guidance": "Should be above 0.8"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["kpm_id"] == kpm_id
        assert data["yellow_min"] == 0.8
        assert data["yellow_max"] == 0.9

    def test_add_duplicate_metric_fails(self, client, admin_headers):
        """Cannot add same KPM to plan twice."""
        # Create category and KPM
        cat_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": "DUP_METRIC_CAT",
            "name": "Duplicate Metric Category"
        })
        cat_id = cat_resp.json()["category_id"]

        kpm_resp = client.post("/kpm/kpms", headers=admin_headers, json={
            "category_id": cat_id,
            "name": "Duplicate KPM"
        })
        kpm_id = kpm_resp.json()["kpm_id"]

        # Create plan
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Dup Metric",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        # Add metric first time
        client.post(f"/monitoring/plans/{plan_id}/metrics", headers=admin_headers, json={
            "kpm_id": kpm_id
        })

        # Try to add same metric again
        response = client.post(f"/monitoring/plans/{plan_id}/metrics", headers=admin_headers, json={
            "kpm_id": kpm_id
        })
        assert response.status_code == 400

    def test_update_metric(self, client, admin_headers):
        """Admin can update a plan metric."""
        # Create category, KPM, and plan
        cat_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": "UPD_METRIC_CAT",
            "name": "Update Metric Category"
        })
        cat_id = cat_resp.json()["category_id"]

        kpm_resp = client.post("/kpm/kpms", headers=admin_headers, json={
            "category_id": cat_id,
            "name": "Update KPM"
        })
        kpm_id = kpm_resp.json()["kpm_id"]

        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Update Metric",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        # Add metric
        metric_resp = client.post(f"/monitoring/plans/{plan_id}/metrics", headers=admin_headers, json={
            "kpm_id": kpm_id,
            "yellow_min": 0.8
        })
        metric_id = metric_resp.json()["metric_id"]

        # Update metric
        response = client.patch(f"/monitoring/plans/{plan_id}/metrics/{metric_id}", headers=admin_headers, json={
            "yellow_min": 0.75,
            "qualitative_guidance": "Updated guidance"
        })
        assert response.status_code == 200
        assert response.json()["yellow_min"] == 0.75
        assert response.json()["qualitative_guidance"] == "Updated guidance"

    def test_delete_metric(self, client, admin_headers):
        """Admin can delete a plan metric."""
        # Create category, KPM, and plan
        cat_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": "DEL_METRIC_CAT",
            "name": "Delete Metric Category"
        })
        cat_id = cat_resp.json()["category_id"]

        kpm_resp = client.post("/kpm/kpms", headers=admin_headers, json={
            "category_id": cat_id,
            "name": "Delete KPM"
        })
        kpm_id = kpm_resp.json()["kpm_id"]

        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Delete Metric",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        # Add metric
        metric_resp = client.post(f"/monitoring/plans/{plan_id}/metrics", headers=admin_headers, json={
            "kpm_id": kpm_id
        })
        metric_id = metric_resp.json()["metric_id"]

        # Delete metric
        response = client.delete(f"/monitoring/plans/{plan_id}/metrics/{metric_id}", headers=admin_headers)
        assert response.status_code == 204
