"""Simple seed for Regional Compliance Report demo."""
from datetime import datetime, timedelta, date
from app.core.database import SessionLocal
from app.core.time import utc_now
from app.models.user import User
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.model_region import ModelRegion
from app.models.region import Region
from app.models.validation import ValidationRequest, ValidationApproval, ValidationRequestModelVersion
from app.models.taxonomy import TaxonomyValue, Taxonomy

db = SessionLocal()

try:
    print("\n" + "="*60)
    print("SEEDING REGIONAL COMPLIANCE REPORT DEMO DATA")
    print("="*60 + "\n")

    # Get required users
    admin = db.query(User).filter(User.email == "admin@example.com").first()
    validator = db.query(User).filter(
        User.email == "validator@example.com").first()
    us_approver = db.query(User).filter(
        User.email == "usapprover@example.com").first()
    eu_approver = db.query(User).filter(
        User.email == "euapprover@example.com").first()

    # Get regions
    us_region = db.query(Region).filter(Region.code == "US").first()
    eu_region = db.query(Region).filter(Region.code == "EU").first()
    uk_region = db.query(Region).filter(Region.code == "UK").first()

    # Get taxonomy values
    val_type_initial = db.query(TaxonomyValue).filter(
        TaxonomyValue.code == "INITIAL").first()
    priority_high = db.query(TaxonomyValue).filter(
        TaxonomyValue.code == "HIGH").first()
    status_approved = db.query(TaxonomyValue).filter(
        TaxonomyValue.code == "APPROVED").first()
    status_pending = db.query(TaxonomyValue).filter(
        TaxonomyValue.code == "PENDING_APPROVAL").first()
    status_in_progress = db.query(TaxonomyValue).filter(
        TaxonomyValue.code == "IN_PROGRESS").first()

    print("✓ Found required users, regions, and taxonomy values\n")

    # ========================================================================
    # SCENARIO 1: Credit Risk Model - v2.1.0 deployed to US (Approved)
    # ========================================================================
    print("Creating Scenario 1: Credit Risk Model")
    print("-" * 60)

    model1 = db.query(Model).filter(Model.model_name ==
                                    "Credit Risk Scorecard v3").first()
    if not model1:
        model1 = Model(
            model_name="Credit Risk Scorecard v3",
            description="Consumer credit risk scoring model",
            development_type="In-House",
            owner_id=admin.user_id,
            developer_id=validator.user_id
        )
        db.add(model1)
        db.commit()
        db.refresh(model1)
        print(f"  ✓ Created model: {model1.model_name}")

    # Create validation request
    val1 = ValidationRequest(
        request_date=date.today() - timedelta(days=60),
        requestor_id=admin.user_id,
        validation_type_id=val_type_initial.value_id,
        priority_id=priority_high.value_id,
        target_completion_date=date.today() - timedelta(days=30),
        current_status_id=status_approved.value_id,
        trigger_reason="Comprehensive validation"
    )
    db.add(val1)
    db.commit()
    db.refresh(val1)

    # Link model to validation
    assoc1 = ValidationRequestModelVersion(
        request_id=val1.request_id,
        model_id=model1.model_id
    )
    db.add(assoc1)

    # Add region to validation
    val1.regions.append(us_region)
    val1.regions.append(eu_region)
    db.commit()

    # Create version linked to validation
    version1 = ModelVersion(
        model_id=model1.model_id,
        version_number="2.1.0",
        validation_request_id=val1.request_id
    )
    db.add(version1)
    db.commit()
    db.refresh(version1)

    # Create US regional approval - APPROVED
    us_appr1 = ValidationApproval(
        request_id=val1.request_id,
        approver_id=us_approver.user_id,
        approver_role="Regional Validator",
        approval_type="Regional",
        region_id=us_region.region_id,
        approval_status="Approved",
        approved_at=utc_now() - timedelta(days=45),
        comments="Approved for US deployment"
    )
    db.add(us_appr1)

    # Create EU regional approval - APPROVED
    eu_appr1 = ValidationApproval(
        request_id=val1.request_id,
        approver_id=eu_approver.user_id,
        approver_role="Regional Validator",
        approval_type="Regional",
        region_id=eu_region.region_id,
        approval_status="Approved",
        approved_at=utc_now() - timedelta(days=44),
        comments="Approved for EU deployment"
    )
    db.add(eu_appr1)
    db.commit()

    # Deploy to US
    us_deploy1 = ModelRegion(
        model_id=model1.model_id,
        region_id=us_region.region_id,
        version_id=version1.version_id,
        deployed_at=utc_now() - timedelta(days=40),
        deployment_notes="Production deployment to US"
    )
    db.add(us_deploy1)

    # Deploy to EU
    eu_deploy1 = ModelRegion(
        model_id=model1.model_id,
        region_id=eu_region.region_id,
        version_id=version1.version_id,
        deployed_at=utc_now() - timedelta(days=38),
        deployment_notes="Production deployment to EU"
    )
    db.add(eu_deploy1)
    db.commit()

    print(f"  ✓ Created validation request (ID: {val1.request_id})")
    print(f"  ✓ Created version 2.1.0")
    print(f"  ✓ US Regional Approval: Approved")
    print(f"  ✓ EU Regional Approval: Approved")
    print(f"  ✓ Deployed to US and EU\n")

    # ========================================================================
    # SCENARIO 2: Market Risk Model - Deployed to US, Pending for UK
    # ========================================================================
    print("Creating Scenario 2: Market Risk Model")
    print("-" * 60)

    model2 = Model(
        model_name="VaR Market Risk Model",
        description="Value-at-Risk model for trading book",
        development_type="In-House",
        owner_id=admin.user_id,
        developer_id=validator.user_id
    )
    db.add(model2)
    db.commit()
    db.refresh(model2)
    print(f"  ✓ Created model: {model2.model_name}")

    # Create validation request
    val2 = ValidationRequest(
        request_date=date.today() - timedelta(days=30),
        requestor_id=admin.user_id,
        validation_type_id=val_type_initial.value_id,
        priority_id=priority_high.value_id,
        target_completion_date=date.today() + timedelta(days=30),
        current_status_id=status_pending.value_id,
        trigger_reason="New model validation"
    )
    db.add(val2)
    db.commit()
    db.refresh(val2)

    # Link model to validation
    assoc2 = ValidationRequestModelVersion(
        request_id=val2.request_id,
        model_id=model2.model_id
    )
    db.add(assoc2)

    # Add regions
    val2.regions.append(us_region)
    val2.regions.append(uk_region)
    db.commit()

    # Create version
    version2 = ModelVersion(
        model_id=model2.model_id,
        version_number="3.0.0",
        validation_request_id=val2.request_id
    )
    db.add(version2)
    db.commit()
    db.refresh(version2)

    # US approval - APPROVED
    us_appr2 = ValidationApproval(
        request_id=val2.request_id,
        approver_id=us_approver.user_id,
        approver_role="Regional Validator",
        approval_type="Regional",
        region_id=us_region.region_id,
        approval_status="Approved",
        approved_at=utc_now() - timedelta(days=7),
        comments="Approved for US deployment"
    )
    db.add(us_appr2)

    # UK approval - PENDING
    uk_appr = ValidationApproval(
        request_id=val2.request_id,
        approver_id=eu_approver.user_id,
        approver_role="Regional Validator",
        approval_type="Regional",
        region_id=uk_region.region_id,
        approval_status="Pending",
        comments="Under review"
    )
    db.add(uk_appr)
    db.commit()

    # Deploy to US only
    us_deploy2 = ModelRegion(
        model_id=model2.model_id,
        region_id=us_region.region_id,
        version_id=version2.version_id,
        deployed_at=utc_now() - timedelta(days=5),
        deployment_notes="Production deployment to US"
    )
    db.add(us_deploy2)

    # Link to UK but no deployment yet
    uk_deploy = ModelRegion(
        model_id=model2.model_id,
        region_id=uk_region.region_id,
        version_id=None,  # Not deployed yet
        deployment_notes="Awaiting approval"
    )
    db.add(uk_deploy)
    db.commit()

    print(f"  ✓ Created validation request (ID: {val2.request_id})")
    print(f"  ✓ Created version 3.0.0")
    print(f"  ✓ US Regional Approval: Approved")
    print(f"  ✓ UK Regional Approval: Pending")
    print(f"  ✓ Deployed to US only\n")

    # ========================================================================
    # SCENARIO 3: CECL Model - Old version deployed, new one being validated
    # ========================================================================
    print("Creating Scenario 3: CECL Model")
    print("-" * 60)

    model3 = Model(
        model_name="CECL Expected Loss Model",
        description="Current Expected Credit Loss model",
        development_type="In-House",
        owner_id=admin.user_id,
        developer_id=validator.user_id
    )
    db.add(model3)
    db.commit()
    db.refresh(model3)
    print(f"  ✓ Created model: {model3.model_name}")

    # Old validation (approved)
    val3_old = ValidationRequest(
        request_date=date.today() - timedelta(days=120),
        requestor_id=admin.user_id,
        validation_type_id=val_type_initial.value_id,
        priority_id=priority_high.value_id,
        target_completion_date=date.today() - timedelta(days=90),
        current_status_id=status_approved.value_id
    )
    db.add(val3_old)
    db.commit()
    db.refresh(val3_old)

    assoc3_old = ValidationRequestModelVersion(
        request_id=val3_old.request_id,
        model_id=model3.model_id
    )
    db.add(assoc3_old)
    val3_old.regions.append(us_region)
    db.commit()

    # Old version
    version3_old = ModelVersion(
        model_id=model3.model_id,
        version_number="1.4.0",
        validation_request_id=val3_old.request_id
    )
    db.add(version3_old)
    db.commit()
    db.refresh(version3_old)

    # Old approval
    us_appr3_old = ValidationApproval(
        request_id=val3_old.request_id,
        approver_id=us_approver.user_id,
        approver_role="Regional Validator",
        approval_type="Regional",
        region_id=us_region.region_id,
        approval_status="Approved",
        approved_at=utc_now() - timedelta(days=100)
    )
    db.add(us_appr3_old)
    db.commit()

    # Deploy old version
    us_deploy3 = ModelRegion(
        model_id=model3.model_id,
        region_id=us_region.region_id,
        version_id=version3_old.version_id,
        deployed_at=utc_now() - timedelta(days=95),
        deployment_notes="Production deployment - older version"
    )
    db.add(us_deploy3)
    db.commit()

    print(f"  ✓ Created old validation (v1.4.0 - Approved and deployed)\n")

    print("=" * 60)
    print("DEMO DATA SEEDING COMPLETE")
    print("=" * 60)
    print("\nTest the report at: /regional-compliance-report/")
    print("  - Filter by US to see 3 models deployed")
    print("  - Filter by EU to see 1 model deployed")
    print("  - Filter by UK to see 0 models deployed (1 pending approval)\n")

except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
