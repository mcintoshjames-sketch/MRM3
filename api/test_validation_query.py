"""
Test script to debug validation request query for model_id 45
"""
from app.core.database import SessionLocal
from app.models.validation import ValidationRequest, ValidationRequestModelVersion
from app.models.taxonomy import TaxonomyValue
from sqlalchemy.orm import joinedload

db = SessionLocal()

try:
    model_id = 45

    print(f"Testing validation request query for model_id {model_id}\n")
    print("=" * 60)

    # First, verify the associations exist
    print("\n1. ValidationRequestModelVersion associations:")
    associations = db.query(ValidationRequestModelVersion).filter(
        ValidationRequestModelVersion.model_id == model_id
    ).all()

    for assoc in associations:
        print(f"  Request ID: {assoc.request_id}, Model ID: {assoc.model_id}, Version ID: {assoc.version_id}")

    print(f"\nTotal associations found: {len(associations)}")

    # Now test the query as it appears in the API endpoint
    print("\n2. Testing the API endpoint query logic:")
    print("-" * 60)

    # This mimics the query from validation_workflow.py
    validation_request_models = ValidationRequestModelVersion.__table__

    query = (
        db.query(ValidationRequest)
        .options(
            joinedload(ValidationRequest.current_status),
            joinedload(ValidationRequest.validation_type),
            joinedload(ValidationRequest.priority),
            joinedload(ValidationRequest.requestor)
        )
        .join(validation_request_models)
        .filter(validation_request_models.c.model_id == model_id)
    )

    results = query.all()

    print(f"\nQuery returned {len(results)} validation requests:")
    for vr in results:
        print(f"\n  Request ID: {vr.request_id}")
        print(f"  Status: {vr.current_status.label if vr.current_status else 'None'}")
        print(f"  Type: {vr.validation_type.label if vr.validation_type else 'None'}")
        print(f"  Priority: {vr.priority.label if vr.priority else 'None'}")
        print(f"  Requestor: {vr.requestor.full_name if vr.requestor else 'None'}")
        print(f"  Request Date: {vr.request_date}")
        print(f"  Created At: {vr.created_at}")

    # Check if there are any validation requests without the join
    print("\n3. All validation requests (without model_id filter):")
    print("-" * 60)
    all_requests = db.query(ValidationRequest).all()
    print(f"Total validation requests in database: {len(all_requests)}")

    # Check if the associations are correctly linked
    print("\n4. Checking request IDs from associations:")
    print("-" * 60)
    request_ids = [assoc.request_id for assoc in associations]
    print(f"Request IDs from associations: {request_ids}")

    for req_id in request_ids:
        vr = db.query(ValidationRequest).filter(ValidationRequest.request_id == req_id).first()
        if vr:
            print(f"  Request {req_id}: EXISTS in ValidationRequest table")
            print(f"    Status ID: {vr.current_status_id}")
            print(f"    Created: {vr.created_at}")
        else:
            print(f"  Request {req_id}: NOT FOUND in ValidationRequest table")

except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
