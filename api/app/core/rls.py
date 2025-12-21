"""Row-Level Security (RLS) filters for data access control."""
from sqlalchemy.orm import Session, Query
from sqlalchemy import or_
from app.models.user import User
from app.models.model import Model
from app.models.model_delegate import ModelDelegate
from app.models.validation import ValidationRequest, ValidationRequestModelVersion
from app.models.model_exception import ModelException


def can_see_all_data(user: User) -> bool:
    """
    Determine if a user can see all data without restrictions.

    These roles have full visibility:
    - Admin
    - Validator (needs to see all models for validation assignments)
    - Global Approver
    - Regional Approver
    """
    privileged_roles = ['Admin', 'Validator',
                        'Global Approver', 'Regional Approver']
    return user.role in privileged_roles


def apply_model_rls(query: Query, user: User, db: Session) -> Query:
    """
    Apply Row-Level Security to model queries.

    Users with "User" role can only see models where they are:
    - Owner/Developer/Delegate AND model is approved (row_approval_status IS NULL), OR
    - Submitter of Draft/needs_revision models (submitted_by_user_id == user_id)

    All other roles (Admin, Validator, Global Approver, Regional Approver) see all models.
    """
    if can_see_all_data(user):
        return query

    # For "User" role, filter to:
    # 1. Approved models they have access to (row_approval_status IS NULL)
    # 2. Their own submissions regardless of approval status
    return query.filter(
        or_(
            # Approved models where user is owner/developer/shared owner/shared developer/delegate
            (
                (Model.row_approval_status == None) &
                or_(
                    Model.owner_id == user.user_id,
                    Model.developer_id == user.user_id,
                    Model.shared_owner_id == user.user_id,
                    Model.shared_developer_id == user.user_id,
                    Model.delegates.any(
                        (ModelDelegate.user_id == user.user_id) &
                        (ModelDelegate.revoked_at == None)
                    )
                )
            ),
            # User's own submissions (Draft, needs_revision, rejected)
            Model.submitted_by_user_id == user.user_id
        )
    )


def apply_validation_request_rls(query: Query, user: User, db: Session) -> Query:
    """
    Apply Row-Level Security to validation request queries.

    Users with "User" role can only see validation requests for models they have access to.
    This is determined by checking access to the associated models.
    """
    if can_see_all_data(user):
        return query

    # For "User" role, filter to only validation requests for models they have access to
    # Need to join through ValidationRequestModelVersion to Model
    return query.join(
        ValidationRequestModelVersion,
        ValidationRequest.request_id == ValidationRequestModelVersion.request_id
    ).join(
        Model,
        ValidationRequestModelVersion.model_id == Model.model_id
    ).filter(
        or_(
            Model.owner_id == user.user_id,
            Model.developer_id == user.user_id,
            Model.shared_owner_id == user.user_id,
            Model.shared_developer_id == user.user_id,
            Model.delegates.any(
                (ModelDelegate.user_id == user.user_id) &
                (ModelDelegate.revoked_at == None)
            )
        )
    ).distinct()


def can_access_model(model_id: int, user: User, db: Session) -> bool:
    """
    Check if a user can access a specific model.

    Returns True if:
    - User has a privileged role (Admin, Validator, Global Approver, Regional Approver), OR
    - Model is approved (row_approval_status IS NULL) AND user is owner/developer/active delegate, OR
    - User is the submitter of the model (regardless of approval status)
    """
    if can_see_all_data(user):
        return True

    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        return False

    # User can always see their own submissions
    if model.submitted_by_user_id == user.user_id:
        return True

    # For approved models only, check ownership/developer/delegate
    if model.row_approval_status is not None:
        # Model is Draft/needs_revision/rejected - only submitter can see
        return False

    # Check if user is owner, developer, shared owner, or shared developer
    if model.owner_id == user.user_id or model.developer_id == user.user_id:
        return True
    if model.shared_owner_id == user.user_id or model.shared_developer_id == user.user_id:
        return True

    # Check if user is an active delegate
    delegate = db.query(ModelDelegate).filter(
        ModelDelegate.model_id == model_id,
        ModelDelegate.user_id == user.user_id,
        ModelDelegate.revoked_at == None
    ).first()

    return delegate is not None


def can_access_validation_request(request_id: int, user: User, db: Session) -> bool:
    """
    Check if a user can access a specific validation request.

    Access is granted if user can access any of the models in the validation request.
    """
    if can_see_all_data(user):
        return True

    # Get model IDs from validation request
    model_versions = db.query(ValidationRequestModelVersion).filter(
        ValidationRequestModelVersion.request_id == request_id
    ).all()

    # Check if user has access to any of the models
    for mv in model_versions:
        if can_access_model(mv.model_id, user, db):
            return True

    return False


def can_modify_model(model_id: int, user: User, db: Session) -> bool:
    """
    Check if a user can modify (update/delete) a specific model.

    Modification is allowed if:
    - User is an Admin, OR
    - Model is approved (row_approval_status IS NULL) AND user is owner/developer/delegate, OR
    - Model is Draft/needs_revision AND user is the submitter
    """
    # Admin can always modify
    if user.role == "Admin":
        return True

    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        return False

    # Submitter can edit Draft/needs_revision models
    if model.row_approval_status in ('Draft', 'needs_revision'):
        return model.submitted_by_user_id == user.user_id

    # For approved models (row_approval_status IS NULL), check standard permissions
    if model.row_approval_status is None:
        # Check if user is owner, developer, shared owner, or shared developer
        if model.owner_id == user.user_id or model.developer_id == user.user_id:
            return True
        if model.shared_owner_id == user.user_id or model.shared_developer_id == user.user_id:
            return True

        # Check if user is an active delegate with can_submit_changes permission
        delegate = db.query(ModelDelegate).filter(
            ModelDelegate.model_id == model_id,
            ModelDelegate.user_id == user.user_id,
            ModelDelegate.revoked_at == None,
            ModelDelegate.can_submit_changes == True
        ).first()

        return delegate is not None

    # Rejected models cannot be edited (must be deleted and recreated)
    return False


def can_see_recommendation(user: User, recommendation, db: Session) -> bool:
    """
    Check if a user can see a specific recommendation.

    Visibility rules:
    - Validation team (Admin, Validator, Global Approver, Regional Approver) can see all
    - DRAFT recommendations are hidden from non-validation team users
    - Other status: user must have access to the associated model OR be the assigned_to user
    """
    # Validation team can see everything
    if can_see_all_data(user):
        return True

    # Get the recommendation's status code
    from app.models import TaxonomyValue
    status = db.query(TaxonomyValue).filter(
        TaxonomyValue.value_id == recommendation.current_status_id
    ).first()

    # DRAFT recommendations are not visible to non-validation team users
    if status and status.code == "REC_DRAFT":
        return False

    # For other statuses, check if user is assigned_to OR has model access
    if recommendation.assigned_to_id == user.user_id:
        return True

    return can_access_model(recommendation.model_id, user, db)


def apply_exception_rls(query: Query, user: User, db: Session) -> Query:
    """
    Apply Row-Level Security to model exception queries.

    Users with "User" role can only see exceptions for models they have access to.
    All other roles (Admin, Validator, Global Approver, Regional Approver) see all exceptions.
    """
    if can_see_all_data(user):
        return query

    # For "User" role, filter to only exceptions for models they have access to
    return query.join(
        Model,
        ModelException.model_id == Model.model_id
    ).filter(
        or_(
            # Approved models where user is owner/developer/shared owner/shared developer/delegate
            (
                (Model.row_approval_status == None) &
                or_(
                    Model.owner_id == user.user_id,
                    Model.developer_id == user.user_id,
                    Model.shared_owner_id == user.user_id,
                    Model.shared_developer_id == user.user_id,
                    Model.delegates.any(
                        (ModelDelegate.user_id == user.user_id) &
                        (ModelDelegate.revoked_at == None)
                    )
                )
            ),
            # User's own submissions (Draft, needs_revision, rejected)
            Model.submitted_by_user_id == user.user_id
        )
    )


def can_access_exception(exception_id: int, user: User, db: Session) -> bool:
    """
    Check if a user can access a specific model exception.

    Access is granted if user can access the exception's associated model.
    """
    if can_see_all_data(user):
        return True

    exception = db.query(ModelException).filter(
        ModelException.exception_id == exception_id
    ).first()

    if not exception:
        return False

    return can_access_model(exception.model_id, user, db)


def is_owner_or_delegate_with_permission(
    model_id: int,
    user: User,
    db: Session,
    permission: str
) -> bool:
    """
    Check if a user is the model owner OR an active delegate with a specific permission.

    Args:
        model_id: The model ID to check
        user: The current user
        db: Database session
        permission: The delegate permission to check ('can_submit_changes', 'can_manage_regional', 'can_attest')

    Returns:
        True if user is Admin, model owner, or delegate with the specified permission
    """
    # Admin can always act
    if user.role == "Admin":
        return True

    model = db.query(Model).filter(Model.model_id == model_id).first()
    if not model:
        return False

    # Check if user is the model owner
    if model.owner_id == user.user_id:
        return True

    # Check if user is an active delegate with the specified permission
    delegate_query = db.query(ModelDelegate).filter(
        ModelDelegate.model_id == model_id,
        ModelDelegate.user_id == user.user_id,
        ModelDelegate.revoked_at == None
    )

    # Apply the specific permission filter
    if permission == 'can_submit_changes':
        delegate_query = delegate_query.filter(ModelDelegate.can_submit_changes == True)
    elif permission == 'can_manage_regional':
        delegate_query = delegate_query.filter(ModelDelegate.can_manage_regional == True)
    elif permission == 'can_attest':
        delegate_query = delegate_query.filter(ModelDelegate.can_attest == True)
    else:
        # Unknown permission, deny access
        return False

    return delegate_query.first() is not None


def can_manage_model_region(model_id: int, user: User, db: Session) -> bool:
    """
    Check if a user can manage regional metadata for a specific model.

    Access is granted if:
    - User is Admin, OR
    - User is the model owner, OR
    - User is an active delegate with can_manage_regional=True
    """
    return is_owner_or_delegate_with_permission(model_id, user, db, 'can_manage_regional')


def can_submit_owner_actions(model_id: int, user: User, db: Session) -> bool:
    """
    Check if a user can perform owner-level actions (like decommissioning review).

    Access is granted if:
    - User is Admin, OR
    - User is the model owner, OR
    - User is an active delegate with can_submit_changes=True
    """
    return is_owner_or_delegate_with_permission(model_id, user, db, 'can_submit_changes')
