"""Query count checks for report endpoints (PERF-02/03)."""
from contextlib import contextmanager
from datetime import date, datetime, timedelta

from sqlalchemy import event

from app.models.attestation import AttestationCycle, AttestationRecord
from app.models.model import Model
from app.models.model_region import ModelRegion
from app.models.model_version import ModelVersion
from app.models.region import Region


@contextmanager
def count_queries(engine):
    """Count SQL statements executed against the given engine."""
    counter = {"value": 0}

    def before_cursor_execute(*_args, **_kwargs):
        counter["value"] += 1

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield counter
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


def test_regional_compliance_query_count(client, admin_headers, db_session, usage_frequency, admin_user):
    """Regional compliance report should not issue N+1 queries."""
    region = Region(code="US", name="United States", requires_regional_approval=True)
    db_session.add(region)
    db_session.flush()

    model = Model(
        model_name="Compliance Model",
        description="Test model",
        owner_id=admin_user.user_id,
        development_type="In-House",
        status="Active",
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(model)
    db_session.flush()

    version = ModelVersion(
        model_id=model.model_id,
        version_number="1.0",
        change_type="MAJOR",
        change_description="Initial version",
        created_by_id=admin_user.user_id,
        scope="GLOBAL"
    )
    db_session.add(version)
    db_session.flush()

    model_region = ModelRegion(
        model_id=model.model_id,
        region_id=region.region_id,
        version_id=version.version_id,
        deployed_at=datetime.combine(date.today(), datetime.min.time())
    )
    db_session.add(model_region)
    db_session.commit()

    with count_queries(db_session.get_bind()) as counter:
        response = client.get("/regional-compliance-report/", headers=admin_headers)

    assert response.status_code == 200
    assert counter["value"] <= 6


def test_attestation_cycles_query_count(client, admin_headers, db_session, sample_model, admin_user):
    """Attestation cycles list should aggregate in SQL with limited queries."""
    today = date.today()
    cycle = AttestationCycle(
        cycle_name="Q1 Cycle",
        period_start_date=today - timedelta(days=30),
        period_end_date=today,
        submission_due_date=today + timedelta(days=7),
        status="OPEN"
    )
    db_session.add(cycle)
    db_session.flush()

    record = AttestationRecord(
        cycle_id=cycle.cycle_id,
        model_id=sample_model.model_id,
        attesting_user_id=admin_user.user_id,
        due_date=today + timedelta(days=7),
        status="PENDING"
    )
    db_session.add(record)
    db_session.commit()

    with count_queries(db_session.get_bind()) as counter:
        response = client.get("/attestations/cycles?limit=10", headers=admin_headers)

    assert response.status_code == 200
    assert counter["value"] <= 4
