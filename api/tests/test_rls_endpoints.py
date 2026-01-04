"""API-level RLS regression tests."""
from datetime import date, timedelta

from app.core.roles import RoleCode
from app.core.security import create_access_token, get_password_hash
from app.models.decommissioning import DecommissioningRequest
from app.models.irp import IRP
from app.models.model import Model
from app.models.model_exception import ModelException
from app.models.monitoring import (
    MonitoringCycle,
    MonitoringCycleApproval,
    MonitoringCycleStatus,
    MonitoringFrequency,
    MonitoringPlan,
    MonitoringTeam,
)
from app.models.recommendation import Recommendation
from app.models.region import Region
from app.models.role import Role
from app.models.team import Team
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.user import User
from app.models.validation import ValidationRequest, ValidationRequestModelVersion


def _create_model(db_session, owner, usage_frequency, name, submitted_by):
    model = Model(
        model_name=name,
        development_type="In-House",
        status="In Development",
        owner_id=owner.user_id,
        submitted_by_user_id=submitted_by.user_id,
        usage_frequency_id=usage_frequency["daily"].value_id,
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


def _create_mrsa_model(db_session, owner, usage_frequency, name, submitted_by):
    model = Model(
        model_name=name,
        development_type="In-House",
        status="In Development",
        owner_id=owner.user_id,
        submitted_by_user_id=submitted_by.user_id,
        usage_frequency_id=usage_frequency["daily"].value_id,
        is_mrsa=True,
        row_approval_status=None,
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


def _create_exception(db_session, model, code):
    exception = ModelException(
        exception_code=code,
        model_id=model.model_id,
        exception_type="UNMITIGATED_PERFORMANCE",
        description="Test exception",
    )
    db_session.add(exception)
    db_session.commit()
    db_session.refresh(exception)
    return exception


def _create_validation_request(db_session, model, requestor, taxonomy_values):
    request = ValidationRequest(
        request_date=date.today(),
        requestor_id=requestor.user_id,
        validation_type_id=taxonomy_values["initial"].value_id,
        priority_id=taxonomy_values["priority_standard"].value_id,
        target_completion_date=date.today() + timedelta(days=30),
        current_status_id=taxonomy_values["status_intake"].value_id,
    )
    db_session.add(request)
    db_session.flush()
    db_session.add(
        ValidationRequestModelVersion(
            request_id=request.request_id,
            model_id=model.model_id,
        )
    )
    db_session.commit()
    db_session.refresh(request)
    return request


def _create_recommendation_taxonomies(db_session):
    status_tax = Taxonomy(name="Recommendation Status", is_system=True)
    priority_tax = Taxonomy(name="Recommendation Priority", is_system=True)
    category_tax = Taxonomy(name="Recommendation Category", is_system=True)
    db_session.add_all([status_tax, priority_tax, category_tax])
    db_session.flush()

    status_open = TaxonomyValue(
        taxonomy_id=status_tax.taxonomy_id,
        code="REC_OPEN",
        label="Open",
        sort_order=1,
    )
    priority_high = TaxonomyValue(
        taxonomy_id=priority_tax.taxonomy_id,
        code="HIGH",
        label="High",
        sort_order=1,
    )
    category_data = TaxonomyValue(
        taxonomy_id=category_tax.taxonomy_id,
        code="DATA_QUALITY",
        label="Data Quality",
        sort_order=1,
    )
    db_session.add_all([status_open, priority_high, category_data])
    db_session.commit()

    return {
        "status_open": status_open,
        "priority_high": priority_high,
        "category_data": category_data,
    }


def _create_recommendation(db_session, model, created_by, assigned_to, rec_code, taxonomies):
    recommendation = Recommendation(
        recommendation_code=rec_code,
        model_id=model.model_id,
        title="Test Recommendation",
        description="Test description",
        priority_id=taxonomies["priority_high"].value_id,
        category_id=taxonomies["category_data"].value_id,
        current_status_id=taxonomies["status_open"].value_id,
        created_by_id=created_by.user_id,
        assigned_to_id=assigned_to.user_id,
        original_target_date=date.today(),
        current_target_date=date.today(),
    )
    db_session.add(recommendation)
    db_session.commit()
    db_session.refresh(recommendation)
    return recommendation


def _create_monitoring_team(db_session, name, members=None):
    team = MonitoringTeam(
        name=name,
        description="Test monitoring team",
        is_active=True,
    )
    db_session.add(team)
    db_session.flush()
    if members:
        team.members = members
    db_session.commit()
    db_session.refresh(team)
    return team


def _create_monitoring_plan(db_session, name, team, data_provider, models):
    plan = MonitoringPlan(
        name=name,
        description="Test plan",
        frequency=MonitoringFrequency.QUARTERLY,
        monitoring_team_id=team.team_id if team else None,
        data_provider_user_id=data_provider.user_id if data_provider else None,
        data_submission_lead_days=10,
        reporting_lead_days=20,
        next_submission_due_date=date.today(),
        next_report_due_date=date.today() + timedelta(days=20),
        is_active=True,
    )
    db_session.add(plan)
    db_session.flush()
    plan.models = models
    db_session.commit()
    db_session.refresh(plan)
    return plan


def _create_monitoring_cycle(db_session, plan, assigned_to=None):
    cycle = MonitoringCycle(
        plan_id=plan.plan_id,
        period_start_date=date.today() - timedelta(days=30),
        period_end_date=date.today(),
        submission_due_date=date.today() + timedelta(days=5),
        report_due_date=date.today() + timedelta(days=15),
        status=MonitoringCycleStatus.PENDING.value,
        assigned_to_user_id=assigned_to.user_id if assigned_to else None,
    )
    db_session.add(cycle)
    db_session.commit()
    db_session.refresh(cycle)
    return cycle


def _create_monitoring_approval(db_session, cycle, approval_type, region=None):
    approval = MonitoringCycleApproval(
        cycle_id=cycle.cycle_id,
        approval_type=approval_type,
        region_id=region.region_id if region else None,
        is_required=True,
        approval_status="Pending",
    )
    db_session.add(approval)
    db_session.commit()
    db_session.refresh(approval)
    return approval


def _create_decommission_reason(db_session):
    taxonomy = Taxonomy(name="Model Decommission Reason", is_system=True)
    db_session.add(taxonomy)
    db_session.flush()
    reason = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="RETIRE",
        label="Retire",
        sort_order=1,
    )
    db_session.add(reason)
    db_session.commit()
    return reason


def _create_decommissioning_request(db_session, model, created_by, reason):
    request = DecommissioningRequest(
        model_id=model.model_id,
        status="PENDING",
        reason_id=reason.value_id,
        last_production_date=date.today(),
        archive_location="s3://archive",
        downstream_impact_verified=False,
        created_by_id=created_by.user_id,
    )
    db_session.add(request)
    db_session.commit()
    db_session.refresh(request)
    return request


def _create_irp(db_session, process_name, contact_user, covered_mrsas):
    irp = IRP(
        process_name=process_name,
        description="Test IRP",
        is_active=True,
        contact_user_id=contact_user.user_id,
    )
    db_session.add(irp)
    db_session.flush()
    if covered_mrsas:
        irp.covered_mrsas = covered_mrsas
    db_session.commit()
    db_session.refresh(irp)
    return irp


def _get_role_id(db_session, role_code):
    return db_session.query(Role).filter(Role.code == role_code).first().role_id


def _headers_for_user(user):
    token = create_access_token(data={"sub": user.email})
    return {"Authorization": f"Bearer {token}"}


def _create_user_with_role(db_session, lob_id, email, full_name, role_code):
    user = User(
        email=email,
        full_name=full_name,
        password_hash=get_password_hash("testpass123"),
        role_id=_get_role_id(db_session, role_code),
        lob_id=lob_id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_region(db_session, code, name):
    region = Region(
        code=code,
        name=name,
        requires_regional_approval=True,
    )
    db_session.add(region)
    db_session.commit()
    db_session.refresh(region)
    return region


def test_rls_list_models_filters_by_access(
    client,
    auth_headers,
    sample_model,
    second_user,
    usage_frequency,
    db_session,
):
    other_model = _create_model(
        db_session,
        owner=second_user,
        usage_frequency=usage_frequency,
        name="Other User Model",
        submitted_by=second_user,
    )

    response = client.get("/models/", headers=auth_headers)
    assert response.status_code == 200

    model_ids = {item["model_id"] for item in response.json()}
    assert sample_model.model_id in model_ids
    assert other_model.model_id not in model_ids


def test_rls_list_exceptions_filters_by_model_access(
    client,
    auth_headers,
    sample_model,
    second_user,
    usage_frequency,
    db_session,
):
    other_model = _create_model(
        db_session,
        owner=second_user,
        usage_frequency=usage_frequency,
        name="Other User Model",
        submitted_by=second_user,
    )

    own_exception = _create_exception(db_session, sample_model, "EXC-2026-00001")
    other_exception = _create_exception(db_session, other_model, "EXC-2026-00002")

    response = client.get("/exceptions/", headers=auth_headers)
    assert response.status_code == 200

    payload = response.json()
    exception_ids = {item["exception_id"] for item in payload["items"]}
    assert own_exception.exception_id in exception_ids
    assert other_exception.exception_id not in exception_ids
    assert payload["total"] == 1


def test_rls_list_validation_requests_filters_by_model_access(
    client,
    auth_headers,
    sample_model,
    second_user,
    usage_frequency,
    taxonomy_values,
    db_session,
):
    other_model = _create_model(
        db_session,
        owner=second_user,
        usage_frequency=usage_frequency,
        name="Other User Model",
        submitted_by=second_user,
    )

    own_request = _create_validation_request(
        db_session,
        model=sample_model,
        requestor=sample_model.owner,
        taxonomy_values=taxonomy_values,
    )
    other_request = _create_validation_request(
        db_session,
        model=other_model,
        requestor=other_model.owner,
        taxonomy_values=taxonomy_values,
    )

    response = client.get("/validation-workflow/requests/", headers=auth_headers)
    assert response.status_code == 200

    request_ids = {item["request_id"] for item in response.json()}
    assert own_request.request_id in request_ids
    assert other_request.request_id not in request_ids


def test_rls_list_recommendations_filters_by_model_access(
    client,
    auth_headers,
    sample_model,
    second_user,
    usage_frequency,
    db_session,
):
    other_model = _create_model(
        db_session,
        owner=second_user,
        usage_frequency=usage_frequency,
        name="Other User Model",
        submitted_by=second_user,
    )
    taxonomies = _create_recommendation_taxonomies(db_session)

    own_rec = _create_recommendation(
        db_session,
        model=sample_model,
        created_by=sample_model.owner,
        assigned_to=sample_model.owner,
        rec_code="REC-2026-00001",
        taxonomies=taxonomies,
    )
    other_rec = _create_recommendation(
        db_session,
        model=other_model,
        created_by=second_user,
        assigned_to=second_user,
        rec_code="REC-2026-00002",
        taxonomies=taxonomies,
    )

    response = client.get("/recommendations/", headers=auth_headers)
    assert response.status_code == 200

    recommendation_ids = {item["recommendation_id"] for item in response.json()}
    assert own_rec.recommendation_id in recommendation_ids
    assert other_rec.recommendation_id not in recommendation_ids


def test_rls_list_monitoring_plans_filters_by_model_access(
    client,
    auth_headers,
    sample_model,
    second_user,
    usage_frequency,
    db_session,
):
    other_model = _create_model(
        db_session,
        owner=second_user,
        usage_frequency=usage_frequency,
        name="Other User Model",
        submitted_by=second_user,
    )
    team = _create_monitoring_team(db_session, "Monitoring Team", members=[second_user])

    accessible_plan = _create_monitoring_plan(
        db_session,
        name="Plan A",
        team=team,
        data_provider=second_user,
        models=[sample_model],
    )
    hidden_plan = _create_monitoring_plan(
        db_session,
        name="Plan B",
        team=team,
        data_provider=second_user,
        models=[other_model],
    )

    response = client.get("/monitoring/plans", headers=auth_headers)
    assert response.status_code == 200

    plan_ids = {item["plan_id"] for item in response.json()}
    assert accessible_plan.plan_id in plan_ids
    assert hidden_plan.plan_id not in plan_ids


def test_rls_monitoring_cycle_access_for_assignee(
    client,
    auth_headers,
    test_user,
    second_user,
    usage_frequency,
    db_session,
):
    other_model = _create_model(
        db_session,
        owner=second_user,
        usage_frequency=usage_frequency,
        name="Other User Model",
        submitted_by=second_user,
    )
    team = _create_monitoring_team(db_session, "Monitoring Team", members=[second_user])
    plan = _create_monitoring_plan(
        db_session,
        name="Assignee Plan",
        team=team,
        data_provider=second_user,
        models=[other_model],
    )
    cycle = _create_monitoring_cycle(db_session, plan, assigned_to=test_user)

    response = client.get(f"/monitoring/cycles/{cycle.cycle_id}", headers=auth_headers)
    assert response.status_code == 200

    response = client.get(f"/monitoring/cycles/{cycle.cycle_id}/results", headers=auth_headers)
    assert response.status_code == 200


def test_rls_monitoring_cycle_approvals_require_access(
    client,
    auth_headers,
    second_user,
    usage_frequency,
    db_session,
):
    other_model = _create_model(
        db_session,
        owner=second_user,
        usage_frequency=usage_frequency,
        name="Approvals Locked Model",
        submitted_by=second_user,
    )
    team = _create_monitoring_team(db_session, "Approvals Team", members=[second_user])
    plan = _create_monitoring_plan(
        db_session,
        name="Approvals Plan",
        team=team,
        data_provider=second_user,
        models=[other_model],
    )
    cycle = _create_monitoring_cycle(db_session, plan)
    _create_monitoring_approval(db_session, cycle, "Global")

    response = client.get(
        f"/monitoring/cycles/{cycle.cycle_id}/approvals", headers=auth_headers
    )
    assert response.status_code == 404

    response = client.get(
        f"/monitoring/cycles/{cycle.cycle_id}/report/pdf", headers=auth_headers
    )
    assert response.status_code == 404


def test_rls_monitoring_cycle_approvals_allows_global_approver(
    client,
    second_user,
    usage_frequency,
    lob_hierarchy,
    db_session,
):
    other_model = _create_model(
        db_session,
        owner=second_user,
        usage_frequency=usage_frequency,
        name="Global Approval Model",
        submitted_by=second_user,
    )
    team = _create_monitoring_team(db_session, "Global Approval Team", members=[second_user])
    plan = _create_monitoring_plan(
        db_session,
        name="Global Approval Plan",
        team=team,
        data_provider=second_user,
        models=[other_model],
    )
    cycle = _create_monitoring_cycle(db_session, plan)
    _create_monitoring_approval(db_session, cycle, "Global")

    approver = _create_user_with_role(
        db_session,
        lob_hierarchy["retail"].lob_id,
        "global-approver@example.com",
        "Global Approver",
        RoleCode.GLOBAL_APPROVER.value,
    )
    headers = _headers_for_user(approver)

    response = client.get(
        f"/monitoring/cycles/{cycle.cycle_id}/approvals", headers=headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get(
        f"/monitoring/cycles/{cycle.cycle_id}/report/pdf", headers=headers
    )
    assert response.status_code == 400


def test_rls_monitoring_cycle_approvals_allows_regional_approver(
    client,
    second_user,
    usage_frequency,
    lob_hierarchy,
    db_session,
):
    other_model = _create_model(
        db_session,
        owner=second_user,
        usage_frequency=usage_frequency,
        name="Regional Approval Model",
        submitted_by=second_user,
    )
    team = _create_monitoring_team(db_session, "Regional Approval Team", members=[second_user])
    plan = _create_monitoring_plan(
        db_session,
        name="Regional Approval Plan",
        team=team,
        data_provider=second_user,
        models=[other_model],
    )
    cycle = _create_monitoring_cycle(db_session, plan)

    region = _create_region(db_session, "NA", "North America")
    _create_monitoring_approval(db_session, cycle, "Regional", region=region)

    approver = _create_user_with_role(
        db_session,
        lob_hierarchy["retail"].lob_id,
        "regional-approver@example.com",
        "Regional Approver",
        RoleCode.REGIONAL_APPROVER.value,
    )
    approver.regions.append(region)
    db_session.commit()

    headers = _headers_for_user(approver)
    response = client.get(
        f"/monitoring/cycles/{cycle.cycle_id}/approvals", headers=headers
    )
    assert response.status_code == 200

def test_rls_decommissioning_filters_by_model_access(
    client,
    auth_headers,
    sample_model,
    second_user,
    usage_frequency,
    db_session,
):
    other_model = _create_model(
        db_session,
        owner=second_user,
        usage_frequency=usage_frequency,
        name="Other User Model",
        submitted_by=second_user,
    )
    reason = _create_decommission_reason(db_session)
    own_request = _create_decommissioning_request(
        db_session,
        model=sample_model,
        created_by=sample_model.owner,
        reason=reason,
    )
    other_request = _create_decommissioning_request(
        db_session,
        model=other_model,
        created_by=second_user,
        reason=reason,
    )

    response = client.get("/decommissioning/", headers=auth_headers)
    assert response.status_code == 200

    request_ids = {item["request_id"] for item in response.json()}
    assert own_request.request_id in request_ids
    assert other_request.request_id not in request_ids

    response = client.get(f"/decommissioning/{other_request.request_id}", headers=auth_headers)
    assert response.status_code == 404


def test_rls_team_models_filters_by_model_access(
    client,
    auth_headers,
    sample_model,
    second_user,
    usage_frequency,
    lob_hierarchy,
    db_session,
):
    other_model = _create_model(
        db_session,
        owner=second_user,
        usage_frequency=usage_frequency,
        name="Other User Model",
        submitted_by=second_user,
    )

    team = Team(name="Coverage Team", description="Test team", is_active=True)
    db_session.add(team)
    db_session.flush()

    lob_hierarchy["retail"].team_id = team.team_id
    lob_hierarchy["credit"].team_id = team.team_id
    db_session.commit()

    response = client.get(f"/teams/{team.team_id}/models", headers=auth_headers)
    assert response.status_code == 200

    model_ids = {item["model_id"] for item in response.json()}
    assert sample_model.model_id in model_ids
    assert other_model.model_id not in model_ids


def test_rls_overdue_revalidation_report_admin_only(
    client,
    auth_headers,
):
    response = client.get("/overdue-revalidation-report/", headers=auth_headers)
    assert response.status_code == 403


def test_rls_irp_list_filters_by_mrsa_access(
    client,
    auth_headers,
    test_user,
    second_user,
    usage_frequency,
    db_session,
):
    accessible_mrsa = _create_mrsa_model(
        db_session,
        owner=test_user,
        usage_frequency=usage_frequency,
        name="Accessible MRSA",
        submitted_by=test_user,
    )
    inaccessible_mrsa = _create_mrsa_model(
        db_session,
        owner=second_user,
        usage_frequency=usage_frequency,
        name="Inaccessible MRSA",
        submitted_by=second_user,
    )
    accessible_irp = _create_irp(
        db_session,
        process_name="Accessible IRP",
        contact_user=test_user,
        covered_mrsas=[accessible_mrsa],
    )
    _create_irp(
        db_session,
        process_name="Inaccessible IRP",
        contact_user=second_user,
        covered_mrsas=[inaccessible_mrsa],
    )

    response = client.get("/irps/", headers=auth_headers)
    assert response.status_code == 200

    irp_ids = {item["irp_id"] for item in response.json()}
    assert accessible_irp.irp_id in irp_ids
    assert len(irp_ids) == 1


def test_rls_irp_detail_filters_mrsas_for_non_privileged(
    client,
    auth_headers,
    test_user,
    second_user,
    usage_frequency,
    db_session,
):
    accessible_mrsa = _create_mrsa_model(
        db_session,
        owner=test_user,
        usage_frequency=usage_frequency,
        name="Accessible MRSA Detail",
        submitted_by=test_user,
    )
    inaccessible_mrsa = _create_mrsa_model(
        db_session,
        owner=second_user,
        usage_frequency=usage_frequency,
        name="Inaccessible MRSA Detail",
        submitted_by=second_user,
    )
    irp = _create_irp(
        db_session,
        process_name="Mixed IRP",
        contact_user=test_user,
        covered_mrsas=[accessible_mrsa, inaccessible_mrsa],
    )

    response = client.get(f"/irps/{irp.irp_id}", headers=auth_headers)
    assert response.status_code == 200

    payload = response.json()
    assert payload["covered_mrsa_count"] == 1
    assert {mrsa["model_id"] for mrsa in payload["covered_mrsas"]} == {accessible_mrsa.model_id}
