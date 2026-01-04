"""Tests for My Portfolio report endpoints."""
import pytest
from app.core.security import create_access_token
from app.models.user import User
from app.models.role import Role
from app.core.roles import RoleCode
from app.core.security import get_password_hash


class TestMyPortfolioDeveloperRole:
    """Test that developer role is included in My Portfolio."""

    def test_my_portfolio_includes_developer_models(
        self, client, db_session, test_user, usage_frequency, lob_hierarchy
    ):
        """Developer should see models where they are developer_id."""
        # Create a second user who will be the owner
        user_role_id = db_session.query(Role).filter(
            Role.code == RoleCode.USER.value
        ).first().role_id

        owner_user = User(
            email="owner@example.com",
            full_name="Owner User",
            password_hash=get_password_hash("owner123"),
            role_id=user_role_id,
            lob_id=lob_hierarchy["corporate"].lob_id
        )
        db_session.add(owner_user)
        db_session.commit()
        db_session.refresh(owner_user)

        # Create a model where test_user is developer (not owner)
        from app.models.model import Model
        model = Model(
            model_name="Test Model for Developer",
            description="A model where test_user is developer",
            development_type="In-House",
            status="In Development",
            owner_id=owner_user.user_id,  # Owner is different user
            developer_id=test_user.user_id,  # test_user is developer
            usage_frequency_id=usage_frequency["daily"].value_id,
        )
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)

        # Login as developer (test_user)
        token = create_access_token(data={"sub": test_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        # Get portfolio
        response = client.get("/reports/my-portfolio", headers=headers)
        assert response.status_code == 200

        data = response.json()

        # Verify model appears in portfolio
        assert len(data["models"]) == 1
        portfolio_model = data["models"][0]

        # Verify ownership type is 'developer'
        assert portfolio_model["ownership_type"] == "developer"
        assert portfolio_model["model_id"] == model.model_id
        assert portfolio_model["model_name"] == "Test Model for Developer"

    def test_my_portfolio_developer_precedence(
        self, client, db_session, test_user, usage_frequency, lob_hierarchy
    ):
        """Owner should take precedence over developer when user has both roles."""
        # Create a model where test_user is BOTH owner and developer
        from app.models.model import Model
        model = Model(
            model_name="Test Model Owner and Developer",
            description="A model where test_user is both owner and developer",
            development_type="In-House",
            status="In Development",
            owner_id=test_user.user_id,  # test_user is owner
            developer_id=test_user.user_id,  # test_user is also developer
            usage_frequency_id=usage_frequency["daily"].value_id,
        )
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)

        # Login as test_user
        token = create_access_token(data={"sub": test_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        # Get portfolio
        response = client.get("/reports/my-portfolio", headers=headers)
        assert response.status_code == 200

        data = response.json()

        # Verify model appears in portfolio
        assert len(data["models"]) == 1
        portfolio_model = data["models"][0]

        # Verify ownership type is 'primary' (owner takes precedence)
        assert portfolio_model["ownership_type"] == "primary"
        assert portfolio_model["model_id"] == model.model_id

    def test_my_portfolio_multiple_ownership_types(
        self, client, db_session, test_user, usage_frequency, lob_hierarchy
    ):
        """Portfolio should include models with different ownership types."""
        # Create a second user for ownership scenarios
        user_role_id = db_session.query(Role).filter(
            Role.code == RoleCode.USER.value
        ).first().role_id

        other_user = User(
            email="other@example.com",
            full_name="Other User",
            password_hash=get_password_hash("other123"),
            role_id=user_role_id,
            lob_id=lob_hierarchy["corporate"].lob_id
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        from app.models.model import Model

        # Model 1: test_user is primary owner
        model_owner = Model(
            model_name="Model As Owner",
            description="test_user is owner",
            development_type="In-House",
            status="In Development",
            owner_id=test_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id,
        )
        db_session.add(model_owner)

        # Model 2: test_user is shared owner
        model_shared = Model(
            model_name="Model As Shared Owner",
            description="test_user is shared owner",
            development_type="In-House",
            status="In Development",
            owner_id=other_user.user_id,
            shared_owner_id=test_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id,
        )
        db_session.add(model_shared)

        # Model 3: test_user is developer
        model_developer = Model(
            model_name="Model As Developer",
            description="test_user is developer",
            development_type="In-House",
            status="In Development",
            owner_id=other_user.user_id,
            developer_id=test_user.user_id,
            usage_frequency_id=usage_frequency["daily"].value_id,
        )
        db_session.add(model_developer)

        db_session.commit()

        # Login as test_user
        token = create_access_token(data={"sub": test_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        # Get portfolio
        response = client.get("/reports/my-portfolio", headers=headers)
        assert response.status_code == 200

        data = response.json()

        # Verify all three models appear in portfolio
        assert len(data["models"]) == 3

        # Verify ownership types
        ownership_types = {m["model_name"]: m["ownership_type"]
                           for m in data["models"]}
        assert ownership_types["Model As Owner"] == "primary"
        assert ownership_types["Model As Shared Owner"] == "shared"
        assert ownership_types["Model As Developer"] == "developer"
