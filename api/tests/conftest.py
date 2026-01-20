"""Pytest fixtures for API testing."""
import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.core.security import get_password_hash, create_access_token
from app.models.base import Base
from app.models.user import User
from app.models.role import Role
from app.core.roles import RoleCode, ROLE_CODE_TO_DISPLAY
from app.models.model import Model
from app.models.vendor import Vendor
from app.models.model_pending_edit import ModelPendingEdit  # For pending edit workflow tests
from app.models.lob import LOBUnit


# Include KPI test fixtures
pytest_plugins = ["tests.conftest_kpi"]


def _build_sqlite_url(base_dir: Path, worker_id: str) -> tuple[str, Path]:
    db_dir = base_dir / f"sqlite_{worker_id}"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "test.db"
    return f"sqlite:///{db_path}", db_path


@pytest.fixture(scope="session")
def sqlite_engine(tmp_path_factory):
    """Create a per-worker SQLite engine for parallel test isolation."""
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    db_url, db_path = _build_sqlite_url(tmp_path_factory.getbasetemp(), worker_id)
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine
    engine.dispose()
    if db_path.exists():
        db_path.unlink()


@pytest.fixture(scope="session")
def session_factory(sqlite_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)


@pytest.fixture(scope="function")
def db_session(sqlite_engine, session_factory):
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=sqlite_engine)
    db = session_factory()
    for code, display_name in ROLE_CODE_TO_DISPLAY.items():
        db.add(Role(code=code, display_name=display_name, is_system=True, is_active=True))
    db.commit()
    yield db
    db.close()
    Base.metadata.drop_all(bind=sqlite_engine)


@pytest.fixture(scope="session")
def postgres_engine():
    """Create a dedicated Postgres schema for integration tests (if configured)."""
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")

    schema = f"test_{uuid.uuid4().hex}"
    base_engine = create_engine(url)
    with base_engine.connect() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        conn.execute(text(f'SET search_path TO "{schema}"'))
        conn.commit()

    pg_engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    Base.metadata.create_all(bind=pg_engine)

    yield pg_engine

    pg_engine.dispose()
    with base_engine.connect() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        conn.commit()
    base_engine.dispose()


@pytest.fixture(scope="function")
def postgres_db_session(postgres_engine):
    """Fresh Postgres database session per test (schema-local)."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=postgres_engine)
    db = SessionLocal()

    table_names = [table.name for table in Base.metadata.tables.values()]
    if table_names:
        quoted = ", ".join(f'"{name}"' for name in table_names)
        db.execute(text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE"))
        db.commit()

    for code, display_name in ROLE_CODE_TO_DISPLAY.items():
        db.add(Role(code=code, display_name=display_name, is_system=True, is_active=True))
    db.commit()

    yield db

    db.close()


@pytest.fixture(scope="function")
def client(db_session, session_factory):
    """Test client with database override.

    Note: db_session already created tables, so we don't need to create them again.
    """
    def override_get_db():
        try:
            db = session_factory()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def lob_hierarchy(db_session):
    """Create a test LOB hierarchy for testing.

    Note: full_path is a computed property, not stored in DB.
    org_unit format: S#### for synthetic (test) data, 5 digits for real data.
    """
    # Root level: Corporate (synthetic org_unit since it's SBU level)
    corporate = LOBUnit(
        code="CORP",
        name="Corporate",
        org_unit="S0001",  # Synthetic org_unit for SBU
        level=0,
        parent_id=None,
        is_active=True
    )
    db_session.add(corporate)
    db_session.flush()

    # Level 1: Business Units
    retail = LOBUnit(
        code="RET",
        name="Retail Banking",
        org_unit="10001",  # 5-digit org_unit
        level=1,
        parent_id=corporate.lob_id,
        is_active=True
    )
    wholesale = LOBUnit(
        code="WHL",
        name="Wholesale Banking",
        org_unit="10002",  # 5-digit org_unit
        level=1,
        parent_id=corporate.lob_id,
        is_active=True
    )
    db_session.add_all([retail, wholesale])
    db_session.flush()

    # Level 2: Departments under Retail
    credit = LOBUnit(
        code="CRD",
        name="Credit",
        org_unit="20001",  # 5-digit org_unit
        level=2,
        parent_id=retail.lob_id,
        is_active=True
    )
    deposits = LOBUnit(
        code="DEP",
        name="Deposits",
        org_unit="20002",  # 5-digit org_unit
        level=2,
        parent_id=retail.lob_id,
        is_active=True
    )
    db_session.add_all([credit, deposits])
    db_session.commit()

    return {
        "corporate": corporate,
        "retail": retail,
        "wholesale": wholesale,
        "credit": credit,
        "deposits": deposits
    }


@pytest.fixture
def test_user(db_session, lob_hierarchy):
    """Create a test user."""
    role_id = db_session.query(Role).filter(Role.code == RoleCode.USER.value).first().role_id
    user = User(
        email="test@example.com",
        full_name="Test User",
        password_hash=get_password_hash("testpass123"),
        role_id=role_id,
        lob_id=lob_hierarchy["retail"].lob_id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session, lob_hierarchy):
    """Create an admin user."""
    role_id = db_session.query(Role).filter(Role.code == RoleCode.ADMIN.value).first().role_id
    user = User(
        email="admin@example.com",
        full_name="Admin User",
        password_hash=get_password_hash("admin123"),
        role_id=role_id,
        lob_id=lob_hierarchy["corporate"].lob_id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Get authorization headers for test user."""
    token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user):
    """Get authorization headers for admin user."""
    token = create_access_token(data={"sub": admin_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def usage_frequency(db_session):
    """Create usage frequency taxonomy values required for models."""
    from app.models.taxonomy import Taxonomy, TaxonomyValue

    # Create Usage Frequency taxonomy
    freq_tax = Taxonomy(name="Usage Frequency", is_system=True)
    db_session.add(freq_tax)
    db_session.flush()

    # Create frequency values
    daily = TaxonomyValue(taxonomy_id=freq_tax.taxonomy_id, code="DAILY", label="Daily", sort_order=1)
    weekly = TaxonomyValue(taxonomy_id=freq_tax.taxonomy_id, code="WEEKLY", label="Weekly", sort_order=2)
    monthly = TaxonomyValue(taxonomy_id=freq_tax.taxonomy_id, code="MONTHLY", label="Monthly", sort_order=3)

    db_session.add_all([daily, weekly, monthly])
    db_session.commit()

    return {
        "daily": daily,
        "weekly": weekly,
        "monthly": monthly
    }


@pytest.fixture
def sample_model(db_session, test_user, usage_frequency):
    """Create a sample model in pending state (editable by submitter).

    Note: Model is in 'pending' approval state with test_user as submitter.
    This allows test_user to access and modify it via RLS without being in users list.
    """
    model = Model(
        model_name="Test Model",
        description="A test model",
        development_type="In-House",
        status="In Development",
        owner_id=test_user.user_id,
        row_approval_status="Draft",  # Draft models are editable by submitter
        submitted_by_user_id=test_user.user_id,  # test_user is the submitter
        usage_frequency_id=usage_frequency["daily"].value_id  # Required field
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def sample_vendor(db_session):
    """Create a sample vendor."""
    vendor = Vendor(
        name="Test Vendor",
        contact_info="contact@testvendor.com"
    )
    db_session.add(vendor)
    db_session.commit()
    db_session.refresh(vendor)
    return vendor


@pytest.fixture
def second_user(db_session, lob_hierarchy):
    """Create a second test user for developer/user relationships."""
    role_id = db_session.query(Role).filter(Role.code == RoleCode.USER.value).first().role_id
    user = User(
        email="developer@example.com",
        full_name="Developer User",
        password_hash=get_password_hash("devpass123"),
        role_id=role_id,
        lob_id=lob_hierarchy["credit"].lob_id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def second_user_headers(second_user):
    """Get authorization headers for second user."""
    token = create_access_token(data={"sub": second_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def validator_user(db_session, lob_hierarchy):
    """Create a validator user."""
    role_id = db_session.query(Role).filter(Role.code == RoleCode.VALIDATOR.value).first().role_id
    user = User(
        email="validator@example.com",
        full_name="Validator User",
        password_hash=get_password_hash("validator123"),
        role_id=role_id,
        lob_id=lob_hierarchy["wholesale"].lob_id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def validator_headers(validator_user):
    """Get authorization headers for validator user."""
    token = create_access_token(data={"sub": validator_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def risk_tier_taxonomy(db_session):
    """Create Model Risk Tier taxonomy with TIER_1-4 values for risk assessment tests."""
    from app.models.taxonomy import Taxonomy, TaxonomyValue

    taxonomy = Taxonomy(name="Model Risk Tier", is_system=True)
    db_session.add(taxonomy)
    db_session.flush()

    tiers = [
        TaxonomyValue(taxonomy_id=taxonomy.taxonomy_id, code="TIER_1", label="Tier 1 (High)", sort_order=1),
        TaxonomyValue(taxonomy_id=taxonomy.taxonomy_id, code="TIER_2", label="Tier 2 (Medium)", sort_order=2),
        TaxonomyValue(taxonomy_id=taxonomy.taxonomy_id, code="TIER_3", label="Tier 3 (Low)", sort_order=3),
        TaxonomyValue(taxonomy_id=taxonomy.taxonomy_id, code="TIER_4", label="Tier 4 (Very Low)", sort_order=4),
    ]
    db_session.add_all(tiers)
    db_session.commit()

    return {
        "taxonomy": taxonomy,
        "TIER_1": tiers[0],
        "TIER_2": tiers[1],
        "TIER_3": tiers[2],
        "TIER_4": tiers[3],
    }


@pytest.fixture
def taxonomy_values(db_session):
    """Create taxonomy values for validation testing."""
    from app.models.taxonomy import Taxonomy, TaxonomyValue

    # Create taxonomies
    risk_tier_tax = Taxonomy(name="Model Risk Tier", is_system=True)
    val_type_tax = Taxonomy(name="Validation Type", is_system=True)
    outcome_tax = Taxonomy(name="Validation Outcome", is_system=True)
    scope_tax = Taxonomy(name="Validation Scope", is_system=True)
    priority_tax = Taxonomy(name="Validation Priority", is_system=True)
    status_tax = Taxonomy(name="Validation Request Status", is_system=True)

    db_session.add_all([risk_tier_tax, val_type_tax, outcome_tax, scope_tax, priority_tax, status_tax])
    db_session.flush()

    # Create values
    tier1 = TaxonomyValue(taxonomy_id=risk_tier_tax.taxonomy_id, code="TIER_1", label="Tier 1", sort_order=1)
    tier2 = TaxonomyValue(taxonomy_id=risk_tier_tax.taxonomy_id, code="TIER_2", label="Tier 2", sort_order=2)
    initial = TaxonomyValue(taxonomy_id=val_type_tax.taxonomy_id, code="INITIAL", label="Initial", sort_order=1)
    comprehensive = TaxonomyValue(taxonomy_id=val_type_tax.taxonomy_id, code="COMPREHENSIVE", label="Comprehensive", sort_order=2)
    targeted = TaxonomyValue(taxonomy_id=val_type_tax.taxonomy_id, code="TARGETED", label="Targeted", sort_order=3)
    interim = TaxonomyValue(taxonomy_id=val_type_tax.taxonomy_id, code="INTERIM", label="Interim", sort_order=4)
    pass_outcome = TaxonomyValue(taxonomy_id=outcome_tax.taxonomy_id, code="PASS", label="Pass", sort_order=1)
    pass_findings = TaxonomyValue(taxonomy_id=outcome_tax.taxonomy_id, code="PASS_WITH_FINDINGS", label="Pass with Findings", sort_order=2)
    fail_outcome = TaxonomyValue(taxonomy_id=outcome_tax.taxonomy_id, code="FAIL", label="Fail", sort_order=3)
    full_scope = TaxonomyValue(taxonomy_id=scope_tax.taxonomy_id, code="FULL_SCOPE", label="Full Scope", sort_order=1)
    priority_urgent = TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id, code="URGENT", label="Urgent", sort_order=1)
    priority_standard = TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id, code="STANDARD", label="Standard", sort_order=2)
    priority_medium = TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id, code="MEDIUM", label="Medium", sort_order=3)
    priority_high = TaxonomyValue(taxonomy_id=priority_tax.taxonomy_id, code="HIGH", label="High", sort_order=4)
    status_intake = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="INTAKE", label="Intake", sort_order=1)
    status_planning = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="PLANNING", label="Planning", sort_order=2)
    status_in_progress = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="IN_PROGRESS", label="In Progress", sort_order=3)
    status_review = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="REVIEW", label="Review", sort_order=4)
    status_pending_approval = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="PENDING_APPROVAL", label="Pending Approval", sort_order=5)
    status_approved = TaxonomyValue(taxonomy_id=status_tax.taxonomy_id, code="APPROVED", label="Approved", sort_order=6)

    db_session.add_all([
        tier1,
        tier2,
        initial,
        comprehensive,
        targeted,
        interim,
        pass_outcome,
        pass_findings,
        fail_outcome,
        full_scope,
        priority_urgent,
        priority_standard,
        priority_medium,
        priority_high,
        status_intake,
        status_planning,
        status_in_progress,
        status_review,
        status_pending_approval,
        status_approved
    ])
    db_session.commit()

    return {
        "tier1": tier1,
        "tier2": tier2,
        "initial": initial,
        "comprehensive": comprehensive,
        "targeted": targeted,
        "interim": interim,
        "pass": pass_outcome,
        "pass_with_findings": pass_findings,
        "fail": fail_outcome,
        "full_scope": full_scope,
        "priority_urgent": priority_urgent,
        "priority_standard": priority_standard,
        "priority_medium": priority_medium,
        "priority_high": priority_high,
        "status_intake": status_intake,
        "status_planning": status_planning,
        "status_in_progress": status_in_progress,
        "status_review": status_review,
        "status_pending_approval": status_pending_approval,
        "status_approved": status_approved
    }


@pytest.fixture
def methodology_category(db_session):
    """Create a test methodology category with methodologies for testing."""
    from app.models.methodology import MethodologyCategory, Methodology

    category = MethodologyCategory(
        code="TEST_CAT",
        name="Test Category",
        sort_order=1
    )
    db_session.add(category)
    db_session.flush()

    methodology1 = Methodology(
        category_id=category.category_id,
        name="Test Methodology 1",
        description="First test methodology",
        variants="Variant A, Variant B",
        sort_order=1,
        is_active=True
    )
    methodology2 = Methodology(
        category_id=category.category_id,
        name="Test Methodology 2",
        description="Second test methodology",
        sort_order=2,
        is_active=True
    )
    methodology3 = Methodology(
        category_id=category.category_id,
        name="Inactive Methodology",
        description="This methodology is inactive",
        sort_order=3,
        is_active=False
    )
    db_session.add_all([methodology1, methodology2, methodology3])
    db_session.commit()

    return {
        "category": category,
        "methodology1": methodology1,
        "methodology2": methodology2,
        "inactive_methodology": methodology3
    }


@pytest.fixture
def mrsa_risk_level_taxonomy(db_session):
    """Create MRSA Risk Level taxonomy for IRP testing."""
    from app.models.taxonomy import Taxonomy, TaxonomyValue

    taxonomy = Taxonomy(name="MRSA Risk Level", is_system=True)
    db_session.add(taxonomy)
    db_session.flush()

    high_risk = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="HIGH_RISK",
        label="High-Risk",
        description="High-risk MRSA requiring IRP coverage",
        sort_order=1,
        requires_irp=True
    )
    low_risk = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="LOW_RISK",
        label="Low-Risk",
        description="Low-risk MRSA not requiring IRP coverage",
        sort_order=2,
        requires_irp=False
    )
    db_session.add_all([high_risk, low_risk])
    db_session.commit()

    return {
        "taxonomy": taxonomy,
        "high_risk": high_risk,
        "low_risk": low_risk
    }


@pytest.fixture
def irp_outcome_taxonomy(db_session):
    """Create IRP Review Outcome taxonomy for IRP testing."""
    from app.models.taxonomy import Taxonomy, TaxonomyValue

    taxonomy = Taxonomy(name="IRP Review Outcome", is_system=True)
    db_session.add(taxonomy)
    db_session.flush()

    satisfactory = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="SATISFACTORY",
        label="Satisfactory",
        sort_order=1
    )
    conditional = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="CONDITIONALLY_SATISFACTORY",
        label="Conditionally Satisfactory",
        sort_order=2
    )
    not_satisfactory = TaxonomyValue(
        taxonomy_id=taxonomy.taxonomy_id,
        code="NOT_SATISFACTORY",
        label="Not Satisfactory",
        sort_order=3
    )
    db_session.add_all([satisfactory, conditional, not_satisfactory])
    db_session.commit()

    return {
        "taxonomy": taxonomy,
        "satisfactory": satisfactory,
        "conditional": conditional,
        "not_satisfactory": not_satisfactory
    }


@pytest.fixture
def sample_mrsa(db_session, admin_user, usage_frequency, mrsa_risk_level_taxonomy):
    """Create a sample MRSA (Model Risk-Sensitive Application)."""
    mrsa = Model(
        model_name="Test MRSA",
        description="A test MRSA for IRP testing",
        development_type="In-House",
        status="In Development",
        owner_id=admin_user.user_id,
        is_model=False,
        is_mrsa=True,
        mrsa_risk_level_id=mrsa_risk_level_taxonomy["high_risk"].value_id,
        mrsa_risk_rationale="High business impact requiring IRP oversight",
        usage_frequency_id=usage_frequency["daily"].value_id
    )
    db_session.add(mrsa)
    db_session.commit()
    db_session.refresh(mrsa)
    return mrsa


@pytest.fixture
def sample_irp(db_session, admin_user, sample_mrsa):
    """Create a sample IRP covering the sample MRSA."""
    from app.models.irp import IRP

    irp = IRP(
        process_name="Test IRP",
        description="Test Independent Review Process",
        contact_user_id=admin_user.user_id,
        is_active=True
    )
    irp.covered_mrsas = [sample_mrsa]
    db_session.add(irp)
    db_session.commit()
    db_session.refresh(irp)
    return irp
