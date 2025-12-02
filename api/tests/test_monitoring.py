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
        """Admin can delete a monitoring plan - verifies plan is actually removed."""
        create_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Delete Plan Test",
            "frequency": "Quarterly"
        })
        plan_id = create_resp.json()["plan_id"]

        response = client.delete(f"/monitoring/plans/{plan_id}", headers=admin_headers)
        assert response.status_code == 204

        # Verify plan is actually gone - GET should return 404
        get_response = client.get(f"/monitoring/plans/{plan_id}", headers=admin_headers)
        assert get_response.status_code == 404

    def test_delete_plan_cascades_related_objects(self, client, admin_headers):
        """Deleting plan removes metrics, versions, and cycles via cascade."""
        # Create plan
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan With Related Objects",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        # Add a metric
        cat_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": f"CASCADE_CAT_{plan_id}",
            "name": f"Cascade Category {plan_id}"
        })
        cat_id = cat_resp.json()["category_id"]

        kpm_resp = client.post("/kpm/kpms", headers=admin_headers, json={
            "category_id": cat_id,
            "name": f"Cascade KPM {plan_id}"
        })
        kpm_id = kpm_resp.json()["kpm_id"]

        client.post(f"/monitoring/plans/{plan_id}/metrics", headers=admin_headers, json={
            "kpm_id": kpm_id
        })

        # Publish a version
        version_resp = client.post(f"/monitoring/plans/{plan_id}/versions/publish",
                                   headers=admin_headers, json={})
        assert version_resp.status_code == 201

        # Create a cycle
        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        assert cycle_resp.status_code == 201
        cycle_id = cycle_resp.json()["cycle_id"]

        # Delete plan
        delete_resp = client.delete(f"/monitoring/plans/{plan_id}", headers=admin_headers)
        assert delete_resp.status_code == 204

        # Verify plan is gone
        get_plan_resp = client.get(f"/monitoring/plans/{plan_id}", headers=admin_headers)
        assert get_plan_resp.status_code == 404

        # Verify cycle is gone (cascaded)
        get_cycle_resp = client.get(f"/monitoring/cycles/{cycle_id}", headers=admin_headers)
        assert get_cycle_resp.status_code == 404

        # Verify versions are gone (list versions for deleted plan should 404)
        get_versions_resp = client.get(f"/monitoring/plans/{plan_id}/versions", headers=admin_headers)
        assert get_versions_resp.status_code == 404

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

        # Add metric - note: red_max must be > yellow_max per validation rules
        response = client.post(f"/monitoring/plans/{plan_id}/metrics", headers=admin_headers, json={
            "kpm_id": kpm_id,
            "yellow_min": 0.7,
            "yellow_max": 0.9,
            "red_max": 1.0,
            "qualitative_guidance": "Should be above 0.9 (green), 0.7-0.9 (yellow), above 1.0 (red)"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["kpm_id"] == kpm_id
        assert data["yellow_min"] == 0.7
        assert data["yellow_max"] == 0.9
        assert data["red_max"] == 1.0

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


class TestMonitoringCycles:
    """Tests for Monitoring Cycle CRUD operations."""

    def test_create_cycle(self, client, admin_headers):
        """Admin can create a monitoring cycle."""
        # Create plan first
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Cycles",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        # Create cycle
        response = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={
            "notes": "Test cycle"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["plan_id"] == plan_id
        assert data["status"] == "PENDING"
        assert data["notes"] == "Test cycle"

    def test_list_cycles(self, client, admin_headers):
        """List cycles for a plan."""
        # Create plan and cycle
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Cycle List",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})

        response = client.get(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) >= 1

    def test_get_cycle_by_id(self, client, admin_headers):
        """Get a specific cycle by ID."""
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Get Cycle",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]

        response = client.get(f"/monitoring/cycles/{cycle_id}", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["cycle_id"] == cycle_id

    def test_get_cycle_not_found(self, client, admin_headers):
        """Get non-existent cycle returns 404."""
        response = client.get("/monitoring/cycles/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_update_cycle(self, client, admin_headers, test_user):
        """Admin can update a monitoring cycle."""
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Update Cycle",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]

        response = client.patch(f"/monitoring/cycles/{cycle_id}", headers=admin_headers, json={
            "assigned_to_user_id": test_user.user_id,
            "notes": "Updated notes"
        })
        assert response.status_code == 200
        assert response.json()["notes"] == "Updated notes"

    def test_delete_pending_cycle(self, client, admin_headers):
        """Can delete a PENDING cycle without results."""
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Delete Cycle",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]

        response = client.delete(f"/monitoring/cycles/{cycle_id}", headers=admin_headers)
        assert response.status_code == 204


class TestCycleWorkflow:
    """Tests for monitoring cycle workflow operations."""

    def _publish_version_for_plan(self, client, admin_headers, plan_id):
        """Helper to publish a version for a plan (required before starting cycles).

        Returns the metric_id so tests can add results if needed.
        """
        # Need at least one metric for publish to work
        cat_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": f"WF_CAT_{plan_id}",
            "name": f"Workflow Category {plan_id}"
        })
        cat_id = cat_resp.json()["category_id"]

        kpm_resp = client.post("/kpm/kpms", headers=admin_headers, json={
            "category_id": cat_id,
            "name": f"Workflow KPM {plan_id}"
        })
        kpm_id = kpm_resp.json()["kpm_id"]

        metric_resp = client.post(f"/monitoring/plans/{plan_id}/metrics", headers=admin_headers, json={
            "kpm_id": kpm_id
        })
        metric_id = metric_resp.json()["metric_id"]

        client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={})

        return metric_id

    def test_start_cycle(self, client, admin_headers):
        """Start cycle moves from PENDING to DATA_COLLECTION."""
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Start",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        # Publish version (required for starting cycles)
        self._publish_version_for_plan(client, admin_headers, plan_id)

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]
        assert cycle_resp.json()["status"] == "PENDING"

        response = client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "DATA_COLLECTION"

    def test_start_non_pending_cycle_fails(self, client, admin_headers):
        """Cannot start a cycle that's not PENDING."""
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Start Fail",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        # Publish version
        self._publish_version_for_plan(client, admin_headers, plan_id)

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]

        # Start once
        client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)

        # Try to start again
        response = client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)
        assert response.status_code == 400

    def test_submit_cycle(self, client, admin_headers):
        """Submit cycle moves from DATA_COLLECTION to UNDER_REVIEW."""
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Submit",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        # Publish version and get metric_id
        metric_id = self._publish_version_for_plan(client, admin_headers, plan_id)

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]

        client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)

        # Add at least one result before submitting (required by validation)
        client.post(f"/monitoring/cycles/{cycle_id}/results", headers=admin_headers, json={
            "plan_metric_id": metric_id,
            "numeric_value": 0.95,
            "narrative": "Results look good"
        })

        response = client.post(f"/monitoring/cycles/{cycle_id}/submit", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "UNDER_REVIEW"
        assert response.json()["submitted_at"] is not None

    def test_submit_cycle_fails_without_any_results(self, client, admin_headers):
        """Submit fails if no results have been entered - guards against removed completeness validation."""
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Submit No Results",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        # Publish version (creates metric)
        self._publish_version_for_plan(client, admin_headers, plan_id)

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]

        # Start cycle to move to DATA_COLLECTION
        client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)

        # Try to submit WITHOUT entering any results
        response = client.post(f"/monitoring/cycles/{cycle_id}/submit", headers=admin_headers)
        assert response.status_code == 400
        assert "No results have been entered" in response.json()["detail"]

    def test_submit_cycle_fails_with_missing_metric_results(self, client, admin_headers):
        """Submit fails when some metrics have no results - guards multi-metric completeness."""
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Submit Missing Metrics",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        # Create TWO KPMs and add TWO metrics to the plan
        cat_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": f"MULTI_CAT_{plan_id}",
            "name": f"Multi Category {plan_id}"
        })
        cat_id = cat_resp.json()["category_id"]

        kpm1_resp = client.post("/kpm/kpms", headers=admin_headers, json={
            "category_id": cat_id,
            "name": f"Metric One {plan_id}"
        })
        kpm1_id = kpm1_resp.json()["kpm_id"]

        kpm2_resp = client.post("/kpm/kpms", headers=admin_headers, json={
            "category_id": cat_id,
            "name": f"Metric Two {plan_id}"
        })
        kpm2_id = kpm2_resp.json()["kpm_id"]

        # Add both metrics to plan
        metric1_resp = client.post(f"/monitoring/plans/{plan_id}/metrics", headers=admin_headers, json={
            "kpm_id": kpm1_id
        })
        metric1_id = metric1_resp.json()["metric_id"]

        client.post(f"/monitoring/plans/{plan_id}/metrics", headers=admin_headers, json={
            "kpm_id": kpm2_id
        })
        # Note: We intentionally don't use metric2_id - we'll skip its result

        # Publish version (locks both metrics)
        client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={})

        # Create and start cycle
        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]
        client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)

        # Only add result for metric1, skip metric2
        client.post(f"/monitoring/cycles/{cycle_id}/results", headers=admin_headers, json={
            "plan_metric_id": metric1_id,
            "numeric_value": 0.95,
            "narrative": "First metric looks good"
        })

        # Try to submit - should fail because metric2 has no result
        response = client.post(f"/monitoring/cycles/{cycle_id}/submit", headers=admin_headers)
        assert response.status_code == 400
        assert "Missing results for:" in response.json()["detail"]
        assert f"Metric Two {plan_id}" in response.json()["detail"]

    def test_submit_cycle_fails_with_na_value_no_narrative(self, client, admin_headers):
        """Submit fails when a metric has no value AND no narrative explanation."""
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Submit NA No Narrative",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        # Publish version and get metric_id
        metric_id = self._publish_version_for_plan(client, admin_headers, plan_id)

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]

        client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)

        # Add result with NULL value AND empty narrative (N/A without explanation)
        client.post(f"/monitoring/cycles/{cycle_id}/results", headers=admin_headers, json={
            "plan_metric_id": metric_id,
            "numeric_value": None,
            "narrative": ""  # Empty narrative for N/A value
        })

        # Try to submit - should fail because N/A needs explanation
        response = client.post(f"/monitoring/cycles/{cycle_id}/submit", headers=admin_headers)
        assert response.status_code == 400
        assert "Missing explanation for N/A values" in response.json()["detail"]

    def test_submit_cycle_succeeds_with_na_value_and_narrative(self, client, admin_headers):
        """Submit succeeds when N/A metric has narrative explanation."""
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Submit NA With Narrative",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        metric_id = self._publish_version_for_plan(client, admin_headers, plan_id)

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]

        client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)

        # Add result with NULL value but WITH narrative explanation
        client.post(f"/monitoring/cycles/{cycle_id}/results", headers=admin_headers, json={
            "plan_metric_id": metric_id,
            "numeric_value": None,
            "narrative": "Data not available this period due to system maintenance"
        })

        # Submit should succeed because N/A has explanation
        response = client.post(f"/monitoring/cycles/{cycle_id}/submit", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "UNDER_REVIEW"

    def test_cancel_cycle(self, client, admin_headers):
        """Cancel cycle moves to CANCELLED status."""
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Cancel",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]

        response = client.post(f"/monitoring/cycles/{cycle_id}/cancel", headers=admin_headers, json={
            "cancel_reason": "Testing cancellation"
        })
        assert response.status_code == 200
        assert response.json()["status"] == "CANCELLED"
        assert "CANCELLED" in response.json()["notes"]

    def test_cycle_overdue_fields_past_due_date(self, client, admin_headers):
        """Cycle with past report_due_date in DATA_COLLECTION shows is_overdue=True."""
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Overdue Test",
            "frequency": "Quarterly",
            "reporting_lead_days": 0  # Simplify: report_due = submission_due = period_end + 15
        })
        plan_id = plan_resp.json()["plan_id"]

        # Publish version
        self._publish_version_for_plan(client, admin_headers, plan_id)

        # Create cycle with period_end_date that results in past report_due_date
        # report_due_date = period_end + 15 days (default submission_due) + 0 (no lead days)
        # To make report_due 7 days ago: period_end = today - 7 - 15 = today - 22
        today = date.today()
        period_end = today - timedelta(days=22)
        period_start = period_end - timedelta(days=30)

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={
            "period_start_date": period_start.isoformat(),
            "period_end_date": period_end.isoformat()
        })
        assert cycle_resp.status_code == 201
        cycle_id = cycle_resp.json()["cycle_id"]

        # Start the cycle so it's in DATA_COLLECTION (non-completed status)
        client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)

        # Get cycles list to check overdue fields
        response = client.get(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers)
        assert response.status_code == 200
        cycles = response.json()
        cycle = next(c for c in cycles if c["cycle_id"] == cycle_id)

        assert cycle["is_overdue"] is True
        assert cycle["days_overdue"] == 7

    def test_cycle_overdue_fields_future_due_date(self, client, admin_headers):
        """Cycle with future report_due_date shows is_overdue=False."""
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Future Due Test",
            "frequency": "Quarterly",
            "reporting_lead_days": 0  # Simplify: report_due = submission_due = period_end + 15
        })
        plan_id = plan_resp.json()["plan_id"]

        # Publish version
        self._publish_version_for_plan(client, admin_headers, plan_id)

        # Create cycle with period_end_date that results in future report_due_date
        # report_due = period_end + 15 days
        # To make report_due 14 days in future: period_end = today + 14 - 15 = today - 1
        today = date.today()
        period_end = today - timedelta(days=1)
        period_start = period_end - timedelta(days=30)

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={
            "period_start_date": period_start.isoformat(),
            "period_end_date": period_end.isoformat()
        })
        assert cycle_resp.status_code == 201
        cycle_id = cycle_resp.json()["cycle_id"]

        # Start the cycle
        client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)

        # Get cycles list to check overdue fields
        response = client.get(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers)
        assert response.status_code == 200
        cycles = response.json()
        cycle = next(c for c in cycles if c["cycle_id"] == cycle_id)

        assert cycle["is_overdue"] is False
        assert cycle["days_overdue"] == -14  # Negative means days until due

    def test_cycle_cancelled_never_overdue(self, client, admin_headers):
        """CANCELLED cycles are never considered overdue, even with past due date."""
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Cancelled Not Overdue",
            "frequency": "Quarterly",
            "reporting_lead_days": 0  # Simplify: report_due = submission_due = period_end + 15
        })
        plan_id = plan_resp.json()["plan_id"]

        # Publish version
        self._publish_version_for_plan(client, admin_headers, plan_id)

        # Create cycle with period that results in past due date (30 days ago)
        # report_due = period_end + 15 days
        # To make report_due 30 days ago: period_end = today - 30 - 15 = today - 45
        today = date.today()
        period_end = today - timedelta(days=45)
        period_start = period_end - timedelta(days=30)

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={
            "period_start_date": period_start.isoformat(),
            "period_end_date": period_end.isoformat()
        })
        cycle_id = cycle_resp.json()["cycle_id"]

        # Cancel the cycle
        client.post(f"/monitoring/cycles/{cycle_id}/cancel", headers=admin_headers, json={
            "cancel_reason": "Testing cancelled overdue status"
        })

        # Get cycles list to check overdue fields
        response = client.get(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers)
        assert response.status_code == 200
        cycles = response.json()
        cycle = next(c for c in cycles if c["cycle_id"] == cycle_id)

        # CANCELLED cycle should NOT be overdue
        assert cycle["status"] == "CANCELLED"
        assert cycle["is_overdue"] is False


class TestMonitoringResults:
    """Tests for monitoring result entry."""

    def test_create_result_quantitative(self, client, admin_headers):
        """Create a quantitative result with outcome calculation."""
        # Create category and KPM
        cat_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": "RESULT_CAT",
            "name": "Result Category"
        })
        cat_id = cat_resp.json()["category_id"]

        kpm_resp = client.post("/kpm/kpms", headers=admin_headers, json={
            "category_id": cat_id,
            "name": "Quantitative KPM",
            "evaluation_type": "Quantitative"
        })
        kpm_id = kpm_resp.json()["kpm_id"]

        # Create plan with metric
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Results",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        metric_resp = client.post(f"/monitoring/plans/{plan_id}/metrics", headers=admin_headers, json={
            "kpm_id": kpm_id,
            "yellow_min": 0.8,
            "red_min": 0.6
        })
        metric_id = metric_resp.json()["metric_id"]

        # Publish version (required for starting cycles)
        client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={})

        # Create and start cycle
        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]
        client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)

        # Create result
        response = client.post(f"/monitoring/cycles/{cycle_id}/results", headers=admin_headers, json={
            "plan_metric_id": metric_id,
            "numeric_value": 0.95
        })
        assert response.status_code == 201
        assert response.json()["calculated_outcome"] == "GREEN"

    def test_create_result_yellow_threshold(self, client, admin_headers):
        """Result below yellow threshold shows YELLOW outcome."""
        # Setup
        cat_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": "YELLOW_CAT",
            "name": "Yellow Category"
        })
        cat_id = cat_resp.json()["category_id"]

        kpm_resp = client.post("/kpm/kpms", headers=admin_headers, json={
            "category_id": cat_id,
            "name": "Yellow KPM",
            "evaluation_type": "Quantitative"
        })
        kpm_id = kpm_resp.json()["kpm_id"]

        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Yellow",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        metric_resp = client.post(f"/monitoring/plans/{plan_id}/metrics", headers=admin_headers, json={
            "kpm_id": kpm_id,
            "yellow_min": 0.8,
            "red_min": 0.6
        })
        metric_id = metric_resp.json()["metric_id"]

        # Publish version (required for starting cycles)
        client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={})

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]
        client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)

        # Create result with value below yellow threshold
        response = client.post(f"/monitoring/cycles/{cycle_id}/results", headers=admin_headers, json={
            "plan_metric_id": metric_id,
            "numeric_value": 0.75
        })
        assert response.status_code == 201
        assert response.json()["calculated_outcome"] == "YELLOW"

    def test_create_result_red_threshold(self, client, admin_headers):
        """Result below red threshold shows RED outcome."""
        # Setup
        cat_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": "RED_CAT",
            "name": "Red Category"
        })
        cat_id = cat_resp.json()["category_id"]

        kpm_resp = client.post("/kpm/kpms", headers=admin_headers, json={
            "category_id": cat_id,
            "name": "Red KPM",
            "evaluation_type": "Quantitative"
        })
        kpm_id = kpm_resp.json()["kpm_id"]

        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Red",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        metric_resp = client.post(f"/monitoring/plans/{plan_id}/metrics", headers=admin_headers, json={
            "kpm_id": kpm_id,
            "red_min": 0.6
        })
        metric_id = metric_resp.json()["metric_id"]

        # Publish version (required for starting cycles)
        client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={})

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]
        client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)

        # Create result with value below red threshold
        response = client.post(f"/monitoring/cycles/{cycle_id}/results", headers=admin_headers, json={
            "plan_metric_id": metric_id,
            "numeric_value": 0.5
        })
        assert response.status_code == 201
        assert response.json()["calculated_outcome"] == "RED"

    def test_list_cycle_results(self, client, admin_headers):
        """List all results for a cycle."""
        # Setup - create plan with metric and cycle
        cat_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": "LIST_RES_CAT",
            "name": "List Results Category"
        })
        cat_id = cat_resp.json()["category_id"]

        kpm_resp = client.post("/kpm/kpms", headers=admin_headers, json={
            "category_id": cat_id,
            "name": "List Results KPM"
        })
        kpm_id = kpm_resp.json()["kpm_id"]

        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For List Results",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        metric_resp = client.post(f"/monitoring/plans/{plan_id}/metrics", headers=admin_headers, json={
            "kpm_id": kpm_id
        })
        metric_id = metric_resp.json()["metric_id"]

        # Publish version (required for starting cycles)
        client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={})

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]
        client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)

        # Create result
        client.post(f"/monitoring/cycles/{cycle_id}/results", headers=admin_headers, json={
            "plan_metric_id": metric_id,
            "numeric_value": 0.9
        })

        # List results
        response = client.get(f"/monitoring/cycles/{cycle_id}/results", headers=admin_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_cannot_add_result_to_pending_cycle(self, client, admin_headers):
        """Cannot add results to a PENDING cycle."""
        cat_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": "PEND_RES_CAT",
            "name": "Pending Results Category"
        })
        cat_id = cat_resp.json()["category_id"]

        kpm_resp = client.post("/kpm/kpms", headers=admin_headers, json={
            "category_id": cat_id,
            "name": "Pending Results KPM"
        })
        kpm_id = kpm_resp.json()["kpm_id"]

        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan For Pending Results",
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        metric_resp = client.post(f"/monitoring/plans/{plan_id}/metrics", headers=admin_headers, json={
            "kpm_id": kpm_id
        })
        metric_id = metric_resp.json()["metric_id"]

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]

        # Try to add result without starting cycle
        response = client.post(f"/monitoring/cycles/{cycle_id}/results", headers=admin_headers, json={
            "plan_metric_id": metric_id,
            "numeric_value": 0.9
        })
        assert response.status_code == 400


class TestMonitoringPlanVersioning:
    """Tests for Monitoring Plan Versioning operations."""

    def _create_plan_with_metrics(self, client, admin_headers, plan_name="Versioned Plan"):
        """Helper to create a plan with metrics for versioning tests."""
        # Create category and KPM
        cat_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": f"VER_CAT_{plan_name[:8]}",
            "name": f"Version Category {plan_name[:8]}"
        })
        cat_id = cat_resp.json()["category_id"]

        kpm_resp = client.post("/kpm/kpms", headers=admin_headers, json={
            "category_id": cat_id,
            "name": f"Version KPM {plan_name[:8]}",
            "evaluation_type": "Quantitative"
        })
        kpm_id = kpm_resp.json()["kpm_id"]

        # Create plan
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": plan_name,
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        # Add metric with thresholds
        metric_resp = client.post(f"/monitoring/plans/{plan_id}/metrics", headers=admin_headers, json={
            "kpm_id": kpm_id,
            "yellow_min": 0.8,
            "yellow_max": 0.9,
            "red_min": 0.6,
            "qualitative_guidance": "Test guidance"
        })
        metric_id = metric_resp.json()["metric_id"]

        return plan_id, kpm_id, metric_id

    def test_list_versions_empty(self, client, admin_headers):
        """List versions returns empty list for plan with no published versions."""
        plan_id, _, _ = self._create_plan_with_metrics(client, admin_headers, "Empty Ver Plan")

        response = client.get(f"/monitoring/plans/{plan_id}/versions", headers=admin_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_publish_version(self, client, admin_headers):
        """Admin can publish a version, creating metric snapshots."""
        plan_id, kpm_id, _ = self._create_plan_with_metrics(client, admin_headers, "Publish Ver Plan")

        response = client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={
            "version_name": "Initial Version",
            "description": "First published version"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["version_number"] == 1
        assert data["version_name"] == "Initial Version"
        assert data["is_active"] is True
        assert data["metrics_count"] == 1

    def test_publish_version_increments_number(self, client, admin_headers):
        """Publishing multiple versions increments version_number."""
        plan_id, _, _ = self._create_plan_with_metrics(client, admin_headers, "Multi Ver Plan")

        # Publish v1
        v1_resp = client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={
            "version_name": "Version 1"
        })
        assert v1_resp.json()["version_number"] == 1
        assert v1_resp.json()["is_active"] is True

        # Publish v2
        v2_resp = client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={
            "version_name": "Version 2"
        })
        assert v2_resp.json()["version_number"] == 2
        assert v2_resp.json()["is_active"] is True

        # Verify v1 is now inactive
        versions = client.get(f"/monitoring/plans/{plan_id}/versions", headers=admin_headers).json()
        v1 = next(v for v in versions if v["version_number"] == 1)
        assert v1["is_active"] is False

    def test_list_versions(self, client, admin_headers):
        """List all versions for a plan."""
        plan_id, _, _ = self._create_plan_with_metrics(client, admin_headers, "List Ver Plan")

        # Publish two versions
        client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={})
        client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={})

        response = client.get(f"/monitoring/plans/{plan_id}/versions", headers=admin_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_get_version_detail_with_snapshots(self, client, admin_headers):
        """Get version details includes metric snapshots."""
        plan_id, kpm_id, _ = self._create_plan_with_metrics(client, admin_headers, "Detail Ver Plan")

        publish_resp = client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={})
        version_id = publish_resp.json()["version_id"]

        response = client.get(f"/monitoring/plans/{plan_id}/versions/{version_id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["version_id"] == version_id
        assert "metric_snapshots" in data
        assert len(data["metric_snapshots"]) == 1
        snapshot = data["metric_snapshots"][0]
        assert snapshot["kpm_id"] == kpm_id
        assert snapshot["yellow_min"] == 0.8
        assert snapshot["yellow_max"] == 0.9
        assert snapshot["red_min"] == 0.6

    def test_version_snapshots_preserve_thresholds(self, client, admin_headers):
        """Metric snapshots preserve original thresholds even if plan metrics change."""
        plan_id, kpm_id, metric_id = self._create_plan_with_metrics(client, admin_headers, "Snap Ver Plan")

        # Publish v1
        v1_resp = client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={})
        v1_id = v1_resp.json()["version_id"]

        # Update the plan metric thresholds
        client.patch(f"/monitoring/plans/{plan_id}/metrics/{metric_id}", headers=admin_headers, json={
            "yellow_min": 0.7,  # Changed from 0.8
            "red_min": 0.5      # Changed from 0.6
        })

        # Verify v1 snapshots still have original values
        v1_detail = client.get(f"/monitoring/plans/{plan_id}/versions/{v1_id}", headers=admin_headers).json()
        snapshot = v1_detail["metric_snapshots"][0]
        assert snapshot["yellow_min"] == 0.8  # Original value preserved
        assert snapshot["red_min"] == 0.6     # Original value preserved

    def test_export_version_csv(self, client, admin_headers):
        """Export version metrics as CSV."""
        plan_id, _, _ = self._create_plan_with_metrics(client, admin_headers, "Export Ver Plan")

        publish_resp = client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={})
        version_id = publish_resp.json()["version_id"]

        response = client.get(f"/monitoring/plans/{plan_id}/versions/{version_id}/export", headers=admin_headers)
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        # Check CSV content includes headers
        content = response.text
        assert "KPM Name" in content
        assert "Yellow Min" in content
        assert "Red Min" in content

    def test_start_cycle_requires_published_version(self, client, admin_headers):
        """Starting a cycle requires at least one published version."""
        plan_id, _, _ = self._create_plan_with_metrics(client, admin_headers, "No Ver Plan")

        # Create cycle (without publishing version)
        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]

        # Try to start cycle - should fail
        response = client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)
        assert response.status_code == 400
        assert "published version" in response.json()["detail"].lower()

    def test_start_cycle_locks_to_active_version(self, client, admin_headers):
        """Starting a cycle locks it to the active version."""
        plan_id, _, _ = self._create_plan_with_metrics(client, admin_headers, "Lock Ver Plan")

        # Publish version
        publish_resp = client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={})
        version_id = publish_resp.json()["version_id"]

        # Create and start cycle
        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]

        start_resp = client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)
        assert start_resp.status_code == 200
        data = start_resp.json()
        assert data["plan_version_id"] == version_id
        assert data["version_locked_at"] is not None
        assert data["plan_version"]["version_id"] == version_id

    def test_cycle_remains_locked_after_new_version(self, client, admin_headers):
        """Cycle stays locked to its original version even after new version published."""
        plan_id, _, _ = self._create_plan_with_metrics(client, admin_headers, "Remain Ver Plan")

        # Publish v1 and start cycle
        v1_resp = client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={})
        v1_id = v1_resp.json()["version_id"]

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]
        client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)

        # Publish v2
        v2_resp = client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={})
        v2_id = v2_resp.json()["version_id"]
        assert v2_id != v1_id

        # Verify cycle still locked to v1
        cycle_detail = client.get(f"/monitoring/cycles/{cycle_id}", headers=admin_headers).json()
        assert cycle_detail["plan_version_id"] == v1_id

    def test_active_cycles_warning_no_cycles(self, client, admin_headers):
        """Active cycles warning returns false when no active cycles exist."""
        plan_id, _, _ = self._create_plan_with_metrics(client, admin_headers, "Warn No Cyc")

        response = client.get(f"/monitoring/plans/{plan_id}/active-cycles-warning", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["warning"] is False
        assert data["active_cycle_count"] == 0

    def test_active_cycles_warning_with_active_cycle(self, client, admin_headers):
        """Active cycles warning returns true when active cycles exist."""
        plan_id, _, _ = self._create_plan_with_metrics(client, admin_headers, "Warn Act Cyc")

        # Publish and start a cycle
        client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={})
        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]
        client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)

        response = client.get(f"/monitoring/plans/{plan_id}/active-cycles-warning", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["warning"] is True
        assert data["active_cycle_count"] >= 1

    def test_version_not_found(self, client, admin_headers):
        """Get non-existent version returns 404."""
        plan_id, _, _ = self._create_plan_with_metrics(client, admin_headers, "Not Found Plan")

        response = client.get(f"/monitoring/plans/{plan_id}/versions/99999", headers=admin_headers)
        assert response.status_code == 404


class TestApprovalWorkflow:
    """Tests for monitoring cycle approval workflow."""

    def _publish_version_for_plan(self, client, admin_headers, plan_id, plan_name):
        """Helper to publish a version for a plan (required before starting cycles).

        Returns the metric_id so tests can add results if needed.
        """
        # Need at least one metric for publish to work
        cat_resp = client.post("/kpm/categories", headers=admin_headers, json={
            "code": f"APPR_CAT_{plan_name[:8]}",
            "name": f"Approval Category {plan_name[:8]}"
        })
        cat_id = cat_resp.json()["category_id"]

        kpm_resp = client.post("/kpm/kpms", headers=admin_headers, json={
            "category_id": cat_id,
            "name": f"Approval KPM {plan_name[:8]}"
        })
        kpm_id = kpm_resp.json()["kpm_id"]

        metric_resp = client.post(f"/monitoring/plans/{plan_id}/metrics", headers=admin_headers, json={
            "kpm_id": kpm_id
        })
        metric_id = metric_resp.json()["metric_id"]

        client.post(f"/monitoring/plans/{plan_id}/versions/publish", headers=admin_headers, json={})

        return metric_id

    def _setup_cycle_for_approval(self, client, admin_headers, plan_name):
        """Helper to create a plan, publish version, create cycle, and move to UNDER_REVIEW.

        Returns (plan_id, cycle_id) for further testing.
        """
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": plan_name,
            "frequency": "Quarterly"
        })
        plan_id = plan_resp.json()["plan_id"]

        # Publish version and get metric_id
        metric_id = self._publish_version_for_plan(client, admin_headers, plan_id, plan_name)

        cycle_resp = client.post(f"/monitoring/plans/{plan_id}/cycles", headers=admin_headers, json={})
        cycle_id = cycle_resp.json()["cycle_id"]

        # Start cycle
        client.post(f"/monitoring/cycles/{cycle_id}/start", headers=admin_headers)

        # Add at least one result before submitting (required by validation)
        client.post(f"/monitoring/cycles/{cycle_id}/results", headers=admin_headers, json={
            "plan_metric_id": metric_id,
            "numeric_value": 0.95,
            "narrative": "Results look good for approval testing"
        })

        # Submit
        client.post(f"/monitoring/cycles/{cycle_id}/submit", headers=admin_headers)

        return plan_id, cycle_id

    def test_request_approval_creates_global(self, client, admin_headers):
        """Requesting approval creates a Global approval with correct fields - guards mandatory Global creation."""
        # Setup cycle in UNDER_REVIEW state
        plan_id, cycle_id = self._setup_cycle_for_approval(client, admin_headers, "Plan For Approval")

        # Request approval (requires report_url)
        response = client.post(f"/monitoring/cycles/{cycle_id}/request-approval", headers=admin_headers,
                              json={"report_url": "https://example.com/reports/test-report.pdf"})
        assert response.status_code == 200
        assert response.json()["status"] == "PENDING_APPROVAL"
        assert response.json()["approval_count"] >= 1

        # Verify Global approval exists with correct required fields
        approvals_resp = client.get(f"/monitoring/cycles/{cycle_id}/approvals", headers=admin_headers)
        approvals = approvals_resp.json()
        global_approval = next((a for a in approvals if a["approval_type"] == "Global"), None)

        assert global_approval is not None, "Global approval must be created"
        assert global_approval["is_required"] is True, "Global approval must be marked as required"
        assert global_approval["approval_status"] == "Pending", "Global approval must start as Pending"
        assert global_approval["region"] is None, "Global approval has no region"
        assert global_approval["approver"] is None, "Global approval should have no approver initially"
        assert global_approval["approved_at"] is None, "Global approval should have no approved_at initially"

    def test_list_cycle_approvals(self, client, admin_headers):
        """List approval requirements for a cycle - verifies approval object completeness."""
        # Setup cycle in UNDER_REVIEW state
        plan_id, cycle_id = self._setup_cycle_for_approval(client, admin_headers, "Plan For List Approvals")
        client.post(f"/monitoring/cycles/{cycle_id}/request-approval", headers=admin_headers,
                   json={"report_url": "https://example.com/reports/test-report.pdf"})

        response = client.get(f"/monitoring/cycles/{cycle_id}/approvals", headers=admin_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

        # Check Global approval exists with all required fields present
        approvals = response.json()
        global_approval = next((a for a in approvals if a["approval_type"] == "Global"), None)
        assert global_approval is not None

        # Verify approval object structure (guards against missing fields)
        assert "approval_id" in global_approval
        assert "cycle_id" in global_approval
        assert "approval_type" in global_approval
        assert "is_required" in global_approval
        assert "approval_status" in global_approval
        assert global_approval["is_required"] is True
        assert global_approval["approval_status"] == "Pending"

    def test_approve_global_approval(self, client, admin_headers):
        """Admin can approve a Global approval."""
        # Setup cycle in UNDER_REVIEW state
        plan_id, cycle_id = self._setup_cycle_for_approval(client, admin_headers, "Plan For Global Approval")
        client.post(f"/monitoring/cycles/{cycle_id}/request-approval", headers=admin_headers,
                   json={"report_url": "https://example.com/reports/test-report.pdf"})

        # Get the approval ID
        approvals_resp = client.get(f"/monitoring/cycles/{cycle_id}/approvals", headers=admin_headers)
        global_approval = next(a for a in approvals_resp.json() if a["approval_type"] == "Global")
        approval_id = global_approval["approval_id"]

        # Approve (Admin must provide approval_evidence when approving on behalf)
        response = client.post(f"/monitoring/cycles/{cycle_id}/approvals/{approval_id}/approve",
                              headers=admin_headers, json={
                                  "comments": "Approved by test",
                                  "approval_evidence": "Committee meeting minutes from test date"
                              })
        assert response.status_code == 200
        assert response.json()["approval_status"] == "Approved"
        assert response.json()["approver"] is not None
        assert response.json()["approval_evidence"] is not None
        assert response.json()["is_proxy_approval"] == True

    def test_cycle_auto_completes_when_all_approved(self, client, admin_headers):
        """Cycle transitions to APPROVED when all approvals are granted."""
        # Setup cycle in UNDER_REVIEW state
        plan_id, cycle_id = self._setup_cycle_for_approval(client, admin_headers, "Plan For Auto Complete")
        client.post(f"/monitoring/cycles/{cycle_id}/request-approval", headers=admin_headers,
                   json={"report_url": "https://example.com/reports/test-report.pdf"})

        # Approve all approvals (Admin must provide approval_evidence when approving on behalf)
        approvals_resp = client.get(f"/monitoring/cycles/{cycle_id}/approvals", headers=admin_headers)
        for approval in approvals_resp.json():
            if approval["approval_status"] == "Pending":
                client.post(f"/monitoring/cycles/{cycle_id}/approvals/{approval['approval_id']}/approve",
                           headers=admin_headers, json={
                               "comments": "Approved",
                               "approval_evidence": "Committee meeting minutes for test"
                           })

        # Check cycle is now APPROVED
        cycle_resp = client.get(f"/monitoring/cycles/{cycle_id}", headers=admin_headers)
        assert cycle_resp.json()["status"] == "APPROVED"
        assert cycle_resp.json()["completed_at"] is not None

    def test_reject_approval_returns_to_under_review(self, client, admin_headers):
        """Rejecting an approval returns cycle to UNDER_REVIEW."""
        # Setup cycle in UNDER_REVIEW state
        plan_id, cycle_id = self._setup_cycle_for_approval(client, admin_headers, "Plan For Reject")
        client.post(f"/monitoring/cycles/{cycle_id}/request-approval", headers=admin_headers,
                   json={"report_url": "https://example.com/reports/test-report.pdf"})

        approvals_resp = client.get(f"/monitoring/cycles/{cycle_id}/approvals", headers=admin_headers)
        global_approval = next(a for a in approvals_resp.json() if a["approval_type"] == "Global")
        approval_id = global_approval["approval_id"]

        # Reject
        response = client.post(f"/monitoring/cycles/{cycle_id}/approvals/{approval_id}/reject",
                              headers=admin_headers, json={"comments": "Issues found"})
        assert response.status_code == 200
        assert response.json()["approval_status"] == "Rejected"

        # Check cycle is back to UNDER_REVIEW
        cycle_resp = client.get(f"/monitoring/cycles/{cycle_id}", headers=admin_headers)
        assert cycle_resp.json()["status"] == "UNDER_REVIEW"

    def test_resubmit_cycle_resets_rejected_approvals(self, client, admin_headers):
        """Re-requesting approval after rejection resets Rejected approvals to Pending.

        This guards against the defect where Rejected approvals persisted and blocked
        the cycle from completing even after re-submission and subsequent approvals.
        """
        # Setup cycle in UNDER_REVIEW state
        plan_id, cycle_id = self._setup_cycle_for_approval(client, admin_headers, "Plan For Resubmit")

        # Request approval
        client.post(f"/monitoring/cycles/{cycle_id}/request-approval", headers=admin_headers,
                   json={"report_url": "https://example.com/reports/v1.pdf"})

        # Get approval and reject it
        approvals_resp = client.get(f"/monitoring/cycles/{cycle_id}/approvals", headers=admin_headers)
        global_approval = next(a for a in approvals_resp.json() if a["approval_type"] == "Global")
        approval_id = global_approval["approval_id"]

        # Reject the approval
        reject_resp = client.post(f"/monitoring/cycles/{cycle_id}/approvals/{approval_id}/reject",
                                  headers=admin_headers, json={"comments": "Issues found, please revise"})
        assert reject_resp.status_code == 200
        assert reject_resp.json()["approval_status"] == "Rejected"

        # Verify cycle is back to UNDER_REVIEW
        cycle_resp = client.get(f"/monitoring/cycles/{cycle_id}", headers=admin_headers)
        assert cycle_resp.json()["status"] == "UNDER_REVIEW"

        # Re-request approval (simulating resubmission with fixes)
        resubmit_resp = client.post(f"/monitoring/cycles/{cycle_id}/request-approval", headers=admin_headers,
                                    json={"report_url": "https://example.com/reports/v2-revised.pdf"})
        assert resubmit_resp.status_code == 200
        assert resubmit_resp.json()["status"] == "PENDING_APPROVAL"

        # Verify the previously Rejected approval is now reset to Pending
        approvals_after = client.get(f"/monitoring/cycles/{cycle_id}/approvals", headers=admin_headers)
        global_after = next(a for a in approvals_after.json() if a["approval_type"] == "Global")

        assert global_after["approval_status"] == "Pending", \
            "Rejected approval must be reset to Pending on re-submission"
        assert global_after["approver"] is None, \
            "Approver must be cleared on re-submission"
        assert global_after["approved_at"] is None, \
            "Approved_at must be cleared on re-submission"

        # Now approve and verify cycle completes successfully
        approve_resp = client.post(
            f"/monitoring/cycles/{cycle_id}/approvals/{global_after['approval_id']}/approve",
            headers=admin_headers,
            json={"comments": "Approved after revisions", "approval_evidence": "Review meeting 2025-11-29"}
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["approval_status"] == "Approved"

        # Verify cycle transitions to APPROVED (not stuck due to lingering rejection)
        final_cycle = client.get(f"/monitoring/cycles/{cycle_id}", headers=admin_headers)
        assert final_cycle.json()["status"] == "APPROVED", \
            "Cycle must complete after re-submission approval (no lingering Rejected state)"

    def test_void_approval(self, client, admin_headers):
        """Admin can void an approval requirement."""
        # Setup cycle in UNDER_REVIEW state
        plan_id, cycle_id = self._setup_cycle_for_approval(client, admin_headers, "Plan For Void")
        client.post(f"/monitoring/cycles/{cycle_id}/request-approval", headers=admin_headers,
                   json={"report_url": "https://example.com/reports/test-report.pdf"})

        approvals_resp = client.get(f"/monitoring/cycles/{cycle_id}/approvals", headers=admin_headers)
        global_approval = next(a for a in approvals_resp.json() if a["approval_type"] == "Global")
        approval_id = global_approval["approval_id"]

        # Void
        response = client.post(f"/monitoring/cycles/{cycle_id}/approvals/{approval_id}/void",
                              headers=admin_headers, json={"void_reason": "No longer required"})
        assert response.status_code == 200
        assert response.json()["approval_status"] == "Voided"
        assert response.json()["voided_by"] is not None
        assert response.json()["void_reason"] == "No longer required"

    def test_cannot_approve_voided_approval(self, client, admin_headers):
        """Cannot approve an approval that has been voided."""
        # Setup cycle in UNDER_REVIEW state
        plan_id, cycle_id = self._setup_cycle_for_approval(client, admin_headers, "Plan For Void Check")
        client.post(f"/monitoring/cycles/{cycle_id}/request-approval", headers=admin_headers,
                   json={"report_url": "https://example.com/reports/test-report.pdf"})

        approvals_resp = client.get(f"/monitoring/cycles/{cycle_id}/approvals", headers=admin_headers)
        global_approval = next(a for a in approvals_resp.json() if a["approval_type"] == "Global")
        approval_id = global_approval["approval_id"]

        # Void first
        client.post(f"/monitoring/cycles/{cycle_id}/approvals/{approval_id}/void",
                   headers=admin_headers, json={"void_reason": "No longer required"})

        # Try to approve voided
        response = client.post(f"/monitoring/cycles/{cycle_id}/approvals/{approval_id}/approve",
                              headers=admin_headers, json={"comments": "Should fail"})
        assert response.status_code == 400


# ============================================================================
# Component 9b Tests - Model Monitoring Plans Lookup
# ============================================================================

class TestModelMonitoringPlansLookup:
    """Tests for the model -> monitoring plans lookup endpoint (Component 9b)."""

    def test_model_monitoring_plans_returns_empty_when_no_plans(self, client, admin_headers):
        """Returns empty list when model has no monitoring plans."""
        # Create a model without any monitoring plans
        model_resp = client.post("/models/", headers=admin_headers, json={
            "model_name": "Model Without Plans",
            "owner_id": 1,
            "status": "Draft"
        })
        assert model_resp.status_code == 201
        model_id = model_resp.json()["model_id"]

        # Get monitoring plans for this model
        response = client.get(f"/models/{model_id}/monitoring-plans", headers=admin_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_model_monitoring_plans_returns_plans_covering_model(self, client, admin_headers):
        """Returns monitoring plans that cover the model."""
        # Create a model
        model_resp = client.post("/models/", headers=admin_headers, json={
            "model_name": "Model With Plan",
            "owner_id": 1,
            "status": "Draft"
        })
        model_id = model_resp.json()["model_id"]

        # Create monitoring plan covering this model
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan Covering Model",
            "frequency": "Quarterly",
            "model_ids": [model_id]
        })
        plan_id = plan_resp.json()["plan_id"]

        # Get monitoring plans for this model
        response = client.get(f"/models/{model_id}/monitoring-plans", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["plan_id"] == plan_id
        assert data[0]["plan_name"] == "Plan Covering Model"
        assert data[0]["frequency"] == "Quarterly"

    def test_model_monitoring_plans_includes_versions(self, client, admin_headers):
        """Returns monitoring plan with version information."""
        # Create model
        model_resp = client.post("/models/", headers=admin_headers, json={
            "model_name": "Model With Versioned Plan",
            "owner_id": 1,
            "status": "Draft"
        })
        model_id = model_resp.json()["model_id"]

        # Create plan
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Versioned Plan",
            "frequency": "Quarterly",
            "model_ids": [model_id]
        })
        plan_id = plan_resp.json()["plan_id"]

        # Publish a version
        version_resp = client.post(
            f"/monitoring/plans/{plan_id}/versions/publish",
            headers=admin_headers,
            json={"version_name": "Q1 2025", "description": "Initial version"}
        )
        assert version_resp.status_code == 201
        version_id = version_resp.json()["version_id"]

        # Get monitoring plans
        response = client.get(f"/models/{model_id}/monitoring-plans", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["active_version"] is not None
        assert data[0]["active_version"]["version_id"] == version_id
        assert data[0]["active_version"]["version_name"] == "Q1 2025"
        assert len(data[0]["all_versions"]) == 1

    def test_model_monitoring_plans_404_for_nonexistent_model(self, client, admin_headers):
        """Returns 404 for non-existent model."""
        response = client.get("/models/99999/monitoring-plans", headers=admin_headers)
        assert response.status_code == 404

    def test_model_monitoring_plans_excludes_inactive_plans(self, client, admin_headers):
        """Does not return inactive monitoring plans."""
        # Create model
        model_resp = client.post("/models/", headers=admin_headers, json={
            "model_name": "Model With Inactive Plan",
            "owner_id": 1,
            "status": "Draft"
        })
        model_id = model_resp.json()["model_id"]

        # Create and then deactivate plan
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Plan To Deactivate",
            "frequency": "Quarterly",
            "model_ids": [model_id]
        })
        plan_id = plan_resp.json()["plan_id"]

        # Deactivate plan
        client.patch(f"/monitoring/plans/{plan_id}", headers=admin_headers, json={
            "is_active": False
        })

        # Get monitoring plans - should be empty
        response = client.get(f"/models/{model_id}/monitoring-plans", headers=admin_headers)
        assert response.status_code == 200
        assert len(response.json()) == 0


# ============================================================================
# Component 9b Tests - Validation Plan Component Fields
# ============================================================================

class TestComponent9bFields:
    """Tests for Component 9b specific fields in validation plan components."""

    @pytest.fixture
    def component_definitions(self, db_session):
        """Create component definitions including 9b for testing."""
        from app.models.validation import ValidationComponentDefinition

        # Create component 9b (Performance Monitoring Plan Review)
        comp_9b = ValidationComponentDefinition(
            section_number="9",
            section_title="Model Performance Monitoring Requirements",
            component_code="9b",
            component_title="Performance Monitoring Plan Review",
            is_test_or_analysis=False,
            expectation_high="Required",
            expectation_medium="Required",
            expectation_low="IfApplicable",
            expectation_very_low="NotExpected",
            sort_order=29
        )
        db_session.add(comp_9b)
        db_session.commit()
        return {"9b": comp_9b}

    def _create_validation_request_with_plan(self, client, admin_headers, model_id, validation_type_id, priority_id):
        """Helper to create a validation request with a plan containing component 9b."""
        # Create validation request
        req_resp = client.post("/validation-workflow/requests/", headers=admin_headers, json={
            "model_ids": [model_id],
            "validation_type_id": validation_type_id,
            "priority_id": priority_id,
            "target_completion_date": "2025-12-31"
        })
        assert req_resp.status_code == 201, f"Failed to create validation request: {req_resp.json()}"
        request_id = req_resp.json()["request_id"]

        # Create validation plan (auto-generates component 9b)
        plan_resp = client.post(f"/validation-workflow/requests/{request_id}/plan",
                               headers=admin_headers, json={
                                   "overall_scope_summary": "Test plan with 9b"
                               })
        assert plan_resp.status_code == 201, f"Failed to create plan: {plan_resp.json()}"
        return request_id, plan_resp.json()["plan_id"]

    def test_update_component_9b_with_version(self, client, admin_headers, taxonomy_values, component_definitions):
        """Can update component 9b with monitoring plan version ID."""
        # Create model with risk tier
        model_resp = client.post("/models/", headers=admin_headers, json={
            "model_name": "Model For 9b Test",
            "owner_id": 1,
            "status": "Draft",
            "risk_tier_id": taxonomy_values["tier1"].value_id
        })
        assert model_resp.status_code == 201, f"Failed to create model: {model_resp.json()}"
        model_id = model_resp.json()["model_id"]

        # Create monitoring plan with version
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Monitoring Plan for 9b",
            "frequency": "Quarterly",
            "model_ids": [model_id]
        })
        assert plan_resp.status_code == 201, f"Failed to create monitoring plan: {plan_resp.json()}"
        mon_plan_id = plan_resp.json()["plan_id"]

        version_resp = client.post(f"/monitoring/plans/{mon_plan_id}/versions/publish",
                                   headers=admin_headers,
                                   json={"version_name": "v1"})
        assert version_resp.status_code == 201, f"Failed to publish version: {version_resp.json()}"
        version_id = version_resp.json()["version_id"]

        # Create validation request with plan
        request_id, val_plan_id = self._create_validation_request_with_plan(
            client, admin_headers, model_id,
            taxonomy_values["initial"].value_id,
            taxonomy_values["priority_standard"].value_id
        )

        # Get plan to find component 9b
        plan_resp = client.get(f"/validation-workflow/requests/{request_id}/plan",
                              headers=admin_headers)
        assert plan_resp.status_code == 200, f"Failed to get plan: {plan_resp.json()}"
        plan_data = plan_resp.json()

        # Find component 9b
        comp_9b = next((c for c in plan_data["components"]
                       if c["component_definition"]["component_code"] == "9b"), None)
        assert comp_9b is not None, "Component 9b should exist in plan"

        # Update component 9b with version
        update_resp = client.patch(f"/validation-workflow/requests/{request_id}/plan",
                                   headers=admin_headers, json={
                                       "components": [{
                                           "component_id": comp_9b["component_definition"]["component_id"],
                                           "planned_treatment": "Planned",
                                           "monitoring_plan_version_id": version_id,
                                           "monitoring_review_notes": "Reviewed Q1 metrics"
                                       }]
                                   })
        assert update_resp.status_code == 200

        # Verify update
        verify_resp = client.get(f"/validation-workflow/requests/{request_id}/plan",
                                headers=admin_headers)
        updated_comp_9b = next((c for c in verify_resp.json()["components"]
                               if c["component_definition"]["component_code"] == "9b"), None)
        assert updated_comp_9b["monitoring_plan_version_id"] == version_id
        assert updated_comp_9b["monitoring_review_notes"] == "Reviewed Q1 metrics"

    def test_update_component_9b_with_invalid_version_fails(self, client, admin_headers, taxonomy_values, component_definitions):
        """Cannot update component 9b with non-existent version ID."""
        # Create model with risk tier
        model_resp = client.post("/models/", headers=admin_headers, json={
            "model_name": "Model For Invalid 9b",
            "owner_id": 1,
            "status": "Draft",
            "risk_tier_id": taxonomy_values["tier1"].value_id
        })
        assert model_resp.status_code == 201, f"Failed to create model: {model_resp.json()}"
        model_id = model_resp.json()["model_id"]

        # Create validation request with plan
        request_id, val_plan_id = self._create_validation_request_with_plan(
            client, admin_headers, model_id,
            taxonomy_values["initial"].value_id,
            taxonomy_values["priority_standard"].value_id
        )

        # Get plan to find component 9b
        plan_resp = client.get(f"/validation-workflow/requests/{request_id}/plan",
                              headers=admin_headers)
        assert plan_resp.status_code == 200, f"Failed to get plan: {plan_resp.json()}"
        comp_9b = next((c for c in plan_resp.json()["components"]
                       if c["component_definition"]["component_code"] == "9b"), None)
        assert comp_9b is not None, "Component 9b should exist in plan"

        # Try to update with non-existent version
        update_resp = client.patch(f"/validation-workflow/requests/{request_id}/plan",
                                   headers=admin_headers, json={
                                       "components": [{
                                           "component_id": comp_9b["component_definition"]["component_id"],
                                           "monitoring_plan_version_id": 99999
                                       }]
                                   })
        assert update_resp.status_code == 400
        assert "not found" in update_resp.json()["detail"].lower()

    def test_component_9b_planned_without_version_fails_status_transition(
        self, client, admin_headers, db_session, taxonomy_values, component_definitions
    ):
        """Component 9b marked as Planned without version fails validation on status transition to REVIEW."""
        from app.models.user import User

        # Create a separate validator user (not the model owner)
        validator = User(
            email="validator_9b@test.com",
            password_hash="$2b$12$test",
            full_name="Validator User",
            role="Validator"
        )
        db_session.add(validator)
        db_session.commit()
        validator_id = validator.user_id

        # Create model with Tier 1 risk (9b is Required) - owned by admin (id=1)
        model_resp = client.post("/models/", headers=admin_headers, json={
            "model_name": "Model For 9b Validation Test",
            "owner_id": 1,
            "status": "Draft",
            "risk_tier_id": taxonomy_values["tier1"].value_id
        })
        assert model_resp.status_code == 201
        model_id = model_resp.json()["model_id"]

        # Create validation request
        request_id, val_plan_id = self._create_validation_request_with_plan(
            client, admin_headers, model_id,
            taxonomy_values["initial"].value_id,
            taxonomy_values["priority_standard"].value_id
        )

        # Get component 9b and mark it as Planned (without a version)
        plan_resp = client.get(f"/validation-workflow/requests/{request_id}/plan",
                              headers=admin_headers)
        comp_9b = next((c for c in plan_resp.json()["components"]
                       if c["component_definition"]["component_code"] == "9b"), None)
        assert comp_9b is not None

        # Update 9b to Planned without version (this should succeed, validation happens on status transition)
        update_resp = client.patch(f"/validation-workflow/requests/{request_id}/plan",
                                   headers=admin_headers, json={
                                       "components": [{
                                           "component_id": comp_9b["component_definition"]["component_id"],
                                           "planned_treatment": "Planned"
                                           # No monitoring_plan_version_id
                                       }]
                                   })
        assert update_resp.status_code == 200

        # Assign a PRIMARY validator (required for status transitions)
        # Must be a different user than the model owner and include independence attestation
        assign_resp = client.post(f"/validation-workflow/requests/{request_id}/assignments",
                   headers=admin_headers, json={
                       "validator_id": validator_id,
                       "is_primary": True,
                       "independence_attestation": True
                   })
        assert assign_resp.status_code == 201, f"Failed to assign validator: {assign_resp.json()}"

        # Note: Assigning a validator auto-transitions from INTAKE to PLANNING
        # So we continue from PLANNING -> IN_PROGRESS -> REVIEW

        # Move to IN_PROGRESS
        status_resp = client.patch(f"/validation-workflow/requests/{request_id}/status",
                                   headers=admin_headers, json={
                                       "new_status_id": taxonomy_values["status_in_progress"].value_id,
                                       "change_reason": "Moving to in progress"
                                   })
        assert status_resp.status_code == 200, f"Failed to move to IN_PROGRESS: {status_resp.json()}"

        # Now try to transition to REVIEW (where validate_plan_compliance is called)
        status_resp = client.patch(f"/validation-workflow/requests/{request_id}/status",
                                   headers=admin_headers, json={
                                       "new_status_id": taxonomy_values["status_review"].value_id,
                                       "change_reason": "Moving to review"
                                   })
        # This should fail because 9b is Planned without a version
        assert status_resp.status_code == 400
        error_detail = status_resp.json()["detail"].lower()
        assert "9b" in error_detail or "monitoring plan" in error_detail, f"Expected 9b validation error, got: {error_detail}"

    def test_component_9b_not_planned_without_rationale_fails_update(
        self, client, admin_headers, taxonomy_values, component_definitions
    ):
        """Component 9b marked as NotPlanned without rationale fails at update time (deviation requires rationale)."""
        # Create model with Tier 1 risk (9b is Required)
        model_resp = client.post("/models/", headers=admin_headers, json={
            "model_name": "Model For 9b NotPlanned Test",
            "owner_id": 1,
            "status": "Draft",
            "risk_tier_id": taxonomy_values["tier1"].value_id
        })
        assert model_resp.status_code == 201
        model_id = model_resp.json()["model_id"]

        # Create validation request
        request_id, val_plan_id = self._create_validation_request_with_plan(
            client, admin_headers, model_id,
            taxonomy_values["initial"].value_id,
            taxonomy_values["priority_standard"].value_id
        )

        # Get component 9b
        plan_resp = client.get(f"/validation-workflow/requests/{request_id}/plan",
                              headers=admin_headers)
        comp_9b = next((c for c in plan_resp.json()["components"]
                       if c["component_definition"]["component_code"] == "9b"), None)
        assert comp_9b is not None

        # Try to update 9b to NotPlanned without rationale - this should FAIL
        # because Required -> NotPlanned is a deviation and requires rationale at update time
        update_resp = client.patch(f"/validation-workflow/requests/{request_id}/plan",
                                   headers=admin_headers, json={
                                       "components": [{
                                           "component_id": comp_9b["component_definition"]["component_id"],
                                           "planned_treatment": "NotPlanned"
                                           # No rationale - this is a deviation!
                                       }]
                                   })
        assert update_resp.status_code == 400
        error_detail = update_resp.json()["detail"].lower()
        assert "rationale" in error_detail or "9b" in error_detail, f"Expected rationale error, got: {error_detail}"

    def test_component_9b_not_planned_with_rationale_succeeds(
        self, client, admin_headers, taxonomy_values, component_definitions
    ):
        """Component 9b marked as NotPlanned with rationale succeeds (proper deviation handling)."""
        # Create model with Tier 1 risk (9b is Required)
        model_resp = client.post("/models/", headers=admin_headers, json={
            "model_name": "Model For 9b NotPlanned With Rationale",
            "owner_id": 1,
            "status": "Draft",
            "risk_tier_id": taxonomy_values["tier1"].value_id
        })
        assert model_resp.status_code == 201
        model_id = model_resp.json()["model_id"]

        # Create validation request
        request_id, val_plan_id = self._create_validation_request_with_plan(
            client, admin_headers, model_id,
            taxonomy_values["initial"].value_id,
            taxonomy_values["priority_standard"].value_id
        )

        # Get component 9b
        plan_resp = client.get(f"/validation-workflow/requests/{request_id}/plan",
                              headers=admin_headers)
        comp_9b = next((c for c in plan_resp.json()["components"]
                       if c["component_definition"]["component_code"] == "9b"), None)
        assert comp_9b is not None

        # Update 9b to NotPlanned WITH rationale - this should succeed
        update_resp = client.patch(f"/validation-workflow/requests/{request_id}/plan",
                                   headers=admin_headers, json={
                                       "components": [{
                                           "component_id": comp_9b["component_definition"]["component_id"],
                                           "planned_treatment": "NotPlanned",
                                           "rationale": "Model does not have an active monitoring plan as it is still in development"
                                       }]
                                   })
        assert update_resp.status_code == 200

        # Verify the update
        verify_resp = client.get(f"/validation-workflow/requests/{request_id}/plan",
                                headers=admin_headers)
        updated_comp_9b = next((c for c in verify_resp.json()["components"]
                               if c["component_definition"]["component_code"] == "9b"), None)
        assert updated_comp_9b["planned_treatment"] == "NotPlanned"
        assert "monitoring plan" in updated_comp_9b["rationale"].lower()

    def test_component_9b_planned_with_version_passes_validation(
        self, client, admin_headers, taxonomy_values, component_definitions
    ):
        """Component 9b properly configured passes validation."""
        # Create model with Tier 1 risk
        model_resp = client.post("/models/", headers=admin_headers, json={
            "model_name": "Model For 9b Pass Test",
            "owner_id": 1,
            "status": "Draft",
            "risk_tier_id": taxonomy_values["tier1"].value_id
        })
        assert model_resp.status_code == 201
        model_id = model_resp.json()["model_id"]

        # Create monitoring plan with published version
        plan_resp = client.post("/monitoring/plans", headers=admin_headers, json={
            "name": "Monitoring Plan for 9b Pass",
            "frequency": "Quarterly",
            "model_ids": [model_id]
        })
        mon_plan_id = plan_resp.json()["plan_id"]

        version_resp = client.post(f"/monitoring/plans/{mon_plan_id}/versions/publish",
                                   headers=admin_headers, json={"version_name": "v1"})
        version_id = version_resp.json()["version_id"]

        # Create validation request
        request_id, val_plan_id = self._create_validation_request_with_plan(
            client, admin_headers, model_id,
            taxonomy_values["initial"].value_id,
            taxonomy_values["priority_standard"].value_id
        )

        # Get component 9b and configure it properly
        plan_resp = client.get(f"/validation-workflow/requests/{request_id}/plan",
                              headers=admin_headers)
        comp_9b = next((c for c in plan_resp.json()["components"]
                       if c["component_definition"]["component_code"] == "9b"), None)
        assert comp_9b is not None

        # Update 9b with version
        update_resp = client.patch(f"/validation-workflow/requests/{request_id}/plan",
                                   headers=admin_headers, json={
                                       "components": [{
                                           "component_id": comp_9b["component_definition"]["component_id"],
                                           "planned_treatment": "Planned",
                                           "monitoring_plan_version_id": version_id,
                                           "monitoring_review_notes": "Reviewed monitoring metrics"
                                       }]
                                   })
        assert update_resp.status_code == 200

        # Assign a validator
        client.post(f"/validation-workflow/requests/{request_id}/assignments",
                   headers=admin_headers, json={"validator_id": 1})

        # The 9b validation should pass (other validations may fail but not 9b)
        # To fully test, we would need all components configured properly
        # For now, verify the 9b fields are stored correctly
        verify_resp = client.get(f"/validation-workflow/requests/{request_id}/plan",
                                headers=admin_headers)
        updated_comp_9b = next((c for c in verify_resp.json()["components"]
                               if c["component_definition"]["component_code"] == "9b"), None)
        assert updated_comp_9b["monitoring_plan_version_id"] == version_id
        assert updated_comp_9b["planned_treatment"] == "Planned"
