#!/usr/bin/env python3
"""Benchmark report endpoints with query counts and latency."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "api"))

from app.core.security import get_password_hash  # noqa: E402
from app.core.roles import ROLE_CODE_TO_DISPLAY, RoleCode  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.attestation import AttestationCycle, AttestationRecord  # noqa: E402
from app.models.lob import LOBUnit  # noqa: E402
from app.models.model import Model  # noqa: E402
from app.models.model_region import ModelRegion  # noqa: E402
from app.models.model_version import ModelVersion  # noqa: E402
from app.models.region import Region  # noqa: E402
from app.models.role import Role  # noqa: E402
from app.models.taxonomy import Taxonomy, TaxonomyValue  # noqa: E402
from app.models.user import User  # noqa: E402
from app.api.kpi_report import get_kpi_report, _KPI_CACHE  # noqa: E402
from app.api.regional_compliance_report import (  # noqa: E402
    get_regional_deployment_compliance_report,
)
from app.api.attestations import list_cycles  # noqa: E402


@contextmanager
def query_counter(engine):
    count = {"value": 0}

    def before_cursor_execute(*_args, **_kwargs):
        count["value"] += 1

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield count
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


def seed_roles(db):
    for code, display_name in ROLE_CODE_TO_DISPLAY.items():
        db.add(Role(code=code, display_name=display_name, is_system=True, is_active=True))
    db.commit()


def seed_lob_and_user(db) -> User:
    lob = LOBUnit(code="LOB1", name="LOB 1", level=1, org_unit="S0001", is_active=True)
    db.add(lob)
    db.flush()

    role = db.query(Role).filter(Role.code == RoleCode.ADMIN.value).first()
    user = User(
        email="bench-admin@example.com",
        full_name="Bench Admin",
        password_hash=get_password_hash("benchpass123"),
        role_id=role.role_id,
        lob_id=lob.lob_id
    )
    db.add(user)
    db.commit()
    return user


def seed_taxonomies(db) -> TaxonomyValue:
    usage = Taxonomy(name="Usage Frequency", is_system=True)
    val_type = Taxonomy(name="Validation Type", is_system=True)
    priority = Taxonomy(name="Validation Priority", is_system=True)
    status = Taxonomy(name="Validation Request Status", is_system=True)
    db.add_all([usage, val_type, priority, status])
    db.flush()

    usage_value = TaxonomyValue(
        taxonomy_id=usage.taxonomy_id,
        code="DAILY",
        label="Daily",
        sort_order=1,
        is_active=True
    )
    db.add_all([
        usage_value,
        TaxonomyValue(
            taxonomy_id=val_type.taxonomy_id,
            code="INITIAL",
            label="Initial",
            sort_order=1,
            is_active=True
        ),
        TaxonomyValue(
            taxonomy_id=priority.taxonomy_id,
            code="STANDARD",
            label="Standard",
            sort_order=1,
            is_active=True
        ),
        TaxonomyValue(
            taxonomy_id=status.taxonomy_id,
            code="INTAKE",
            label="Intake",
            sort_order=1,
            is_active=True
        ),
        TaxonomyValue(
            taxonomy_id=status.taxonomy_id,
            code="APPROVED",
            label="Approved",
            sort_order=2,
            is_active=True
        ),
    ])
    db.commit()
    return usage_value


def seed_regions(db, count: int) -> list[Region]:
    regions = []
    for idx in range(count):
        code = f"R{idx + 1}"
        region = Region(code=code, name=f"Region {idx + 1}", requires_regional_approval=True)
        db.add(region)
        regions.append(region)
    db.commit()
    return regions


def seed_models(db, count: int, owner_id: int, usage_frequency_id: int) -> list[Model]:
    models = []
    for idx in range(count):
        model = Model(
            model_name=f"Bench Model {idx + 1}",
            description="Benchmark model",
            owner_id=owner_id,
            development_type="In-House",
            status="Active",
            usage_frequency_id=usage_frequency_id
        )
        db.add(model)
        models.append(model)
        if idx % 1000 == 0:
            db.flush()
    db.commit()
    return models


def seed_versions_and_deployments(db, models: list[Model], regions: list[Region], created_by_id: int):
    for idx, model in enumerate(models):
        version = ModelVersion(
            model_id=model.model_id,
            version_number=f"1.0.{idx + 1}",
            change_type="MAJOR",
            change_description="Initial version",
            created_by_id=created_by_id,
            scope="GLOBAL"
        )
        db.add(version)
        db.flush()
        region = regions[idx % len(regions)]
        db.add(ModelRegion(
            model_id=model.model_id,
            region_id=region.region_id,
            version_id=version.version_id,
            deployed_at=datetime.combine(date.today(), datetime.min.time())
        ))
        if idx % 1000 == 0:
            db.flush()
    db.commit()


def seed_attestation_cycles(db, models: list[Model], user_id: int, cycles: int, records_per_cycle: int):
    today = date.today()
    model_ids = [model.model_id for model in models]
    for idx in range(cycles):
        cycle = AttestationCycle(
            cycle_name=f"Cycle {idx + 1}",
            period_start_date=today - timedelta(days=90),
            period_end_date=today - timedelta(days=30),
            submission_due_date=today + timedelta(days=7),
            status="OPEN"
        )
        db.add(cycle)
        db.flush()
        for record_idx in range(records_per_cycle):
            model_id = model_ids[(idx + record_idx) % len(model_ids)]
            db.add(AttestationRecord(
                cycle_id=cycle.cycle_id,
                model_id=model_id,
                attesting_user_id=user_id,
                due_date=today + timedelta(days=7),
                status="PENDING"
            ))
        if idx % 200 == 0:
            db.flush()
    db.commit()


def run_report(engine, session_factory, run_fn, runs: int):
    timings = []
    query_counts = []
    for _ in range(runs):
        with session_factory() as db:
            with query_counter(engine) as counter:
                start = time.perf_counter()
                run_fn(db)
                duration_ms = (time.perf_counter() - start) * 1000
            timings.append(duration_ms)
            query_counts.append(counter["value"])
    timings.sort()
    query_counts.sort()
    return {
        "runs": runs,
        "p50_ms": timings[int(len(timings) * 0.5)],
        "p95_ms": timings[max(int(len(timings) * 0.95) - 1, 0)],
        "max_queries": query_counts[-1],
        "min_queries": query_counts[0],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark report endpoints.")
    parser.add_argument("--database-url", help="Database URL for benchmark runs.")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables before seeding.")
    parser.add_argument("--models", type=int, default=10000, help="Number of models to seed.")
    parser.add_argument("--regions", type=int, default=5, help="Number of regions to seed.")
    parser.add_argument("--attestation-cycles", type=int, default=2000, help="Number of attestation cycles to seed.")
    parser.add_argument("--records-per-cycle", type=int, default=10, help="Attestation records per cycle.")
    parser.add_argument("--runs", type=int, default=5, help="Runs per report.")
    args = parser.parse_args()

    database_url = args.database_url or os.getenv("BENCH_DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
    if not database_url:
        print("Missing database URL. Set --database-url or BENCH_DATABASE_URL.", file=sys.stderr)
        return 1

    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    if args.reset:
        if engine.dialect.name == "postgresql":
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = current_schema()")
                )
                tables = [row[0] for row in result]
                for table in tables:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                conn.commit()
            Base.metadata.create_all(bind=engine)
        else:
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        if args.reset:
            seed_roles(db)
            admin_user = seed_lob_and_user(db)
            usage_value = seed_taxonomies(db)
            regions = seed_regions(db, args.regions)
            models = seed_models(db, args.models, admin_user.user_id, usage_value.value_id)
            seed_versions_and_deployments(db, models, regions, admin_user.user_id)
            seed_attestation_cycles(db, models, admin_user.user_id, args.attestation_cycles, args.records_per_cycle)
        else:
            admin_user = db.query(User).first()
            if not admin_user:
                print("No users found; run with --reset to seed data.", file=sys.stderr)
                return 1

    def kpi_runner(db):
        current_user = db.query(User).first()
        return get_kpi_report(db=db, current_user=current_user, region_id=None, team_id=None)

    def compliance_runner(db):
        current_user = db.query(User).first()
        return asyncio.run(get_regional_deployment_compliance_report(
            db=db, current_user=current_user, region_code=None, model_id=None, team_id=None, only_deployed=True
        ))

    def cycles_runner(db):
        current_user = db.query(User).first()
        return list_cycles(db=db, current_user=current_user, status=None, limit=100, offset=0)

    _KPI_CACHE.clear()
    kpi_uncached = run_report(engine, SessionLocal, kpi_runner, args.runs)
    kpi_cached = run_report(engine, SessionLocal, kpi_runner, args.runs)
    compliance_metrics = run_report(engine, SessionLocal, compliance_runner, args.runs)
    cycles_metrics = run_report(engine, SessionLocal, cycles_runner, args.runs)

    output = {
        "dataset": {
            "models": args.models,
            "regions": args.regions,
            "attestation_cycles": args.attestation_cycles,
            "records_per_cycle": args.records_per_cycle,
        },
        "kpi_report": {
            "uncached": kpi_uncached,
            "cached": kpi_cached,
        },
        "regional_compliance_report": compliance_metrics,
        "attestation_cycles": cycles_metrics,
    }

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
