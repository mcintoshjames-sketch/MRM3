"""
Independent unit tests for RLS enforcement across critical endpoints.
These tests verify that access controls are correctly applied for different user roles.
"""
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.core.monitoring_membership import MonitoringMembershipService
from app.models.user import User
from app.models.role import Role
from app.core.roles import RoleCode
from app.models.model import Model
from app.models.model_delegate import ModelDelegate
from app.models.monitoring import (
    MonitoringTeam, MonitoringPlan, MonitoringCycle,
    MonitoringCycleStatus, monitoring_team_members
)
from app.models.decommissioning import DecommissioningRequest
from app.models.team import Team
from app.models.lob import LOBUnit

# --- Fixtures for RLS Personas ---


@pytest.fixture
def rls_password_hash():
    return get_password_hash("testpass123")


@pytest.fixture
def rls_users(db_session: Session, rls_password_hash, lob_hierarchy):
    """Create a set of users with different roles for RLS testing."""
    roles = {r.code: r.role_id for r in db_session.query(Role).all()}

    # 1. Model Owner (Standard User)
    owner = User(
        email="owner@example.com", full_name="Model Owner",
        password_hash=rls_password_hash, role_id=roles[RoleCode.USER.value],
        lob_id=lob_hierarchy["retail"].lob_id
    )

    # 2. Delegate (Standard User)
    delegate = User(
        email="delegate@example.com", full_name="Model Delegate",
        password_hash=rls_password_hash, role_id=roles[RoleCode.USER.value],
        lob_id=lob_hierarchy["retail"].lob_id
    )

    # 3. Unprivileged User (Standard User, no relation to model)
    stranger = User(
        email="stranger@example.com", full_name="Stranger User",
        password_hash=rls_password_hash, role_id=roles[RoleCode.USER.value],
        lob_id=lob_hierarchy["wholesale"].lob_id
    )

    # 4. Monitoring Team Member (Standard User)
    monitor = User(
        email="monitor@example.com", full_name="Monitoring User",
        password_hash=rls_password_hash, role_id=roles[RoleCode.USER.value],
        lob_id=lob_hierarchy["retail"].lob_id
    )

    # 5. Validator (Privileged)
    validator = User(
        email="validator@example.com", full_name="Validator User",
        password_hash=rls_password_hash, role_id=roles[RoleCode.VALIDATOR.value],
        lob_id=lob_hierarchy["corporate"].lob_id
    )

    db_session.add_all([owner, delegate, stranger, monitor, validator])
    db_session.commit()

    return {
        "owner": owner,
        "delegate": delegate,
        "stranger": stranger,
        "monitor": monitor,
        "validator": validator
    }


@pytest.fixture
def rls_headers(rls_users):
    """Generate auth headers for all RLS users."""
    headers = {}
    for name, user in rls_users.items():
        token = create_access_token(data={"sub": user.email})
        headers[name] = {"Authorization": f"Bearer {token}"}
    return headers


@pytest.fixture
def rls_data(db_session: Session, rls_users, usage_frequency):
    """Setup model, delegation, monitoring plan, and decommissioning request."""
    owner = rls_users["owner"]
    delegate = rls_users["delegate"]
    monitor = rls_users["monitor"]

    # 1. Create Model owned by 'owner'
    model = Model(
        model_name="RLS Test Model",
        description="Model for RLS testing",
        development_type="In-House",
        status="Active",
        owner_id=owner.user_id,
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.commit()

    # 2. Assign 'delegate' to model
    delegation = ModelDelegate(
        model_id=model.model_id,
        user_id=delegate.user_id,
        can_submit_changes=True,
        delegated_by_id=owner.user_id
    )
    db_session.add(delegation)

    # 3. Create Monitoring Team and add 'monitor' user
    mon_team = MonitoringTeam(
        name="RLS Monitoring Team",
        description="Team for RLS tests",
        is_active=True
    )
    db_session.add(mon_team)
    db_session.flush()

    # Add member via association table (manual insert for simplicity if model not mapped,
    # but here we assume standard relationship)
    # Note: monitoring_team_members is an association table, usually handled via relationship
    # We'll try to use the relationship if defined on User or MonitoringTeam
    # Checking MonitoringTeam model... it has 'members' relationship
    mon_team.members.append(monitor)

    # 4. Create Monitoring Plan for the model
    plan = MonitoringPlan(
        name="RLS Plan",
        frequency="Quarterly",
        monitoring_team_id=mon_team.team_id,
        is_active=True
    )
    db_session.add(plan)
    db_session.flush()

    # Link plan to model
    MonitoringMembershipService(db_session).replace_plan_models(
        plan.plan_id,
        [model.model_id],
        changed_by_user_id=owner.user_id,
        reason="RLS test setup",
    )

    # 5. Create Monitoring Cycle
    cycle = MonitoringCycle(
        plan_id=plan.plan_id,
        period_start_date=date.today(),
        period_end_date=date.today() + timedelta(days=90),
        submission_due_date=date.today() + timedelta(days=100),
        report_due_date=date.today() + timedelta(days=130),
        status=MonitoringCycleStatus.PENDING.value
    )
    db_session.add(cycle)

    # 6. Create Decommissioning Request
    decom_req = DecommissioningRequest(
        model_id=model.model_id,
        created_by_id=owner.user_id,
        status="PENDING",
        # Reusing a taxonomy value for simplicity
        reason_id=usage_frequency["daily"].value_id,
        last_production_date=date.today(),
        archive_location="s3://archive/model"
    )
    db_session.add(decom_req)

    # 7. Create a Reporting Team (for Team Models RLS)
    rep_team = Team(name="RLS Reporting Team", is_active=True)
    db_session.add(rep_team)
    db_session.flush()

    # Assign owner's LOB to this team (indirectly linking model to team)
    # We need to find the LOBUnit and set its team_id
    lob = db_session.query(LOBUnit).filter(
        LOBUnit.lob_id == owner.lob_id).first()
    lob.team_id = rep_team.team_id
    db_session.add(lob)

    db_session.commit()

    return {
        "model": model,
        "plan": plan,
        "cycle": cycle,
        "decom_req": decom_req,
        "rep_team": rep_team
    }

# --- Tests ---


class TestMonitoringRLS:
    """Test RLS enforcement for Monitoring endpoints."""

    def test_list_plans_rls(self, client: TestClient, rls_headers, rls_data):
        """
        Verify GET /monitoring/plans visibility:
        - Owner/Delegate: Should see plan (via model access)
        - Monitor: Should see plan (via team membership)
        - Validator: Should see plan (privileged)
        - Stranger: Should NOT see plan
        """
        # 1. Stranger (No access)
        resp = client.get("/monitoring/plans", headers=rls_headers["stranger"])
        assert resp.status_code == 200
        plans = resp.json()
        assert not any(
            p["plan_id"] == rls_data["plan"].plan_id for p in plans), "Stranger should not see plan"

        # 2. Monitor (Team Member)
        resp = client.get("/monitoring/plans", headers=rls_headers["monitor"])
        assert resp.status_code == 200
        plans = resp.json()
        assert any(
            p["plan_id"] == rls_data["plan"].plan_id for p in plans), "Monitor should see plan"

        # 3. Owner (Model Access)
        resp = client.get("/monitoring/plans", headers=rls_headers["owner"])
        assert resp.status_code == 200
        plans = resp.json()
        assert any(
            p["plan_id"] == rls_data["plan"].plan_id for p in plans), "Owner should see plan"

        # 4. Delegate (Model Access)
        resp = client.get("/monitoring/plans", headers=rls_headers["delegate"])
        assert resp.status_code == 200
        plans = resp.json()
        assert any(
            p["plan_id"] == rls_data["plan"].plan_id for p in plans), "Delegate should see plan"

    def test_get_plan_detail_rls(self, client: TestClient, rls_headers, rls_data):
        """Verify GET /monitoring/plans/{id} access control."""
        plan_id = rls_data["plan"].plan_id

        # Stranger -> 403/404
        resp = client.get(
            f"/monitoring/plans/{plan_id}", headers=rls_headers["stranger"])
        assert resp.status_code in [
            403, 404], "Stranger should be denied access"

        # Owner -> 200
        resp = client.get(
            f"/monitoring/plans/{plan_id}", headers=rls_headers["owner"])
        assert resp.status_code == 200, "Owner should access plan"

        # Delegate -> 200
        resp = client.get(
            f"/monitoring/plans/{plan_id}", headers=rls_headers["delegate"])
        assert resp.status_code == 200, "Delegate should access plan"

    def test_list_cycles_rls(self, client: TestClient, rls_headers, rls_data):
        """Verify GET /monitoring/plans/{id}/cycles access control."""
        plan_id = rls_data["plan"].plan_id

        # Stranger -> 403/404
        resp = client.get(
            f"/monitoring/plans/{plan_id}/cycles", headers=rls_headers["stranger"])
        assert resp.status_code in [
            403, 404], "Stranger should be denied access"

        # Owner -> 200
        resp = client.get(
            f"/monitoring/plans/{plan_id}/cycles", headers=rls_headers["owner"])
        assert resp.status_code == 200, "Owner should access cycles"

    def test_get_cycle_detail_rls(self, client: TestClient, rls_headers, rls_data):
        """Verify GET /monitoring/cycles/{id} access control."""
        cycle_id = rls_data["cycle"].cycle_id

        # Stranger -> 403/404
        resp = client.get(
            f"/monitoring/cycles/{cycle_id}", headers=rls_headers["stranger"])
        assert resp.status_code in [
            403, 404], "Stranger should be denied access"

        # Delegate -> 200
        resp = client.get(
            f"/monitoring/cycles/{cycle_id}", headers=rls_headers["delegate"])
        assert resp.status_code == 200, "Delegate should access cycle"


class TestDecommissioningRLS:
    """Test RLS enforcement for Decommissioning endpoints."""

    def test_list_decommissioning_rls(self, client: TestClient, rls_headers, rls_data):
        """
        Verify GET /decommissioning/ visibility:
        - Owner/Delegate: Should see request
        - Stranger: Should NOT see request
        """
        req_id = rls_data["decom_req"].request_id

        # Stranger
        resp = client.get("/decommissioning/", headers=rls_headers["stranger"])
        assert resp.status_code == 200
        reqs = resp.json()
        assert not any(
            r["request_id"] == req_id for r in reqs), "Stranger should not see request"

        # Owner
        resp = client.get("/decommissioning/", headers=rls_headers["owner"])
        assert resp.status_code == 200
        reqs = resp.json()
        assert any(r["request_id"] ==
                   req_id for r in reqs), "Owner should see request"

        # Delegate
        resp = client.get("/decommissioning/", headers=rls_headers["delegate"])
        assert resp.status_code == 200
        reqs = resp.json()
        assert any(r["request_id"] ==
                   req_id for r in reqs), "Delegate should see request"

    def test_get_decommissioning_detail_rls(self, client: TestClient, rls_headers, rls_data):
        """Verify GET /decommissioning/{id} access control."""
        req_id = rls_data["decom_req"].request_id

        # Stranger -> 403/404
        resp = client.get(
            f"/decommissioning/{req_id}", headers=rls_headers["stranger"])
        assert resp.status_code in [
            403, 404], "Stranger should be denied access"

        # Owner -> 200
        resp = client.get(
            f"/decommissioning/{req_id}", headers=rls_headers["owner"])
        assert resp.status_code == 200, "Owner should access request"


class TestTeamModelsRLS:
    """Test RLS enforcement for Team Models endpoint."""

    def test_get_team_models_rls(self, client: TestClient, rls_headers, rls_data):
        """
        Verify GET /teams/{id}/models visibility:
        - Owner: Should see their model in the team list
        - Stranger: Should NOT see the owner's model (even if they can see the team)
        """
        team_id = rls_data["rep_team"].team_id
        model_id = rls_data["model"].model_id

        # Owner
        resp = client.get(f"/teams/{team_id}/models",
                          headers=rls_headers["owner"])
        assert resp.status_code == 200
        models = resp.json()
        assert any(m["model_id"] ==
                   model_id for m in models), "Owner should see their model"

        # Stranger
        # Note: Stranger might be able to query the team, but the model list should be filtered
        resp = client.get(f"/teams/{team_id}/models",
                          headers=rls_headers["stranger"])
        assert resp.status_code == 200
        models = resp.json()
        assert not any(
            m["model_id"] == model_id for m in models), "Stranger should not see owner's model"
