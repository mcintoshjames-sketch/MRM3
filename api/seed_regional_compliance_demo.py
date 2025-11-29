"""
Seed data for Regional Compliance Report demonstration.

This script creates:
- Sample models
- Model versions
- Regional deployments (model_regions)
- Validation requests for those versions
- Regional approvals with proper region_id and approval_type fields

Run this script to populate test data for the Regional Compliance Report.
"""
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.core.time import utc_now
from app.models.user import User
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.model_region import ModelRegion
from app.models.region import Region
from app.models.validation import ValidationRequest, ValidationApproval, ValidationRequestModelVersion
from app.models.taxonomy import TaxonomyValue


def seed_regional_compliance_demo():
    """Seed demonstration data for regional compliance report."""
    db = SessionLocal()

    try:
        print("\n" + "="*60)
        print("SEEDING REGIONAL COMPLIANCE REPORT DEMO DATA")
        print("="*60 + "\n")

        # Get required users
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        validator = db.query(User).filter(User.email == "validator@example.com").first()
        us_approver = db.query(User).filter(User.email == "usapprover@example.com").first()
        eu_approver = db.query(User).filter(User.email == "euapprover@example.com").first()

        if not all([admin, validator, us_approver, eu_approver]):
            print("❌ ERROR: Required users not found. Run main seed script first.")
            return

        # Get regions
        us_region = db.query(Region).filter(Region.code == "US").first()
        eu_region = db.query(Region).filter(Region.code == "EU").first()
        uk_region = db.query(Region).filter(Region.code == "UK").first()
        apac_region = db.query(Region).filter(Region.code == "APAC").first()

        if not all([us_region, eu_region, uk_region, apac_region]):
            print("❌ ERROR: Required regions not found. Run main seed script first.")
            return

        # Get validation status taxonomy values
        status_approved = db.query(TaxonomyValue).filter(
            TaxonomyValue.code == "APPROVED"
        ).first()
        status_pending = db.query(TaxonomyValue).filter(
            TaxonomyValue.code == "PENDING_APPROVAL"
        ).first()
        status_in_progress = db.query(TaxonomyValue).filter(
            TaxonomyValue.code == "IN_PROGRESS"
        ).first()

        print("✓ Found required users and regions\n")

        # ========================================================================
        # SCENARIO 1: Credit Risk Model - Deployed to US and EU
        # ========================================================================
        print("Creating Scenario 1: Credit Risk Model")
        print("-" * 60)

        model1 = db.query(Model).filter(Model.model_name == "Credit Risk Scorecard v3").first()
        if not model1:
            model1 = Model(
                model_name="Credit Risk Scorecard v3",
                description="Consumer credit risk scoring model for loan origination",
                development_type="In-House",
                owner_id=admin.user_id,
                developer_id=validator.user_id,
                created_at=utc_now() - timedelta(days=180)
            )
            db.add(model1)
            db.commit()
            db.refresh(model1)
            print(f"  ✓ Created model: {model1.model_name} (ID: {model1.model_id})")
        else:
            print(f"  ✓ Model already exists: {model1.model_name} (ID: {model1.model_id})")

        # Version 2.1.0 - Validated and deployed to US (Approved)
        version_210 = db.query(ModelVersion).filter(
            ModelVersion.model_id == model1.model_id,
            ModelVersion.version_number == "2.1.0"
        ).first()

        if not version_210:
            # Create validation request for v2.1.0
            validation_210 = ValidationRequest(
                model_id=model1.model_id,
                current_status_id=status_approved.value_id if status_approved else None,
                created_at=utc_now() - timedelta(days=60),
                updated_at=utc_now() - timedelta(days=45)
            )
            db.add(validation_210)
            db.commit()
            db.refresh(validation_210)

            # Add US and EU regions to validation
            validation_210.regions.append(us_region)
            validation_210.regions.append(eu_region)
            db.commit()

            # Create version
            version_210 = ModelVersion(
                model_id=model1.model_id,
                version_number="2.1.0",
                validation_request_id=validation_210.request_id,
                created_at=utc_now() - timedelta(days=60)
            )
            db.add(version_210)
            db.commit()
            db.refresh(version_210)

            # Create US regional approval - APPROVED
            us_approval = ValidationApproval(
                request_id=validation_210.request_id,
                approver_id=us_approver.user_id,
                approver_role="Regional Validator",
                approval_type="Regional",
                region_id=us_region.region_id,
                approval_status="Approved",
                approved_at=utc_now() - timedelta(days=45),
                comments="Approved for US deployment. All validation checks passed."
            )
            db.add(us_approval)

            # Create EU regional approval - APPROVED
            eu_approval = ValidationApproval(
                request_id=validation_210.request_id,
                approver_id=eu_approver.user_id,
                approver_role="Regional Validator",
                approval_type="Regional",
                region_id=eu_region.region_id,
                approval_status="Approved",
                approved_at=utc_now() - timedelta(days=44),
                comments="Approved for EU deployment. Meets regulatory requirements."
            )
            db.add(eu_approval)
            db.commit()

            print(f"  ✓ Created version 2.1.0 with validation request (ID: {validation_210.request_id})")
            print(f"    - US Regional Approval: Approved")
            print(f"    - EU Regional Approval: Approved")
        else:
            print(f"  ✓ Version 2.1.0 already exists")

        # Deploy version 2.1.0 to US
        us_deployment = db.query(ModelRegion).filter(
            ModelRegion.model_id == model1.model_id,
            ModelRegion.region_id == us_region.region_id
        ).first()

        if not us_deployment:
            us_deployment = ModelRegion(
                model_id=model1.model_id,
                region_id=us_region.region_id,
                version_id=version_210.version_id,
                deployed_at=utc_now() - timedelta(days=40),
                deployment_notes="Production deployment - US region"
            )
            db.add(us_deployment)
            print(f"  ✓ Deployed v2.1.0 to US region")
        else:
            us_deployment.version_id = version_210.version_id
            us_deployment.deployed_at = utc_now() - timedelta(days=40)
            print(f"  ✓ Updated US deployment to v2.1.0")

        # Deploy version 2.1.0 to EU
        eu_deployment = db.query(ModelRegion).filter(
            ModelRegion.model_id == model1.model_id,
            ModelRegion.region_id == eu_region.region_id
        ).first()

        if not eu_deployment:
            eu_deployment = ModelRegion(
                model_id=model1.model_id,
                region_id=eu_region.region_id,
                version_id=version_210.version_id,
                deployed_at=utc_now() - timedelta(days=38),
                deployment_notes="Production deployment - EU region"
            )
            db.add(eu_deployment)
            print(f"  ✓ Deployed v2.1.0 to EU region")
        else:
            eu_deployment.version_id = version_210.version_id
            eu_deployment.deployed_at = utc_now() - timedelta(days=38)
            print(f"  ✓ Updated EU deployment to v2.1.0")

        db.commit()
        print()

        # ========================================================================
        # SCENARIO 2: Market Risk Model - Deployed to US, Pending approval for UK
        # ========================================================================
        print("Creating Scenario 2: Market Risk Model")
        print("-" * 60)

        model2 = db.query(Model).filter(Model.model_name == "VaR Market Risk Model").first()
        if not model2:
            model2 = Model(
                model_name="VaR Market Risk Model",
                description="Value-at-Risk model for trading book capital",
                development_type="In-House",
                owner_id=admin.user_id,
                developer_id=validator.user_id,
                created_at=utc_now() - timedelta(days=120)
            )
            db.add(model2)
            db.commit()
            db.refresh(model2)
            print(f"  ✓ Created model: {model2.model_name} (ID: {model2.model_id})")
        else:
            print(f"  ✓ Model already exists: {model2.model_name} (ID: {model2.model_id})")

        # Version 3.0.0 - Deployed to US (Approved), Pending for UK
        version_300 = db.query(ModelVersion).filter(
            ModelVersion.model_id == model2.model_id,
            ModelVersion.version_number == "3.0.0"
        ).first()

        if not version_300:
            # Create validation request for v3.0.0
            validation_300 = ValidationRequest(
                model_id=model2.model_id,
                current_status_id=status_pending.value_id if status_pending else None,
                created_at=utc_now() - timedelta(days=30),
                updated_at=utc_now() - timedelta(days=5)
            )
            db.add(validation_300)
            db.commit()
            db.refresh(validation_300)

            # Add US and UK regions to validation
            validation_300.regions.append(us_region)
            validation_300.regions.append(uk_region)
            db.commit()

            # Create version
            version_300 = ModelVersion(
                model_id=model2.model_id,
                version_number="3.0.0",
                validation_request_id=validation_300.request_id,
                created_at=utc_now() - timedelta(days=30)
            )
            db.add(version_300)
            db.commit()
            db.refresh(version_300)

            # Create US regional approval - APPROVED
            us_approval_2 = ValidationApproval(
                request_id=validation_300.request_id,
                approver_id=us_approver.user_id,
                approver_role="Regional Validator",
                approval_type="Regional",
                region_id=us_region.region_id,
                approval_status="Approved",
                approved_at=utc_now() - timedelta(days=7),
                comments="Approved for US deployment after comprehensive testing."
            )
            db.add(us_approval_2)

            # Create UK regional approval - PENDING (no approved_at date)
            uk_approval = ValidationApproval(
                request_id=validation_300.request_id,
                approver_id=eu_approver.user_id,  # EU approver handles UK too
                approver_role="Regional Validator",
                approval_type="Regional",
                region_id=uk_region.region_id,
                approval_status="Pending",
                comments="Under review for UK regulatory requirements."
            )
            db.add(uk_approval)
            db.commit()

            print(f"  ✓ Created version 3.0.0 with validation request (ID: {validation_300.request_id})")
            print(f"    - US Regional Approval: Approved")
            print(f"    - UK Regional Approval: Pending")
        else:
            print(f"  ✓ Version 3.0.0 already exists")

        # Deploy version 3.0.0 to US only (UK pending approval)
        us_deployment_2 = db.query(ModelRegion).filter(
            ModelRegion.model_id == model2.model_id,
            ModelRegion.region_id == us_region.region_id
        ).first()

        if not us_deployment_2:
            us_deployment_2 = ModelRegion(
                model_id=model2.model_id,
                region_id=us_region.region_id,
                version_id=version_300.version_id,
                deployed_at=utc_now() - timedelta(days=5),
                deployment_notes="Production deployment - US region"
            )
            db.add(us_deployment_2)
            print(f"  ✓ Deployed v3.0.0 to US region")
        else:
            us_deployment_2.version_id = version_300.version_id
            us_deployment_2.deployed_at = utc_now() - timedelta(days=5)
            print(f"  ✓ Updated US deployment to v3.0.0")

        # Create UK model_region link but without deployed version (pending approval)
        uk_deployment = db.query(ModelRegion).filter(
            ModelRegion.model_id == model2.model_id,
            ModelRegion.region_id == uk_region.region_id
        ).first()

        if not uk_deployment:
            uk_deployment = ModelRegion(
                model_id=model2.model_id,
                region_id=uk_region.region_id,
                version_id=None,  # Not deployed yet
                deployment_notes="Awaiting regional approval before deployment"
            )
            db.add(uk_deployment)
            print(f"  ✓ Created UK region link (not deployed - pending approval)")

        db.commit()
        print()

        # ========================================================================
        # SCENARIO 3: CECL Model - Validation in progress
        # ========================================================================
        print("Creating Scenario 3: CECL Model")
        print("-" * 60)

        model3 = db.query(Model).filter(Model.model_name == "CECL Expected Loss Model").first()
        if not model3:
            model3 = Model(
                model_name="CECL Expected Loss Model",
                description="Current Expected Credit Loss model for loan portfolios",
                development_type="In-House",
                owner_id=admin.user_id,
                developer_id=validator.user_id,
                created_at=utc_now() - timedelta(days=90)
            )
            db.add(model3)
            db.commit()
            db.refresh(model3)
            print(f"  ✓ Created model: {model3.model_name} (ID: {model3.model_id})")
        else:
            print(f"  ✓ Model already exists: {model3.model_name} (ID: {model3.model_id})")

        # Version 1.5.0 - Currently being validated
        version_150 = db.query(ModelVersion).filter(
            ModelVersion.model_id == model3.model_id,
            ModelVersion.version_number == "1.5.0"
        ).first()

        if not version_150:
            # Create validation request for v1.5.0 - IN PROGRESS
            validation_150 = ValidationRequest(
                model_id=model3.model_id,
                current_status_id=status_in_progress.value_id if status_in_progress else None,
                created_at=utc_now() - timedelta(days=15),
                updated_at=utc_now() - timedelta(days=1)
            )
            db.add(validation_150)
            db.commit()
            db.refresh(validation_150)

            # Add US region to validation
            validation_150.regions.append(us_region)
            db.commit()

            # Create version
            version_150 = ModelVersion(
                model_id=model3.model_id,
                version_number="1.5.0",
                validation_request_id=validation_150.request_id,
                created_at=utc_now() - timedelta(days=15)
            )
            db.add(version_150)
            db.commit()
            db.refresh(version_150)

            print(f"  ✓ Created version 1.5.0 with validation IN PROGRESS (ID: {validation_150.request_id})")
            print(f"    - No approvals yet (validation in progress)")
        else:
            print(f"  ✓ Version 1.5.0 already exists")

        # Old version 1.4.0 still deployed to US
        version_140 = db.query(ModelVersion).filter(
            ModelVersion.model_id == model3.model_id,
            ModelVersion.version_number == "1.4.0"
        ).first()

        if not version_140:
            # Create old validation (already approved)
            validation_140 = ValidationRequest(
                model_id=model3.model_id,
                current_status_id=status_approved.value_id if status_approved else None,
                created_at=utc_now() - timedelta(days=120),
                updated_at=utc_now() - timedelta(days=100)
            )
            db.add(validation_140)
            db.commit()
            db.refresh(validation_140)

            validation_140.regions.append(us_region)
            db.commit()

            version_140 = ModelVersion(
                model_id=model3.model_id,
                version_number="1.4.0",
                validation_request_id=validation_140.request_id,
                created_at=utc_now() - timedelta(days=120)
            )
            db.add(version_140)
            db.commit()
            db.refresh(version_140)

            # Old US approval - APPROVED
            us_approval_old = ValidationApproval(
                request_id=validation_140.request_id,
                approver_id=us_approver.user_id,
                approver_role="Regional Validator",
                approval_type="Regional",
                region_id=us_region.region_id,
                approval_status="Approved",
                approved_at=utc_now() - timedelta(days=100)
            )
            db.add(us_approval_old)
            db.commit()

            print(f"  ✓ Created old version 1.4.0 (currently deployed)")

        # Deploy old version to US
        us_deployment_3 = db.query(ModelRegion).filter(
            ModelRegion.model_id == model3.model_id,
            ModelRegion.region_id == us_region.region_id
        ).first()

        if not us_deployment_3:
            us_deployment_3 = ModelRegion(
                model_id=model3.model_id,
                region_id=us_region.region_id,
                version_id=version_140.version_id,
                deployed_at=utc_now() - timedelta(days=95),
                deployment_notes="Production deployment - older version still active"
            )
            db.add(us_deployment_3)
            print(f"  ✓ Deployed v1.4.0 to US region (newer version being validated)")
        else:
            us_deployment_3.version_id = version_140.version_id
            us_deployment_3.deployed_at = utc_now() - timedelta(days=95)
            print(f"  ✓ Updated US deployment to v1.4.0")

        db.commit()
        print()

        # ========================================================================
        # SUMMARY
        # ========================================================================
        print("=" * 60)
        print("DEMO DATA SEEDING COMPLETE")
        print("=" * 60)
        print("\nSummary:")
        print(f"  ✓ Created 3 models with versions and validations")
        print(f"  ✓ Created regional deployments to US, EU, and UK")
        print(f"  ✓ Created regional approvals with proper region_id")
        print(f"\nTest the report at: http://localhost:8001/regional-compliance-report/")
        print(f"  - Filter by US to see 3 deployed models")
        print(f"  - Filter by EU to see 1 deployed model")
        print(f"  - Filter by UK to see 0 deployed models (1 pending approval)")
        print()

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_regional_compliance_demo()
