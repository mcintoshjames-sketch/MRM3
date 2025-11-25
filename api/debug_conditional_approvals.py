"""
Debug script to investigate why conditional approvals are not being created
for validation request 46.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from app.models.validation import ValidationRequest
from app.models.conditional_approval import ConditionalApprovalRule
from app.models.model import Model
from app.core.rule_evaluation import get_required_approver_roles

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/mrm_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def debug_validation_request_46():
    db = SessionLocal()
    try:
        # Get validation request 46
        validation_request = db.query(ValidationRequest).options(
            joinedload(ValidationRequest.models),
            joinedload(ValidationRequest.validation_type),
            joinedload(ValidationRequest.current_status)
        ).filter(ValidationRequest.request_id == 46).first()

        if not validation_request:
            print("❌ Validation request 46 not found")
            return

        print(f"\n✅ Validation Request #{validation_request.request_id}")
        print(f"   Status: {validation_request.current_status.label if validation_request.current_status else 'N/A'}")
        print(f"   Validation Type: {validation_request.validation_type.label if validation_request.validation_type else 'N/A'}")
        print(f"   Models: {len(validation_request.models)}")

        # Check models
        for idx, model in enumerate(validation_request.models, 1):
            print(f"\n   Model #{idx}: {model.model_name} (ID: {model.model_id})")
            print(f"      Risk Tier ID: {model.risk_tier_id}")
            if model.risk_tier_id:
                risk_tier = model.risk_tier
                print(f"      Risk Tier: {risk_tier.label if risk_tier else 'N/A'}")
            else:
                print(f"      Risk Tier: None (NULL)")

        # Check active conditional approval rules
        print("\n\n📋 Active Conditional Approval Rules:")
        rules = db.query(ConditionalApprovalRule).filter(
            ConditionalApprovalRule.is_active == True
        ).all()

        if not rules:
            print("   ❌ No active conditional approval rules found")
        else:
            for rule in rules:
                print(f"\n   Rule #{rule.rule_id}: {rule.rule_name}")
                print(f"      Description: {rule.description or 'N/A'}")
                print(f"      Constraints:")
                if rule.applies_to_all_validations:
                    print(f"         ✓ Applies to ALL validations")
                if rule.validation_type_ids:
                    print(f"         Validation Types: {rule.validation_type_ids}")
                if rule.risk_tier_ids:
                    print(f"         Risk Tiers: {rule.risk_tier_ids}")

                # Show required approver roles
                print(f"      Required Approver Roles: {len(rule.required_approvers)}")
                for req in rule.required_approvers:
                    print(f"         - {req.approver_role.role_name if req.approver_role else 'N/A'}")

        # Test rule evaluation for each model
        print("\n\n🔍 Testing Rule Evaluation:")
        for model in validation_request.models:
            print(f"\n   Model: {model.model_name} (ID: {model.model_id})")

            result = get_required_approver_roles(db, validation_request, model)

            print(f"      Matching Rules: {len(result['matching_rules'])}")
            for rule_info in result['matching_rules']:
                print(f"         - Rule #{rule_info['rule_id']}: {rule_info['rule_name']}")

            print(f"      Required Roles: {len(result['required_roles'])}")
            for role_info in result['required_roles']:
                print(f"         - {role_info['role_name']} (ID: {role_info['role_id']})")
                if role_info.get('approval_id'):
                    print(f"           (Approval already exists: #{role_info['approval_id']})")

    finally:
        db.close()

if __name__ == "__main__":
    debug_validation_request_46()
