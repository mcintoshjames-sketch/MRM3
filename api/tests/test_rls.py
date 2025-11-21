import pytest
from datetime import datetime
from app.models.model import Model
from app.models.model_delegate import ModelDelegate
from app.core.rls import apply_model_rls, can_access_model
from app.models.validation import ValidationRequest, ValidationRequestModelVersion
from app.core.rls import apply_validation_request_rls, can_access_validation_request


def test_admin_can_see_all_models(db_session, admin_user, test_user, second_user):
    """Test that admin users can see all models regardless of ownership."""
    # Create models owned by different users
    model1 = Model(
        model_name="User 1 Model",
        description="Owned by user 1",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id
    )
    model2 = Model(
        model_name="User 2 Model",
        description="Owned by user 2",
        development_type="In-House",
        status="Active",
        owner_id=second_user.user_id
    )
    db_session.add_all([model1, model2])
    db_session.commit()

    # Check list access
    query = db_session.query(Model)
    filtered_query = apply_model_rls(query, admin_user, db_session)
    results = filtered_query.all()

    assert len(results) == 2
    assert model1 in results
    assert model2 in results

    # Check direct access
    assert can_access_model(model1.model_id, admin_user, db_session) is True
    assert can_access_model(model2.model_id, admin_user, db_session) is True


def test_validator_can_see_all_models(db_session, validator_user, test_user, second_user):
    """Test that validator users can see all models."""
    # Create models owned by different users
    model1 = Model(
        model_name="User 1 Model",
        description="Owned by user 1",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id
    )
    model2 = Model(
        model_name="User 2 Model",
        description="Owned by user 2",
        development_type="In-House",
        status="Active",
        owner_id=second_user.user_id
    )
    db_session.add_all([model1, model2])
    db_session.commit()

    # Check list access
    query = db_session.query(Model)
    filtered_query = apply_model_rls(query, validator_user, db_session)
    results = filtered_query.all()

    assert len(results) == 2

    # Check direct access
    assert can_access_model(
        model1.model_id, validator_user, db_session) is True
    assert can_access_model(
        model2.model_id, validator_user, db_session) is True


def test_user_can_see_owned_models(db_session, test_user, second_user):
    """Test that users can see models they own."""
    # Create model owned by test_user
    model = Model(
        model_name="My Model",
        description="Owned by me",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id
    )
    # Create model owned by someone else
    other_model = Model(
        model_name="Other Model",
        description="Not owned by me",
        development_type="In-House",
        status="Active",
        owner_id=second_user.user_id
    )
    db_session.add_all([model, other_model])
    db_session.commit()

    # Check list access
    query = db_session.query(Model)
    filtered_query = apply_model_rls(query, test_user, db_session)
    results = filtered_query.all()

    assert len(results) == 1
    assert results[0].model_id == model.model_id

    # Check direct access
    assert can_access_model(model.model_id, test_user, db_session) is True
    assert can_access_model(other_model.model_id,
                            test_user, db_session) is False


def test_user_can_see_developed_models(db_session, test_user, second_user):
    """Test that users can see models they are the developer for."""
    # Create model developed by test_user (owned by someone else)
    model = Model(
        model_name="Developed Model",
        description="Developed by me",
        development_type="In-House",
        status="Active",
        owner_id=second_user.user_id,
        developer_id=test_user.user_id
    )
    db_session.add(model)
    db_session.commit()

    # Check list access
    query = db_session.query(Model)
    filtered_query = apply_model_rls(query, test_user, db_session)
    results = filtered_query.all()

    assert len(results) == 1
    assert results[0].model_id == model.model_id

    # Check direct access
    assert can_access_model(model.model_id, test_user, db_session) is True


def test_user_can_see_delegated_models(db_session, test_user, second_user):
    """Test that users can see models they are a delegate for."""
    # Create model owned by someone else
    model = Model(
        model_name="Delegated Model",
        description="I am a delegate",
        development_type="In-House",
        status="Active",
        owner_id=second_user.user_id
    )
    db_session.add(model)
    db_session.commit()

    # Add test_user as delegate
    delegate = ModelDelegate(
        model_id=model.model_id,
        user_id=test_user.user_id,
        delegated_by_id=second_user.user_id,
        delegated_at=datetime.utcnow()
    )
    db_session.add(delegate)
    db_session.commit()

    # Check list access
    query = db_session.query(Model)
    filtered_query = apply_model_rls(query, test_user, db_session)
    results = filtered_query.all()

    assert len(results) == 1
    assert results[0].model_id == model.model_id

    # Check direct access
    assert can_access_model(model.model_id, test_user, db_session) is True


def test_user_cannot_see_revoked_delegated_models(db_session, test_user, second_user):
    """Test that users cannot see models where their delegation was revoked."""
    # Create model owned by someone else
    model = Model(
        model_name="Revoked Model",
        description="I was a delegate",
        development_type="In-House",
        status="Active",
        owner_id=second_user.user_id
    )
    db_session.add(model)
    db_session.commit()

    # Add test_user as delegate but revoked
    delegate = ModelDelegate(
        model_id=model.model_id,
        user_id=test_user.user_id,
        delegated_by_id=second_user.user_id,
        delegated_at=datetime.utcnow(),
        revoked_at=datetime.utcnow(),
        revoked_by_id=second_user.user_id
    )
    db_session.add(delegate)
    db_session.commit()

    # Check list access
    query = db_session.query(Model)
    filtered_query = apply_model_rls(query, test_user, db_session)
    results = filtered_query.all()

    assert len(results) == 0

    # Check direct access
    assert can_access_model(model.model_id, test_user, db_session) is False


def test_user_can_see_validation_requests_for_accessible_models(db_session, test_user, second_user, taxonomy_values):
    """Test that users can see validation requests for models they have access to."""
    # Create model owned by test_user
    model = Model(
        model_name="My Model",
        description="Owned by me",
        development_type="In-House",
        status="Active",
        owner_id=test_user.user_id
    )
    db_session.add(model)
    db_session.commit()

    # Create validation request for this model
    val_req = ValidationRequest(
        request_date=datetime.utcnow().date(),
        requestor_id=test_user.user_id,
        validation_type_id=taxonomy_values["initial"].value_id,
        # Using tier1 as priority for simplicity
        priority_id=taxonomy_values["tier1"].value_id,
        # Using initial as status for simplicity
        current_status_id=taxonomy_values["initial"].value_id,
        target_completion_date=datetime.utcnow().date(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(val_req)
    db_session.flush()

    # Link model to validation request
    assoc = ValidationRequestModelVersion(
        request_id=val_req.request_id,
        model_id=model.model_id
    )
    db_session.add(assoc)
    db_session.commit()

    # Check list access
    query = db_session.query(ValidationRequest)
    filtered_query = apply_validation_request_rls(query, test_user, db_session)
    results = filtered_query.all()

    assert len(results) == 1
    assert results[0].request_id == val_req.request_id

    # Check direct access
    assert can_access_validation_request(
        val_req.request_id, test_user, db_session) is True


def test_user_cannot_see_validation_requests_for_inaccessible_models(db_session, test_user, second_user, taxonomy_values):
    """Test that users cannot see validation requests for models they do not have access to."""
    # Create model owned by someone else
    model = Model(
        model_name="Other Model",
        description="Not owned by me",
        development_type="In-House",
        status="Active",
        owner_id=second_user.user_id
    )
    db_session.add(model)
    db_session.commit()

    # Create validation request for this model
    val_req = ValidationRequest(
        request_date=datetime.utcnow().date(),
        requestor_id=second_user.user_id,
        validation_type_id=taxonomy_values["initial"].value_id,
        priority_id=taxonomy_values["tier1"].value_id,
        current_status_id=taxonomy_values["initial"].value_id,
        target_completion_date=datetime.utcnow().date(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(val_req)
    db_session.flush()

    # Link model to validation request
    assoc = ValidationRequestModelVersion(
        request_id=val_req.request_id,
        model_id=model.model_id
    )
    db_session.add(assoc)
    db_session.commit()

    # Check list access
    query = db_session.query(ValidationRequest)
    filtered_query = apply_validation_request_rls(query, test_user, db_session)
    results = filtered_query.all()

    assert len(results) == 0

    # Check direct access
    assert can_access_validation_request(
        val_req.request_id, test_user, db_session) is False
