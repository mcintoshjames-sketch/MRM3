"""Tests for Entra user synchronization service."""
import pytest
from datetime import datetime

from app.models.user import User, AzureState, LocalStatus
from app.models.entra_user import EntraUser
from app.core.security import get_password_hash
from app.core.roles import RoleCode
from app.models.role import Role
from app.services.entra_sync import synchronize_user, synchronize_all_users


@pytest.fixture
def entra_user_active(db_session):
    """Create an active Entra user in primary directory."""
    entra_user = EntraUser(
        object_id="active-entra-001",
        user_principal_name="john.doe@contoso.com",
        display_name="John Doe",
        given_name="John",
        surname="Doe",
        mail="john.doe@contoso.com",
        job_title="Developer",
        department="Engineering",
        account_enabled=True,
        in_recycle_bin=False
    )
    db_session.add(entra_user)
    db_session.commit()
    return entra_user


@pytest.fixture
def entra_user_disabled(db_session):
    """Create a disabled Entra user (IT lockout) in primary directory."""
    entra_user = EntraUser(
        object_id="disabled-entra-002",
        user_principal_name="jane.doe@contoso.com",
        display_name="Jane Doe",
        given_name="Jane",
        surname="Doe",
        mail="jane.doe@contoso.com",
        job_title="Analyst",
        department="Finance",
        account_enabled=False,
        in_recycle_bin=False
    )
    db_session.add(entra_user)
    db_session.commit()
    return entra_user


@pytest.fixture
def entra_user_in_recycle_bin(db_session):
    """Create an Entra user in the recycle bin (soft deleted)."""
    deleted_dt = datetime(2024, 1, 15, 10, 30, 0)
    entra_user = EntraUser(
        object_id="recycled-entra-003",
        user_principal_name="bob.smith@contoso.com",
        display_name="Bob Smith",
        given_name="Bob",
        surname="Smith",
        mail="bob.smith@contoso.com",
        job_title="Manager",
        department="Operations",
        account_enabled=True,
        in_recycle_bin=True,
        deleted_datetime=deleted_dt
    )
    db_session.add(entra_user)
    db_session.commit()
    return entra_user


@pytest.fixture
def app_user_with_active_entra(db_session, lob_hierarchy, entra_user_active):
    """Create an app user linked to an active Entra user."""
    role_id = db_session.query(Role).filter(Role.code == RoleCode.USER.value).first().role_id
    user = User(
        email="john.doe@contoso.com",
        full_name="John Doe",
        password_hash=get_password_hash("testpass123"),
        role_id=role_id,
        lob_id=lob_hierarchy["retail"].lob_id,
        azure_object_id=entra_user_active.object_id,
        azure_state=None,  # Not synced yet
        local_status=LocalStatus.ENABLED.value
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def app_user_with_disabled_entra(db_session, lob_hierarchy, entra_user_disabled):
    """Create an app user linked to a disabled Entra user."""
    role_id = db_session.query(Role).filter(Role.code == RoleCode.USER.value).first().role_id
    user = User(
        email="jane.doe@contoso.com",
        full_name="Jane Doe",
        password_hash=get_password_hash("testpass123"),
        role_id=role_id,
        lob_id=lob_hierarchy["retail"].lob_id,
        azure_object_id=entra_user_disabled.object_id,
        azure_state=AzureState.EXISTS.value,  # Was active before
        local_status=LocalStatus.ENABLED.value  # Currently enabled
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def app_user_with_recycled_entra(db_session, lob_hierarchy, entra_user_in_recycle_bin):
    """Create an app user linked to an Entra user in recycle bin."""
    role_id = db_session.query(Role).filter(Role.code == RoleCode.USER.value).first().role_id
    user = User(
        email="bob.smith@contoso.com",
        full_name="Bob Smith",
        password_hash=get_password_hash("testpass123"),
        role_id=role_id,
        lob_id=lob_hierarchy["retail"].lob_id,
        azure_object_id=entra_user_in_recycle_bin.object_id,
        azure_state=AzureState.EXISTS.value,  # Was active before soft delete
        local_status=LocalStatus.ENABLED.value
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def app_user_with_hard_deleted_entra(db_session, lob_hierarchy):
    """Create an app user whose linked Entra user has been hard deleted."""
    role_id = db_session.query(Role).filter(Role.code == RoleCode.USER.value).first().role_id
    user = User(
        email="charlie.gone@contoso.com",
        full_name="Charlie Gone",
        password_hash=get_password_hash("testpass123"),
        role_id=role_id,
        lob_id=lob_hierarchy["retail"].lob_id,
        azure_object_id="hard-deleted-entra-004",  # No EntraUser record exists
        azure_state=AzureState.EXISTS.value,  # Was active before hard delete
        local_status=LocalStatus.ENABLED.value
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def app_user_without_entra(db_session, lob_hierarchy):
    """Create an app user without any Entra linkage."""
    role_id = db_session.query(Role).filter(Role.code == RoleCode.USER.value).first().role_id
    user = User(
        email="local@example.com",
        full_name="Local User",
        password_hash=get_password_hash("testpass123"),
        role_id=role_id,
        lob_id=lob_hierarchy["retail"].lob_id,
        azure_object_id=None,
        azure_state=None,
        local_status=LocalStatus.ENABLED.value
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestSynchronizeUser:
    """Tests for synchronize_user function."""

    def test_scenario_a_active_entra_user(self, db_session, app_user_with_active_entra):
        """Scenario A: Active Entra user -> EXISTS, ENABLED."""
        user_id = app_user_with_active_entra.user_id
        synchronize_user(db_session, user_id)

        # Expire session cache and re-query to verify persistence
        db_session.expire_all()
        user = db_session.query(User).filter(User.user_id == user_id).first()

        assert user.azure_state == AzureState.EXISTS.value
        assert user.local_status == LocalStatus.ENABLED.value
        assert user.azure_deleted_on is None

    def test_scenario_b_it_lockout(self, db_session, app_user_with_disabled_entra):
        """Scenario B: IT Lockout (account_enabled=false) -> EXISTS, DISABLED."""
        user_id = app_user_with_disabled_entra.user_id
        synchronize_user(db_session, user_id)

        # Expire session cache and re-query to verify persistence
        db_session.expire_all()
        user = db_session.query(User).filter(User.user_id == user_id).first()

        assert user.azure_state == AzureState.EXISTS.value
        assert user.local_status == LocalStatus.DISABLED.value
        assert user.azure_deleted_on is None

    def test_scenario_c_soft_delete(self, db_session, app_user_with_recycled_entra, entra_user_in_recycle_bin):
        """Scenario C: Soft deleted (in recycle bin) -> SOFT_DELETED, DISABLED."""
        user_id = app_user_with_recycled_entra.user_id
        expected_deleted_dt = entra_user_in_recycle_bin.deleted_datetime
        synchronize_user(db_session, user_id)

        # Expire session cache and re-query to verify persistence
        db_session.expire_all()
        user = db_session.query(User).filter(User.user_id == user_id).first()

        assert user.azure_state == AzureState.SOFT_DELETED.value
        assert user.local_status == LocalStatus.DISABLED.value
        assert user.azure_deleted_on == expected_deleted_dt

    def test_scenario_d_hard_delete(self, db_session, app_user_with_hard_deleted_entra):
        """Scenario D: Hard deleted (not found) -> NOT_FOUND, DISABLED."""
        user_id = app_user_with_hard_deleted_entra.user_id
        synchronize_user(db_session, user_id)

        # Expire session cache and re-query to verify persistence
        db_session.expire_all()
        user = db_session.query(User).filter(User.user_id == user_id).first()

        assert user.azure_state == AzureState.NOT_FOUND.value
        assert user.local_status == LocalStatus.DISABLED.value

    def test_non_entra_user_skipped(self, db_session, app_user_without_entra):
        """Non-Entra user should be skipped and returned unchanged."""
        user_id = app_user_without_entra.user_id
        original_status = app_user_without_entra.local_status
        synchronize_user(db_session, user_id)

        # Expire session cache and re-query to verify persistence
        db_session.expire_all()
        user = db_session.query(User).filter(User.user_id == user_id).first()

        assert user.azure_object_id is None
        assert user.azure_state is None
        assert user.local_status == original_status

    def test_user_not_found_raises_error(self, db_session):
        """Should raise ValueError if user not found."""
        with pytest.raises(ValueError, match="User not found"):
            synchronize_user(db_session, 999999)

    def test_reactivation_clears_deleted_date(self, db_session, lob_hierarchy, entra_user_in_recycle_bin):
        """When user is restored from recycle bin, azure_deleted_on should be cleared."""
        # First create a user that was soft-deleted
        role_id = db_session.query(Role).filter(Role.code == RoleCode.USER.value).first().role_id
        user = User(
            email="restored@contoso.com",
            full_name="Restored User",
            password_hash=get_password_hash("testpass123"),
            role_id=role_id,
            lob_id=lob_hierarchy["retail"].lob_id,
            azure_object_id=entra_user_in_recycle_bin.object_id,
            azure_state=AzureState.SOFT_DELETED.value,
            local_status=LocalStatus.DISABLED.value,
            azure_deleted_on=entra_user_in_recycle_bin.deleted_datetime
        )
        db_session.add(user)
        db_session.commit()
        user_id = user.user_id

        # Simulate restoration by modifying Entra user
        entra_user_in_recycle_bin.in_recycle_bin = False
        entra_user_in_recycle_bin.deleted_datetime = None
        entra_user_in_recycle_bin.account_enabled = True
        db_session.commit()

        # Sync should update state
        synchronize_user(db_session, user_id)

        # Expire session cache and re-query to verify persistence
        db_session.expire_all()
        synced_user = db_session.query(User).filter(User.user_id == user_id).first()

        assert synced_user.azure_state == AzureState.EXISTS.value
        assert synced_user.local_status == LocalStatus.ENABLED.value
        assert synced_user.azure_deleted_on is None


class TestSynchronizeAllUsers:
    """Tests for synchronize_all_users function."""

    def test_sync_all_returns_correct_counts(
        self,
        db_session,
        app_user_with_active_entra,
        app_user_with_disabled_entra,
        app_user_with_recycled_entra,
        app_user_with_hard_deleted_entra,
        app_user_without_entra
    ):
        """Should return correct counts for each state."""
        results = synchronize_all_users(db_session)

        # Active and disabled are both EXISTS (different local_status)
        assert results["exists"] == 2  # Active + disabled
        assert results["soft_deleted"] == 1  # Recycled
        assert results["not_found"] == 1  # Hard deleted
        assert results["errors"] == 0

        # Verify non-Entra user was not counted
        total = results["exists"] + results["soft_deleted"] + results["not_found"] + results["errors"]
        assert total == 4  # Only Entra-linked users

    def test_sync_all_updates_all_users(
        self,
        db_session,
        app_user_with_active_entra,
        app_user_with_recycled_entra
    ):
        """Should actually update all users' states."""
        # Before sync - clear states
        app_user_with_active_entra.azure_state = None
        app_user_with_recycled_entra.azure_state = None
        db_session.commit()

        synchronize_all_users(db_session)

        # Refresh from DB
        db_session.refresh(app_user_with_active_entra)
        db_session.refresh(app_user_with_recycled_entra)

        assert app_user_with_active_entra.azure_state == AzureState.EXISTS.value
        assert app_user_with_recycled_entra.azure_state == AzureState.SOFT_DELETED.value

    def test_sync_all_with_no_entra_users(self, db_session, app_user_without_entra):
        """Should return zero counts when no Entra-linked users exist."""
        results = synchronize_all_users(db_session)

        assert results["exists"] == 0
        assert results["soft_deleted"] == 0
        assert results["not_found"] == 0
        assert results["errors"] == 0


class TestAuthEnforcement:
    """Tests for authentication enforcement with disabled users."""

    def test_login_disabled_user_returns_403(self, client, lob_hierarchy, db_session):
        """Disabled user should not be able to log in."""
        # Create a disabled user
        role_id = db_session.query(Role).filter(Role.code == RoleCode.USER.value).first().role_id
        user = User(
            email="disabled@example.com",
            full_name="Disabled User",
            password_hash=get_password_hash("testpass123"),
            role_id=role_id,
            lob_id=lob_hierarchy["retail"].lob_id,
            local_status=LocalStatus.DISABLED.value
        )
        db_session.add(user)
        db_session.commit()

        response = client.post(
            "/auth/login",
            json={"email": "disabled@example.com", "password": "testpass123"}
        )

        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()

    def test_api_call_with_disabled_user_returns_403(self, client, lob_hierarchy, db_session):
        """API call with valid token but disabled user should be blocked."""
        from app.core.security import create_access_token

        # Create a user that will be disabled
        role_id = db_session.query(Role).filter(Role.code == RoleCode.USER.value).first().role_id
        user = User(
            email="will.be.disabled@example.com",
            full_name="Will Be Disabled",
            password_hash=get_password_hash("testpass123"),
            role_id=role_id,
            lob_id=lob_hierarchy["retail"].lob_id,
            local_status=LocalStatus.ENABLED.value
        )
        db_session.add(user)
        db_session.commit()

        # Generate token while user is enabled
        token = create_access_token(data={"sub": user.email})
        headers = {"Authorization": f"Bearer {token}"}

        # First verify the token works
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 200

        # Now disable the user
        user.local_status = LocalStatus.DISABLED.value
        db_session.commit()

        # Token should no longer work
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].lower()


class TestEntraHardDeleteFlow:
    """Tests for hard delete flow from Entra directory."""

    def test_hard_delete_marks_app_user_disabled(self, client, admin_headers, db_session, lob_hierarchy):
        """Hard deleting Entra user should mark app user as NOT_FOUND/DISABLED."""
        # Create Entra user
        entra_user = EntraUser(
            object_id="to-be-deleted-001",
            user_principal_name="delete.me@contoso.com",
            display_name="Delete Me",
            given_name="Delete",
            surname="Me",
            mail="delete.me@contoso.com",
            account_enabled=True,
            in_recycle_bin=False
        )
        db_session.add(entra_user)
        db_session.flush()

        # Create app user linked to Entra user
        role_id = db_session.query(Role).filter(Role.code == RoleCode.USER.value).first().role_id
        app_user = User(
            email="delete.me@contoso.com",
            full_name="Delete Me",
            password_hash=get_password_hash("testpass123"),
            role_id=role_id,
            lob_id=lob_hierarchy["retail"].lob_id,
            azure_object_id="to-be-deleted-001",
            azure_state=AzureState.EXISTS.value,
            local_status=LocalStatus.ENABLED.value
        )
        db_session.add(app_user)
        db_session.commit()
        user_id = app_user.user_id

        # Delete the Entra user
        response = client.delete(
            f"/auth/entra/users/to-be-deleted-001",
            headers=admin_headers
        )
        assert response.status_code == 204

        # Verify app user is now marked as NOT_FOUND/DISABLED
        db_session.refresh(app_user)
        assert app_user.azure_state == AzureState.NOT_FOUND.value
        assert app_user.local_status == LocalStatus.DISABLED.value
        assert app_user.azure_deleted_on is not None

        # Verify azure_object_id is preserved (tombstone pattern)
        assert app_user.azure_object_id == "to-be-deleted-001"

    def test_hard_delete_without_app_user_succeeds(self, client, admin_headers, db_session):
        """Hard deleting Entra user without linked app user should succeed."""
        # Create Entra user without app user
        entra_user = EntraUser(
            object_id="unlinked-001",
            user_principal_name="unlinked@contoso.com",
            display_name="Unlinked User",
            given_name="Unlinked",
            surname="User",
            mail="unlinked@contoso.com",
            account_enabled=True,
            in_recycle_bin=False
        )
        db_session.add(entra_user)
        db_session.commit()

        # Delete the Entra user
        response = client.delete(
            f"/auth/entra/users/unlinked-001",
            headers=admin_headers
        )
        assert response.status_code == 204

        # Verify Entra user is deleted
        deleted_user = db_session.query(EntraUser).filter(
            EntraUser.object_id == "unlinked-001"
        ).first()
        assert deleted_user is None


class TestSyncAPIEndpoints:
    """Tests for sync API endpoints."""

    def test_sync_single_user_admin_only(self, client, db_session, auth_headers, admin_headers, app_user_with_active_entra):
        """Single user sync should be admin-only and actually update the user."""
        user_id = app_user_with_active_entra.user_id

        # Clear azure_state to verify it gets set by sync
        app_user_with_active_entra.azure_state = None
        db_session.commit()

        # Non-admin should be rejected
        response = client.post(f"/auth/users/{user_id}/sync-azure", headers=auth_headers)
        assert response.status_code == 403

        # Verify state was NOT updated by failed request
        db_session.expire_all()
        user = db_session.query(User).filter(User.user_id == user_id).first()
        assert user.azure_state is None  # Should still be None

        # Admin should succeed and update state
        response = client.post(f"/auth/users/{user_id}/sync-azure", headers=admin_headers)
        assert response.status_code == 200

        # Verify state WAS updated by successful request
        db_session.expire_all()
        user = db_session.query(User).filter(User.user_id == user_id).first()
        assert user.azure_state == AzureState.EXISTS.value

    def test_sync_all_users_admin_only(
        self,
        client,
        db_session,
        auth_headers,
        admin_headers,
        app_user_with_active_entra,
        app_user_with_recycled_entra
    ):
        """Sync all users should be admin-only with correct counts and state changes."""
        # Clear azure_state on users to verify sync updates them
        app_user_with_active_entra.azure_state = None
        app_user_with_recycled_entra.azure_state = None
        db_session.commit()

        user1_id = app_user_with_active_entra.user_id
        user2_id = app_user_with_recycled_entra.user_id

        # Non-admin should be rejected
        response = client.post("/auth/users/sync-azure-all", headers=auth_headers)
        assert response.status_code == 403

        # Verify states were NOT updated
        db_session.expire_all()
        assert db_session.query(User).filter(User.user_id == user1_id).first().azure_state is None
        assert db_session.query(User).filter(User.user_id == user2_id).first().azure_state is None

        # Admin should succeed
        response = client.post("/auth/users/sync-azure-all", headers=admin_headers)
        assert response.status_code == 200

        # Validate response contains expected counts (not just keys)
        data = response.json()
        assert data["exists"] >= 1  # At least active user
        assert data["soft_deleted"] >= 1  # At least recycled user
        assert data["errors"] == 0
        # Total should match Entra-linked users
        total = data["exists"] + data["soft_deleted"] + data["not_found"]
        assert total >= 2

        # Verify states WERE updated in database
        db_session.expire_all()
        user1 = db_session.query(User).filter(User.user_id == user1_id).first()
        user2 = db_session.query(User).filter(User.user_id == user2_id).first()
        assert user1.azure_state == AzureState.EXISTS.value
        assert user2.azure_state == AzureState.SOFT_DELETED.value

    def test_sync_single_user_returns_updated_user(self, client, admin_headers, db_session, app_user_with_active_entra):
        """Single user sync should return the updated user response and persist changes."""
        user_id = app_user_with_active_entra.user_id

        # Clear state to verify it gets set
        app_user_with_active_entra.azure_state = None
        db_session.commit()

        response = client.post(
            f"/auth/users/{user_id}/sync-azure",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["azure_state"] == AzureState.EXISTS.value
        assert data["local_status"] == LocalStatus.ENABLED.value

        # Verify persistence in database
        db_session.expire_all()
        user = db_session.query(User).filter(User.user_id == user_id).first()
        assert user.azure_state == AzureState.EXISTS.value
        assert user.local_status == LocalStatus.ENABLED.value
