"""Entra user synchronization service.

This service synchronizes user Azure state from the mock Entra directory.
It mimics the Dataverse logic for determining Azure State based on the
user's presence in the primary directory or recycle bin.
"""
from sqlalchemy.orm import Session
from app.models.user import User, AzureState, LocalStatus
from app.models.entra_user import EntraUser


def synchronize_user(db: Session, user_id: int) -> User:
    """
    Sync a user's Azure state from the mock Entra directory.

    Mimics Dataverse logic for determining Azure State:
    1. Check Primary Directory (not in recycle bin) -> EXISTS
    2. Check Recycle Bin -> SOFT_DELETED
    3. Not found anywhere -> NOT_FOUND

    Args:
        db: Database session
        user_id: ID of the user to synchronize

    Returns:
        Updated User object

    Raises:
        ValueError: If user not found
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise ValueError("User not found")

    if not user.azure_object_id:
        # Non-Entra user - skip sync
        return user

    object_id = user.azure_object_id

    # Step 1: Check Primary Directory (not in recycle bin)
    entra_user = db.query(EntraUser).filter(
        EntraUser.object_id == object_id,
        EntraUser.in_recycle_bin == False
    ).first()

    if entra_user:
        user.azure_state = AzureState.EXISTS.value
        # Mirror account_enabled to local_status
        user.local_status = LocalStatus.ENABLED.value if entra_user.account_enabled else LocalStatus.DISABLED.value
        user.azure_deleted_on = None
        db.commit()
        return user

    # Step 2: Check Recycle Bin
    entra_user = db.query(EntraUser).filter(
        EntraUser.object_id == object_id,
        EntraUser.in_recycle_bin == True
    ).first()

    if entra_user:
        user.azure_state = AzureState.SOFT_DELETED.value
        user.local_status = LocalStatus.DISABLED.value
        user.azure_deleted_on = entra_user.deleted_datetime
        db.commit()
        return user

    # Step 3: Hard Deleted (not found anywhere)
    user.azure_state = AzureState.NOT_FOUND.value
    user.local_status = LocalStatus.DISABLED.value
    db.commit()
    return user


def synchronize_all_users(db: Session) -> dict:
    """
    Sync all Entra-linked users.

    Returns:
        Dictionary with summary stats:
        - exists: Count of users found in primary directory
        - soft_deleted: Count of users in recycle bin
        - not_found: Count of users not found (hard deleted)
        - errors: Count of sync errors
    """
    users = db.query(User).filter(User.azure_object_id.isnot(None)).all()
    results = {"exists": 0, "soft_deleted": 0, "not_found": 0, "errors": 0}

    for user in users:
        try:
            result = synchronize_user(db, user.user_id)
            if result.azure_state == AzureState.EXISTS.value:
                results["exists"] += 1
            elif result.azure_state == AzureState.SOFT_DELETED.value:
                results["soft_deleted"] += 1
            elif result.azure_state == AzureState.NOT_FOUND.value:
                results["not_found"] += 1
        except Exception:
            results["errors"] += 1

    return results
