"""Pytest fixtures for API testing."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.core.security import get_password_hash, create_access_token
from app.models.base import Base
from app.models.user import User
from app.models.model import Model
from app.models.vendor import Vendor

# In-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Test client with database override."""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        full_name="Test User",
        password_hash=get_password_hash("testpass123"),
        role="User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session):
    """Create an admin user."""
    user = User(
        email="admin@example.com",
        full_name="Admin User",
        password_hash=get_password_hash("admin123"),
        role="Admin"
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
def sample_model(db_session, test_user):
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
        row_approval_status="pending",  # Pending models are editable by submitter
        submitted_by_user_id=test_user.user_id  # test_user is the submitter
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
def second_user(db_session):
    """Create a second test user for developer/user relationships."""
    user = User(
        email="developer@example.com",
        full_name="Developer User",
        password_hash=get_password_hash("devpass123"),
        role="User"
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
def validator_user(db_session):
    """Create a validator user."""
    user = User(
        email="validator@example.com",
        full_name="Validator User",
        password_hash=get_password_hash("validator123"),
        role="Validator"
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
def taxonomy_values(db_session):
    """Create taxonomy values for validation testing."""
    from app.models.taxonomy import Taxonomy, TaxonomyValue

    # Create taxonomies
    risk_tier_tax = Taxonomy(name="Model Risk Tier", is_system=True)
    val_type_tax = Taxonomy(name="Validation Type", is_system=True)
    outcome_tax = Taxonomy(name="Validation Outcome", is_system=True)
    scope_tax = Taxonomy(name="Validation Scope", is_system=True)

    db_session.add_all([risk_tier_tax, val_type_tax, outcome_tax, scope_tax])
    db_session.flush()

    # Create values
    tier1 = TaxonomyValue(taxonomy_id=risk_tier_tax.taxonomy_id, code="TIER_1", label="Tier 1", sort_order=1)
    tier2 = TaxonomyValue(taxonomy_id=risk_tier_tax.taxonomy_id, code="TIER_2", label="Tier 2", sort_order=2)
    initial = TaxonomyValue(taxonomy_id=val_type_tax.taxonomy_id, code="INITIAL", label="Initial", sort_order=1)
    annual = TaxonomyValue(taxonomy_id=val_type_tax.taxonomy_id, code="ANNUAL", label="Annual Review", sort_order=2)
    pass_outcome = TaxonomyValue(taxonomy_id=outcome_tax.taxonomy_id, code="PASS", label="Pass", sort_order=1)
    pass_findings = TaxonomyValue(taxonomy_id=outcome_tax.taxonomy_id, code="PASS_WITH_FINDINGS", label="Pass with Findings", sort_order=2)
    fail_outcome = TaxonomyValue(taxonomy_id=outcome_tax.taxonomy_id, code="FAIL", label="Fail", sort_order=3)
    full_scope = TaxonomyValue(taxonomy_id=scope_tax.taxonomy_id, code="FULL_SCOPE", label="Full Scope", sort_order=1)

    db_session.add_all([tier1, tier2, initial, annual, pass_outcome, pass_findings, fail_outcome, full_scope])
    db_session.commit()

    return {
        "tier1": tier1,
        "tier2": tier2,
        "initial": initial,
        "annual": annual,
        "pass": pass_outcome,
        "pass_with_findings": pass_findings,
        "fail": fail_outcome,
        "full_scope": full_scope
    }
