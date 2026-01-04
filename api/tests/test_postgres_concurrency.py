"""Postgres-backed concurrency tests for validation requests (DATA-01)."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

from app.core.security import get_password_hash
from app.models.lob import LOBUnit
from app.models.model import Model
from app.models.taxonomy import Taxonomy, TaxonomyValue
from app.models.user import User
from app.models.validation import ValidationRequestModelVersion
from app.schemas.validation import ValidationRequestCreate
from app.api.validation_workflow import create_validation_request
from app.core.roles import RoleCode
from app.models.role import Role


def _seed_usage_frequency(db) -> TaxonomyValue:
    taxonomy = Taxonomy(name="Usage Frequency", is_system=True)
    db.add(taxonomy)
    db.flush()
    value = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="DAILY",
        label="Daily",
        sort_order=1,
        is_active=True
    )
    db.add(value)
    db.commit()
    return value


def _seed_validation_taxonomies(db) -> dict[str, TaxonomyValue]:
    val_type = Taxonomy(name="Validation Type", is_system=True)
    priority = Taxonomy(name="Validation Priority", is_system=True)
    status = Taxonomy(name="Validation Request Status", is_system=True)
    db.add_all([val_type, priority, status])
    db.flush()

    initial = TaxonomyValue(
        taxonomy_id=val_type.taxonomy_id,
        code="INITIAL",
        label="Initial",
        sort_order=1,
        is_active=True
    )
    standard = TaxonomyValue(
        taxonomy_id=priority.taxonomy_id,
        code="STANDARD",
        label="Standard",
        sort_order=1,
        is_active=True
    )
    intake = TaxonomyValue(
        taxonomy_id=status.taxonomy_id,
        code="INTAKE",
        label="Intake",
        sort_order=1,
        is_active=True
    )
    approved = TaxonomyValue(
        taxonomy_id=status.taxonomy_id,
        code="APPROVED",
        label="Approved",
        sort_order=2,
        is_active=True
    )
    cancelled = TaxonomyValue(
        taxonomy_id=status.taxonomy_id,
        code="CANCELLED",
        label="Cancelled",
        sort_order=3,
        is_active=True
    )
    db.add_all([initial, standard, intake, approved, cancelled])
    db.commit()
    return {
        "initial": initial,
        "standard": standard,
    }


@pytest.mark.postgres
def test_validation_request_concurrency_locking(postgres_db_session, postgres_engine):
    """Parallel requests should not create overlapping active validations."""
    role = postgres_db_session.query(Role).filter(
        Role.code == RoleCode.USER.value
    ).first()

    lob = LOBUnit(
        code="LOB1",
        name="LOB 1",
        level=1,
        org_unit="S0001",
        is_active=True
    )
    postgres_db_session.add(lob)
    postgres_db_session.flush()

    user = User(
        email="concurrency@example.com",
        full_name="Concurrency User",
        password_hash=get_password_hash("testpass123"),
        role_id=role.role_id,
        lob_id=lob.lob_id
    )
    postgres_db_session.add(user)
    postgres_db_session.flush()

    usage_frequency = _seed_usage_frequency(postgres_db_session)
    taxonomy_values = _seed_validation_taxonomies(postgres_db_session)

    model = Model(
        model_name="Concurrent Model",
        description="Test model",
        owner_id=user.user_id,
        development_type="In-House",
        usage_frequency_id=usage_frequency.value_id
    )
    postgres_db_session.add(model)
    postgres_db_session.commit()

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=postgres_engine)
    barrier = Barrier(5)

    def worker():
        session = SessionLocal()
        try:
            current_user = session.query(User).filter(
                User.email == user.email
            ).first()
            request_data = ValidationRequestCreate(
                model_ids=[model.model_id],
                validation_type_id=taxonomy_values["initial"].value_id,
                priority_id=taxonomy_values["standard"].value_id,
                target_completion_date=date.today() + timedelta(days=90),
                force_create=True
            )
            barrier.wait()
            result = create_validation_request(
                request_data=request_data,
                db=session,
                current_user=current_user
            )
            return ("success", result.request_id)
        except HTTPException as exc:
            return ("error", exc.detail)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(lambda _: worker(), range(5)))

    successes = [r for r in results if r[0] == "success"]
    assert len(successes) == 1

    created = postgres_db_session.query(ValidationRequestModelVersion).filter(
        ValidationRequestModelVersion.model_id == model.model_id
    ).count()
    assert created == 1
