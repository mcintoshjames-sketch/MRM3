"""Tests for team management and LOB team inheritance."""
from fastapi.testclient import TestClient

from app.core.team_utils import build_lob_team_map, get_all_lob_ids_for_team
from app.core.security import get_password_hash
from app.core.roles import RoleCode
from app.models.team import Team
from app.models.lob import LOBUnit
from app.models.model import Model
from app.models.user import User
from app.models.role import Role
from app.models.region import Region
from app.models.model_region import ModelRegion


def test_team_crud_and_lob_assignment(
    client: TestClient,
    admin_headers,
    lob_hierarchy
):
    create_resp = client.post(
        "/teams/",
        json={"name": "Retail Risk Team", "description": "Retail team", "is_active": True},
        headers=admin_headers
    )
    assert create_resp.status_code == 201
    team = create_resp.json()
    team_id = team["team_id"]

    list_resp = client.get("/teams/", headers=admin_headers)
    assert list_resp.status_code == 200
    assert any(t["team_id"] == team_id for t in list_resp.json())

    assign_resp = client.post(
        f"/teams/{team_id}/lobs",
        json={"lob_id": lob_hierarchy["credit"].lob_id},
        headers=admin_headers
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["lob_id"] == lob_hierarchy["credit"].lob_id

    detail_resp = client.get(f"/teams/{team_id}", headers=admin_headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["lob_count"] == 1
    assert detail["lob_units"][0]["lob_id"] == lob_hierarchy["credit"].lob_id

    remove_resp = client.delete(
        f"/teams/{team_id}/lobs/{lob_hierarchy['credit'].lob_id}",
        headers=admin_headers
    )
    assert remove_resp.status_code == 204

    detail_resp = client.get(f"/teams/{team_id}", headers=admin_headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["lob_count"] == 0

    delete_resp = client.delete(f"/teams/{team_id}", headers=admin_headers)
    assert delete_resp.status_code == 204

    list_resp = client.get("/teams/", headers=admin_headers)
    assert any(t["team_id"] == team_id and t["is_active"] is False for t in list_resp.json())


def test_build_lob_team_map_closest_ancestor(db_session, lob_hierarchy):
    parent_team = Team(name="Retail Team", description="Retail", is_active=True)
    child_team = Team(name="Credit Team", description="Credit", is_active=True)
    db_session.add_all([parent_team, child_team])
    db_session.flush()

    lob_hierarchy["retail"].team_id = parent_team.team_id
    lob_hierarchy["credit"].team_id = child_team.team_id

    credit_child = LOBUnit(
        code="CRD_SUB",
        name="Credit Sub",
        org_unit="30001",
        level=lob_hierarchy["credit"].level + 1,
        parent_id=lob_hierarchy["credit"].lob_id,
        is_active=True
    )
    db_session.add(credit_child)
    db_session.commit()

    lob_team_map = build_lob_team_map(db_session)
    assert lob_team_map[credit_child.lob_id] == child_team.team_id
    assert lob_team_map[lob_hierarchy["deposits"].lob_id] == parent_team.team_id


def test_get_all_lob_ids_for_team_excludes_other_team_branches(db_session, lob_hierarchy):
    parent_team = Team(name="Retail Root Team", description="Retail", is_active=True)
    child_team = Team(name="Credit Root Team", description="Credit", is_active=True)
    db_session.add_all([parent_team, child_team])
    db_session.flush()

    lob_hierarchy["retail"].team_id = parent_team.team_id
    lob_hierarchy["credit"].team_id = child_team.team_id

    credit_child = LOBUnit(
        code="CRD_CHILD",
        name="Credit Child",
        org_unit="30002",
        level=lob_hierarchy["credit"].level + 1,
        parent_id=lob_hierarchy["credit"].lob_id,
        is_active=True
    )
    db_session.add(credit_child)
    db_session.commit()

    parent_lobs = get_all_lob_ids_for_team(db_session, parent_team.team_id)
    assert lob_hierarchy["retail"].lob_id in parent_lobs
    assert lob_hierarchy["deposits"].lob_id in parent_lobs
    assert lob_hierarchy["credit"].lob_id not in parent_lobs
    assert credit_child.lob_id not in parent_lobs


def test_list_models_team_filter(
    client: TestClient,
    db_session,
    admin_headers,
    lob_hierarchy,
    test_user,
    usage_frequency
):
    other_role_id = db_session.query(Role).filter(Role.code == RoleCode.USER.value).first().role_id
    other_user = User(
        email="other@example.com",
        full_name="Other User",
        password_hash=get_password_hash("otherpass"),
        role_id=other_role_id,
        lob_id=lob_hierarchy["wholesale"].lob_id
    )
    db_session.add(other_user)
    db_session.flush()

    team = Team(name="Retail Owners", description="Retail team", is_active=True)
    db_session.add(team)
    db_session.flush()
    lob_hierarchy["retail"].team_id = team.team_id

    model_with_team = Model(
        model_name="Retail Model",
        description="Retail model",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id,
        usage_frequency_id=usage_frequency["daily"].value_id,
    )
    model_unassigned = Model(
        model_name="Wholesale Model",
        description="Wholesale model",
        development_type="In-House",
        status="Active",
        owner_id=other_user.user_id,
        usage_frequency_id=usage_frequency["daily"].value_id,
    )
    db_session.add_all([model_with_team, model_unassigned])
    db_session.commit()

    team_resp = client.get(f"/models/?team_id={team.team_id}", headers=admin_headers)
    assert team_resp.status_code == 200
    team_ids = {model["model_id"] for model in team_resp.json()}
    assert model_with_team.model_id in team_ids
    assert model_unassigned.model_id not in team_ids

    unassigned_resp = client.get("/models/?team_id=0", headers=admin_headers)
    assert unassigned_resp.status_code == 200
    unassigned_ids = {model["model_id"] for model in unassigned_resp.json()}
    assert model_unassigned.model_id in unassigned_ids
    assert model_with_team.model_id not in unassigned_ids


def test_regional_compliance_report_team_filter(
    client: TestClient,
    db_session,
    admin_headers,
    lob_hierarchy,
    test_user,
    usage_frequency
):
    team = Team(name="Retail Compliance", description="Retail", is_active=True)
    db_session.add(team)
    db_session.flush()
    lob_hierarchy["retail"].team_id = team.team_id

    model = Model(
        model_name="Retail Region Model",
        description="Regional model",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id,
        usage_frequency_id=usage_frequency["daily"].value_id,
    )
    db_session.add(model)
    db_session.flush()

    region = Region(code="US", name="United States", requires_regional_approval=False)
    db_session.add(region)
    db_session.flush()

    db_session.add(ModelRegion(model_id=model.model_id, region_id=region.region_id))
    db_session.commit()

    team_resp = client.get(
        f"/regional-compliance-report/?only_deployed=false&team_id={team.team_id}",
        headers=admin_headers
    )
    assert team_resp.status_code == 200
    assert team_resp.json()["total_records"] == 1
    assert team_resp.json()["records"][0]["model_id"] == model.model_id

    unassigned_resp = client.get(
        "/regional-compliance-report/?only_deployed=false&team_id=0",
        headers=admin_headers
    )
    assert unassigned_resp.status_code == 200
    assert unassigned_resp.json()["total_records"] == 0
