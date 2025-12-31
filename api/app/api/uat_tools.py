"""UAT Tools - Temporary endpoints for data reset and re-seeding.

WARNING: These endpoints are for UAT/testing only and should be removed before production.
"""
import json
import os
from datetime import date, timedelta, datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.time import utc_now
from app.models.user import User
from app.core.roles import is_admin, RoleCode

router = APIRouter()

# Backup storage directory (inside container)
BACKUP_DIR = "/tmp/uat_backups"


class BackupInfo(BaseModel):
    """Backup metadata."""
    backup_id: str
    created_at: str
    created_by: str
    table_counts: Dict[str, int]
    size_bytes: int


# Tables to PRESERVE (configuration/reference data)
PRESERVE_TABLES = {
    # Core users and directory
    "users",
    "user_regions",
    "entra_users",
    # Taxonomies
    "taxonomies",
    "taxonomy_values",
    # Regions and Vendors
    "regions",
    "vendors",
    # Validation configuration
    "validation_policies",
    "validation_workflow_sla",
    "validation_component_definitions",
    "component_definition_configurations",
    "component_definition_config_items",
    # Model type/change taxonomies
    "model_change_categories",
    "model_change_types",
    "model_type_categories",
    "model_types",
    # Conditional approval configuration
    "approver_roles",
    "conditional_approval_rules",
    "rule_required_approvers",
    # FRY reporting structure
    "fry_reports",
    "fry_schedules",
    "fry_metric_groups",
    "fry_line_items",
    # KPM categories and definitions
    "kpm_categories",
    "kpms",
    # Risk assessment factors
    "qualitative_risk_factors",
    "qualitative_factor_guidance",
    # Scorecard configuration
    "scorecard_sections",
    "scorecard_criteria",
    # MAP applications reference
    "map_applications",
    # Recommendation config
    "recommendation_priority_configs",
    "recommendation_timeframe_configs",
    # Monitoring frequency reference
    # "monitoring_frequencies",  # if exists as separate table
}

# Tables to CLEAR (transactional data) - order matters for FK constraints
CLEAR_TABLES_ORDERED = [
    # Audit logs first (no FK dependencies on it)
    "audit_logs",
    # Monitoring results and cycles
    "monitoring_results",
    "monitoring_cycle_approvals",
    "monitoring_cycles",
    "monitoring_plan_metric_snapshots",
    "monitoring_plan_model_snapshots",
    "monitoring_plan_versions",
    "monitoring_plan_metrics",
    "monitoring_plan_models",
    "monitoring_plans",
    "monitoring_team_members",
    "monitoring_teams",
    # Recommendations
    "recommendation_approvals",
    "recommendation_status_history",
    "closure_evidences",
    "recommendation_rebuttals",
    "action_plan_tasks",
    "recommendations",
    # Decommissioning
    "decommissioning_approvals",
    "decommissioning_status_history",
    "decommissioning_requests",
    # Validation workflow
    "validation_scorecard_results",
    "validation_scorecard_ratings",
    "validation_approvals",
    "validation_review_outcomes",
    "validation_outcomes",
    "validation_work_components",
    "validation_assignments",
    "validation_status_history",
    "validation_plan_components",
    "validation_plans",
    "validation_request_model_versions",
    "validation_request_models",
    "validation_requests",
    "validation_grouping_memory",
    # Risk assessments
    "qualitative_factor_assessments",
    "model_risk_assessments",
    # Model-related
    "overdue_revalidation_comments",
    "version_deployment_tasks",
    "export_views",
    "model_pending_edits",
    "model_applications",
    "model_dependency_metadata",
    "model_feed_dependencies",
    "model_hierarchies",
    "model_name_history",
    "model_submission_comments",
    "model_delegates",
    "model_version_regions",
    "model_versions",
    "model_regions",
    "model_regulatory_categories",
    "model_users",
    "models",
    # Saved queries (user-specific but transactional)
    "saved_queries",
]


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role for UAT tools."""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for UAT tools"
        )
    return current_user


def _serialize_value(value):
    """Serialize a database value to JSON-compatible format."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    # Handle Decimal
    try:
        from decimal import Decimal
        if isinstance(value, Decimal):
            return float(value)
    except ImportError:
        pass
    return value


def _deserialize_value(value, column_type: str):
    """Deserialize a JSON value back to database format."""
    if value is None:
        return None

    # Handle datetime columns
    if 'timestamp' in column_type.lower() or 'datetime' in column_type.lower():
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return value

    # Handle date columns
    if column_type.lower() == 'date':
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                return value

    return value


@router.post("/backup")
def create_backup(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict:
    """
    Create a backup of all transactional data before reset.

    Backups are stored as JSON files and can be restored later.
    This is useful for preserving test data before running reset.
    """
    # Ensure backup directory exists
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Generate backup ID with timestamp
    backup_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"backup_{backup_id}.json")

    backup_data = {
        "backup_id": backup_id,
        "created_at": utc_now().isoformat(),
        "created_by": current_user.email,
        "tables": {}
    }

    table_counts = {}
    errors = []

    # Backup each transactional table in reverse order (for proper restore order)
    for table_name in reversed(CLEAR_TABLES_ORDERED):
        try:
            # Check if table exists
            check_result = db.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                f"WHERE table_name = '{table_name}')"
            ))
            if not check_result.scalar():
                continue

            # Get column info
            columns_result = db.execute(text(
                f"SELECT column_name, data_type FROM information_schema.columns "
                f"WHERE table_name = '{table_name}' ORDER BY ordinal_position"
            ))
            columns = [(row[0], row[1]) for row in columns_result]

            if not columns:
                continue

            # Fetch all rows
            column_names = [c[0] for c in columns]
            result = db.execute(text(f'SELECT * FROM "{table_name}"'))
            rows = result.fetchall()

            # Serialize rows
            table_data = []
            for row in rows:
                row_dict = {}
                for i, (col_name, col_type) in enumerate(columns):
                    row_dict[col_name] = _serialize_value(row[i])
                table_data.append(row_dict)

            backup_data["tables"][table_name] = {
                "columns": columns,
                "rows": table_data
            }
            table_counts[table_name] = len(table_data)

        except Exception as e:
            errors.append(f"{table_name}: {str(e)}")

    # Write backup file
    try:
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2, default=str)

        file_size = os.path.getsize(backup_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to write backup file: {str(e)}"
        )

    return {
        "message": "Backup created successfully",
        "backup_id": backup_id,
        "backup_path": backup_path,
        "table_counts": table_counts,
        "total_rows": sum(table_counts.values()),
        "size_bytes": file_size,
        "errors": errors if errors else None
    }


@router.get("/backups")
def list_backups(
    current_user: User = Depends(require_admin)
) -> Dict:
    """
    List all available backups.

    Returns backup metadata including creation time, creator, and size.
    """
    if not os.path.exists(BACKUP_DIR):
        return {"backups": [], "count": 0}

    backups = []
    for filename in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if filename.startswith("backup_") and filename.endswith(".json"):
            filepath = os.path.join(BACKUP_DIR, filename)
            try:
                with open(filepath, 'r') as f:
                    # Read just the metadata without loading all data
                    data = json.load(f)

                table_counts = {
                    table: len(table_data.get("rows", []))
                    for table, table_data in data.get("tables", {}).items()
                }

                backups.append({
                    "backup_id": data.get("backup_id", filename.replace("backup_", "").replace(".json", "")),
                    "created_at": data.get("created_at"),
                    "created_by": data.get("created_by"),
                    "table_counts": table_counts,
                    "total_rows": sum(table_counts.values()),
                    "size_bytes": os.path.getsize(filepath)
                })
            except Exception as e:
                backups.append({
                    "backup_id": filename.replace("backup_", "").replace(".json", ""),
                    "error": str(e)
                })

    return {
        "backups": backups,
        "count": len(backups),
        "backup_directory": BACKUP_DIR
    }


@router.post("/restore/{backup_id}")
def restore_backup(
    backup_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict:
    """
    Restore transactional data from a backup.

    WARNING: This will first DELETE all current transactional data,
    then restore from the backup. Make sure you have a current backup
    if you need to preserve the current state.
    """
    backup_path = os.path.join(BACKUP_DIR, f"backup_{backup_id}.json")

    if not os.path.exists(backup_path):
        raise HTTPException(
            status_code=404,
            detail=f"Backup '{backup_id}' not found"
        )

    # Load backup data
    try:
        with open(backup_path, 'r') as f:
            backup_data = json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read backup file: {str(e)}"
        )

    # First, clear all transactional data
    deleted_counts = {}
    for table_name in CLEAR_TABLES_ORDERED:
        try:
            check_result = db.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                f"WHERE table_name = '{table_name}')"
            ))
            if not check_result.scalar():
                continue

            result = db.execute(text(f'DELETE FROM "{table_name}"'))
            deleted_counts[table_name] = result.rowcount
            db.commit()
        except Exception:
            db.rollback()

    # Restore data from backup (tables are in reverse order for proper FK handling)
    restored_counts = {}
    errors = []
    tables_data = backup_data.get("tables", {})

    # Process tables in the order they appear in backup (reversed CLEAR_TABLES_ORDERED)
    # which should be safe for FK constraints
    for table_name in reversed(CLEAR_TABLES_ORDERED):
        if table_name not in tables_data:
            continue

        table_info = tables_data[table_name]
        rows = table_info.get("rows", [])
        columns = table_info.get("columns", [])

        if not rows:
            restored_counts[table_name] = 0
            continue

        try:
            column_names = [c[0] for c in columns]
            column_types = {c[0]: c[1] for c in columns}

            for row in rows:
                # Build INSERT statement
                values = []
                placeholders = []
                for col_name in column_names:
                    if col_name in row:
                        val = _deserialize_value(row[col_name], column_types.get(col_name, ''))
                        values.append(val)
                        placeholders.append(f":{col_name}")
                    else:
                        placeholders.append("DEFAULT")

                cols_str = ', '.join(f'"{c}"' for c in column_names if c in row)
                placeholders_str = ', '.join(f":{c}" for c in column_names if c in row)

                insert_sql = f'INSERT INTO "{table_name}" ({cols_str}) VALUES ({placeholders_str})'

                params = {c: _deserialize_value(row[c], column_types.get(c, ''))
                          for c in column_names if c in row}

                db.execute(text(insert_sql), params)

            db.commit()
            restored_counts[table_name] = len(rows)

        except Exception as e:
            db.rollback()
            errors.append(f"{table_name}: {str(e)}")

    # Reset sequences to max values
    sequence_tables = [
        ("models_model_id_seq", "models", "model_id"),
        ("model_versions_version_id_seq", "model_versions", "version_id"),
        ("validation_requests_request_id_seq", "validation_requests", "request_id"),
        ("recommendations_recommendation_id_seq", "recommendations", "recommendation_id"),
        ("monitoring_plans_plan_id_seq", "monitoring_plans", "plan_id"),
        ("monitoring_cycles_cycle_id_seq", "monitoring_cycles", "cycle_id"),
        ("audit_logs_log_id_seq", "audit_logs", "log_id"),
    ]

    for seq_name, table, column in sequence_tables:
        try:
            result = db.execute(text(f'SELECT COALESCE(MAX("{column}"), 0) + 1 FROM "{table}"'))
            max_val = result.scalar()
            db.execute(text(f"ALTER SEQUENCE {seq_name} RESTART WITH {max_val}"))
            db.commit()
        except Exception:
            db.rollback()

    return {
        "message": f"Restore from backup '{backup_id}' complete",
        "backup_created_at": backup_data.get("created_at"),
        "backup_created_by": backup_data.get("created_by"),
        "deleted_counts": deleted_counts,
        "restored_counts": restored_counts,
        "total_restored": sum(restored_counts.values()),
        "errors": errors if errors else None
    }


@router.delete("/backups/{backup_id}")
def delete_backup(
    backup_id: str,
    current_user: User = Depends(require_admin)
) -> Dict:
    """
    Delete a specific backup file.
    """
    backup_path = os.path.join(BACKUP_DIR, f"backup_{backup_id}.json")

    if not os.path.exists(backup_path):
        raise HTTPException(
            status_code=404,
            detail=f"Backup '{backup_id}' not found"
        )

    try:
        os.remove(backup_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete backup: {str(e)}"
        )

    return {
        "message": f"Backup '{backup_id}' deleted successfully"
    }


@router.delete("/reset-transactional-data")
def reset_transactional_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict:
    """
    Reset all transactional data while preserving configuration.

    WARNING: This will DELETE all models, validations, recommendations,
    monitoring data, and audit logs. Configuration (taxonomies, policies,
    users, vendors, regions) will be preserved.

    This endpoint is for UAT purposes only.
    """
    deleted_counts = {}
    errors = []
    skipped = []

    for table_name in CLEAR_TABLES_ORDERED:
        try:
            # First check if table exists
            check_result = db.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                f"WHERE table_name = '{table_name}')"
            ))
            table_exists = check_result.scalar()

            if not table_exists:
                skipped.append(table_name)
                continue

            # Use raw SQL to avoid ORM cascade issues
            result = db.execute(text(f'DELETE FROM "{table_name}"'))
            deleted_counts[table_name] = result.rowcount
            db.commit()  # Commit after each successful deletion
        except Exception as e:
            db.rollback()  # Rollback failed transaction to continue
            errors.append(f"{table_name}: {str(e)}")

    # Reset sequences for primary keys
    sequence_resets = [
        "models_model_id_seq",
        "model_versions_version_id_seq",
        "validation_requests_request_id_seq",
        "recommendations_recommendation_id_seq",
        "monitoring_plans_plan_id_seq",
        "monitoring_cycles_cycle_id_seq",
        "audit_logs_log_id_seq",
    ]

    for seq in sequence_resets:
        try:
            db.execute(text(f"ALTER SEQUENCE {seq} RESTART WITH 1"))
            db.commit()
        except Exception:
            db.rollback()
            pass  # Sequence might not exist

    return {
        "message": "Transactional data reset complete",
        "deleted_counts": deleted_counts,
        "skipped_tables": skipped if skipped else None,
        "errors": errors if errors else None,
        "preserved_tables": list(PRESERVE_TABLES)
    }


@router.post("/seed-uat-data")
def seed_uat_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict:
    """
    Seed UAT data using API-like workflows for internal consistency.

    Creates a comprehensive set of example models at various stages:
    - 2 models fully validated and approved
    - 2 models in active validation (different stages)
    - 1 model pending initial validation
    - 1 model with recommendations in progress
    - 1 model approaching revalidation due date
    - 1 model overdue for revalidation (~14 months, past Tier 1 grace period)
    - 1 model critically overdue (~18 months since last validation)
    - 1 model with overdue validation request (target date in past)
    - 1 model with overdue recommendations (15-45 days past due)

    All models have internally consistent historical data including:
    - Version history
    - Validation requests with complete status history progression
    - Validation outcomes where applicable
    - Recommendations and action plan tasks where applicable

    This endpoint is for UAT purposes only.
    """
    from app.models import (
        Model, ModelVersion, ValidationRequest, ValidationStatusHistory,
        ValidationAssignment, ValidationOutcome, ValidationApproval,
        ValidationPlan, ValidationPlanComponent, Recommendation,
        ActionPlanTask, TaxonomyValue, Taxonomy, Region,
        ModelRiskAssessment, QualitativeFactorAssessment, QualitativeRiskFactor
    )
    from app.models.model import ModelStatus
    from app.models.validation import ValidationRequestModelVersion
    from decimal import Decimal

    results = {"models_created": [], "validations_created": [], "errors": []}

    try:
        # Get required taxonomy values
        def get_taxonomy_value(taxonomy_name: str, code: str) -> TaxonomyValue:
            return db.query(TaxonomyValue).join(Taxonomy).filter(
                Taxonomy.name == taxonomy_name,
                TaxonomyValue.code == code
            ).first()

        # Get status values
        status_intake = get_taxonomy_value("Validation Request Status", "INTAKE")
        status_planning = get_taxonomy_value("Validation Request Status", "PLANNING")
        status_in_progress = get_taxonomy_value("Validation Request Status", "IN_PROGRESS")
        status_review = get_taxonomy_value("Validation Request Status", "REVIEW")
        status_pending_approval = get_taxonomy_value("Validation Request Status", "PENDING_APPROVAL")
        status_approved = get_taxonomy_value("Validation Request Status", "APPROVED")

        # Get priority values
        priority_high = get_taxonomy_value("Validation Priority", "HIGH")
        priority_medium = get_taxonomy_value("Validation Priority", "MEDIUM")
        priority_low = get_taxonomy_value("Validation Priority", "LOW")

        # Get validation types
        type_initial = get_taxonomy_value("Validation Type", "INITIAL")
        type_comprehensive = get_taxonomy_value("Validation Type", "COMPREHENSIVE")
        type_targeted = get_taxonomy_value("Validation Type", "TARGETED")

        # Get risk tiers
        tier_1 = get_taxonomy_value("Model Risk Tier", "TIER_1")
        tier_2 = get_taxonomy_value("Model Risk Tier", "TIER_2")
        tier_3 = get_taxonomy_value("Model Risk Tier", "TIER_3")

        # Get outcome values
        outcome_fit = get_taxonomy_value("Overall Rating", "FIT_FOR_PURPOSE")
        outcome_not_fit = get_taxonomy_value("Overall Rating", "NOT_FIT_FOR_PURPOSE")

        # Get usage frequency values
        usage_daily = get_taxonomy_value("Model Usage Frequency", "DAILY")
        usage_monthly = get_taxonomy_value("Model Usage Frequency", "MONTHLY")
        usage_quarterly = get_taxonomy_value("Model Usage Frequency", "QUARTERLY")

        # Get recommendation priorities
        rec_priority_high = get_taxonomy_value("Recommendation Priority", "HIGH")
        rec_priority_medium = get_taxonomy_value("Recommendation Priority", "MEDIUM")

        # Get recommendation statuses (note: codes use REC_ prefix)
        rec_status_open = get_taxonomy_value("Recommendation Status", "REC_OPEN")
        rec_status_in_progress = get_taxonomy_value("Recommendation Status", "REC_PENDING_ACTION_PLAN")

        # Get a region
        region = db.query(Region).first()

        # Get users for assignments
        admin_user = db.query(User).filter(User.role_code == RoleCode.ADMIN.value).first()
        validator_user = db.query(User).filter(User.role_code == RoleCode.VALIDATOR.value).first()
        regular_user = db.query(User).filter(User.role_code == RoleCode.USER.value).first()

        if not all([status_intake, status_approved, tier_1, admin_user, usage_daily]):
            raise HTTPException(
                status_code=400,
                detail="Required taxonomy values or users not found. Run base seed first."
            )

        # Get qualitative factors for risk assessment
        factors = db.query(QualitativeRiskFactor).filter(
            QualitativeRiskFactor.is_active == True
        ).all()

        today = date.today()

        # ========================================
        # MODEL 1: Fully Validated Tier 1 Model
        # ========================================
        model1 = Model(
            model_name="Credit Risk Scorecard",
            description="Consumer credit scoring model for loan origination decisions. Uses logistic regression with 15 predictive variables.",
            development_type="In-House",
            owner_id=admin_user.user_id,
            developer_id=validator_user.user_id if validator_user else admin_user.user_id,
            risk_tier_id=tier_1.value_id if tier_1 else None,
            usage_frequency_id=usage_daily.value_id,
            status=ModelStatus.ACTIVE.value,
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add(model1)
        db.flush()

        # Create initial version
        version1 = ModelVersion(
            model_id=model1.model_id,
            version_number="2.1",
            change_type="MAJOR",
            change_description="Production release with enhanced features",
            created_by_id=admin_user.user_id,
            production_date=today - timedelta(days=180),
            status="ACTIVE"
        )
        db.add(version1)
        db.flush()

        # Create completed validation request
        val_req1 = ValidationRequest(
            validation_type_id=type_comprehensive.value_id if type_comprehensive else type_initial.value_id,
            priority_id=priority_high.value_id if priority_high else priority_medium.value_id,
            current_status_id=status_approved.value_id,
            requestor_id=admin_user.user_id,
            target_completion_date=today - timedelta(days=30),
            completion_date=datetime.combine(today - timedelta(days=35), datetime.min.time()),
            trigger_reason="Annual comprehensive validation completed successfully.",
            created_at=utc_now() - timedelta(days=200)
        )
        db.add(val_req1)
        db.flush()

        # Link model to validation request via association table
        db.add(ValidationRequestModelVersion(
            request_id=val_req1.request_id,
            model_id=model1.model_id,
            version_id=version1.version_id
        ))
        db.flush()

        # Create status history for val_req1
        prev_status_id = None
        for status_val, days_ago in [
            (status_intake, 200), (status_planning, 195), (status_in_progress, 180),
            (status_review, 50), (status_pending_approval, 40), (status_approved, 35)
        ]:
            if status_val:
                history = ValidationStatusHistory(
                    request_id=val_req1.request_id,
                    old_status_id=prev_status_id,
                    new_status_id=status_val.value_id,
                    changed_by_id=admin_user.user_id,
                    change_reason="Workflow progression",
                    changed_at=utc_now() - timedelta(days=days_ago)
                )
                db.add(history)
                prev_status_id = status_val.value_id

        # Create outcome
        outcome1 = ValidationOutcome(
            request_id=val_req1.request_id,
            overall_rating_id=outcome_fit.value_id if outcome_fit else outcome_not_fit.value_id,
            executive_summary="Model performs within acceptable thresholds. Minor documentation updates recommended.",
            effective_date=today - timedelta(days=35),
            created_at=utc_now() - timedelta(days=40)
        )
        db.add(outcome1)

        # Note: Risk assessments commented out due to check constraint complexity
        # Can be added later with proper calculation of derived tiers

        results["models_created"].append({
            "model_id": model1.model_id,
            "name": model1.model_name,
            "status": "Fully validated, approved"
        })

        # ========================================
        # MODEL 2: Tier 2 Model with Active Validation
        # ========================================
        model2 = Model(
            model_name="Market Risk VaR",
            description="Value-at-Risk model for trading book positions using historical simulation.",
            development_type="In-House",
            owner_id=admin_user.user_id,
            risk_tier_id=tier_2.value_id if tier_2 else None,
            usage_frequency_id=usage_daily.value_id,
            status=ModelStatus.ACTIVE.value,
            created_at=utc_now() - timedelta(days=365),
            updated_at=utc_now()
        )
        db.add(model2)
        db.flush()

        version2 = ModelVersion(
            model_id=model2.model_id,
            version_number="3.0",
            change_type="MAJOR",
            change_description="Updated methodology",
            created_by_id=admin_user.user_id,
            production_date=today - timedelta(days=90),
            status="ACTIVE"
        )
        db.add(version2)
        db.flush()

        # Validation in progress
        val_req2 = ValidationRequest(
            validation_type_id=type_targeted.value_id if type_targeted else type_initial.value_id,
            priority_id=priority_medium.value_id if priority_medium else priority_low.value_id,
            current_status_id=status_in_progress.value_id if status_in_progress else status_intake.value_id,
            requestor_id=admin_user.user_id,
            target_completion_date=today + timedelta(days=30),
            trigger_reason="Targeted review of methodology changes.",
            created_at=utc_now() - timedelta(days=45)
        )
        db.add(val_req2)
        db.flush()

        # Link model to validation request
        db.add(ValidationRequestModelVersion(
            request_id=val_req2.request_id,
            model_id=model2.model_id,
            version_id=version2.version_id
        ))
        db.flush()

        # Assignment
        if validator_user:
            assignment2 = ValidationAssignment(
                request_id=val_req2.request_id,
                validator_id=validator_user.user_id,
                is_primary=True,
                is_reviewer=False,
                assignment_date=today - timedelta(days=40)
            )
            db.add(assignment2)

        results["models_created"].append({
            "model_id": model2.model_id,
            "name": model2.model_name,
            "status": "Validation in progress"
        })

        # ========================================
        # MODEL 3: Tier 3 Model Pending Validation
        # ========================================
        model3 = Model(
            model_name="Customer Segmentation",
            description="ML-based customer segmentation for marketing campaigns.",
            development_type="Third-Party",
            owner_id=regular_user.user_id if regular_user else admin_user.user_id,
            vendor_id=1,  # Assumes vendor exists
            risk_tier_id=tier_3.value_id if tier_3 else None,
            usage_frequency_id=usage_quarterly.value_id,
            status=ModelStatus.IN_DEVELOPMENT.value,
            created_at=utc_now() - timedelta(days=30),
            updated_at=utc_now()
        )
        db.add(model3)
        db.flush()

        version3 = ModelVersion(
            model_id=model3.model_id,
            version_number="1.0",
            change_type="MAJOR",
            change_description="Initial version",
            created_by_id=admin_user.user_id,
            status="DRAFT"
        )
        db.add(version3)
        db.flush()

        # Validation in intake
        val_req3 = ValidationRequest(
            validation_type_id=type_initial.value_id,
            priority_id=priority_low.value_id if priority_low else priority_medium.value_id,
            current_status_id=status_intake.value_id,
            requestor_id=admin_user.user_id,
            target_completion_date=today + timedelta(days=60),
            trigger_reason="Initial validation for new third-party model.",
            created_at=utc_now() - timedelta(days=5)
        )
        db.add(val_req3)
        db.flush()

        # Link model to validation request
        db.add(ValidationRequestModelVersion(
            request_id=val_req3.request_id,
            model_id=model3.model_id,
            version_id=version3.version_id
        ))

        results["models_created"].append({
            "model_id": model3.model_id,
            "name": model3.model_name,
            "status": "Pending initial validation (intake)"
        })

        # ========================================
        # MODEL 4: Model with Open Recommendations
        # ========================================
        model4 = Model(
            model_name="CECL Allowance Model",
            description="Current Expected Credit Loss model for loan loss provisioning.",
            development_type="In-House",
            owner_id=admin_user.user_id,
            developer_id=validator_user.user_id if validator_user else None,
            risk_tier_id=tier_1.value_id if tier_1 else None,
            usage_frequency_id=usage_quarterly.value_id,
            status=ModelStatus.ACTIVE.value,
            created_at=utc_now() - timedelta(days=500),
            updated_at=utc_now()
        )
        db.add(model4)
        db.flush()

        version4 = ModelVersion(
            model_id=model4.model_id,
            version_number="4.2",
            change_type="MINOR",
            change_description="Quarterly parameter update",
            created_by_id=admin_user.user_id,
            production_date=today - timedelta(days=60),
            status="ACTIVE"
        )
        db.add(version4)
        db.flush()

        # Completed validation with findings
        val_req4 = ValidationRequest(
            validation_type_id=type_comprehensive.value_id if type_comprehensive else type_initial.value_id,
            priority_id=priority_high.value_id if priority_high else priority_medium.value_id,
            current_status_id=status_approved.value_id,
            requestor_id=admin_user.user_id,
            target_completion_date=today - timedelta(days=45),
            completion_date=datetime.combine(today - timedelta(days=50), datetime.min.time()),
            trigger_reason="Comprehensive validation completed with findings.",
            created_at=utc_now() - timedelta(days=120)
        )
        db.add(val_req4)
        db.flush()

        # Link model to validation request
        db.add(ValidationRequestModelVersion(
            request_id=val_req4.request_id,
            model_id=model4.model_id,
            version_id=version4.version_id
        ))
        db.flush()

        outcome4 = ValidationOutcome(
            request_id=val_req4.request_id,
            overall_rating_id=outcome_fit.value_id if outcome_fit else outcome_not_fit.value_id,
            executive_summary="Model approved with conditions. Two recommendations require remediation.",
            effective_date=today - timedelta(days=50),
            created_at=utc_now() - timedelta(days=50)
        )
        db.add(outcome4)
        db.flush()

        # Create recommendations - note: Model 4 recommendations have future due dates (not overdue)
        # Overdue recommendations are on Model 10
        if rec_status_open and rec_priority_high:
            rec1 = Recommendation(
                recommendation_code=f"REC-{today.year}-00001",
                validation_request_id=val_req4.request_id,
                model_id=model4.model_id,
                title="Enhance documentation for economic scenario assumptions",
                description="Documentation should clearly specify the economic scenarios used and their rationale.",
                priority_id=rec_priority_high.value_id,
                current_status_id=rec_status_open.value_id,
                created_by_id=validator_user.user_id if validator_user else admin_user.user_id,
                assigned_to_id=admin_user.user_id,
                original_target_date=today + timedelta(days=30),
                current_target_date=today + timedelta(days=30),
                created_at=utc_now() - timedelta(days=50)
            )
            db.add(rec1)

        if rec_status_in_progress and rec_priority_medium:
            # Get task completion status
            task_status_in_progress = get_taxonomy_value("Action Plan Task Status", "IN_PROGRESS")

            rec2 = Recommendation(
                recommendation_code=f"REC-{today.year}-00002",
                validation_request_id=val_req4.request_id,
                model_id=model4.model_id,
                title="Implement automated backtesting framework",
                description="Develop automated backtesting to run monthly and generate exception reports.",
                priority_id=rec_priority_medium.value_id,
                current_status_id=rec_status_in_progress.value_id,
                created_by_id=validator_user.user_id if validator_user else admin_user.user_id,
                assigned_to_id=admin_user.user_id,
                original_target_date=today + timedelta(days=60),
                current_target_date=today + timedelta(days=60),
                created_at=utc_now() - timedelta(days=50)
            )
            db.add(rec2)
            db.flush()

            # Add action plan task
            if task_status_in_progress:
                task1 = ActionPlanTask(
                    recommendation_id=rec2.recommendation_id,
                    task_order=1,
                    description="Document requirements and design for automated backtesting framework.",
                    owner_id=admin_user.user_id,
                    target_date=today + timedelta(days=15),
                    completion_status_id=task_status_in_progress.value_id,
                    created_at=utc_now() - timedelta(days=30)
                )
                db.add(task1)

        results["models_created"].append({
            "model_id": model4.model_id,
            "name": model4.model_name,
            "status": "Approved with open recommendations"
        })

        # ========================================
        # MODEL 5: Model Approaching Revalidation
        # ========================================
        model5 = Model(
            model_name="Fraud Detection Neural Network",
            description="Deep learning model for real-time transaction fraud detection.",
            development_type="In-House",
            owner_id=admin_user.user_id,
            risk_tier_id=tier_2.value_id if tier_2 else None,
            usage_frequency_id=usage_daily.value_id,
            status=ModelStatus.ACTIVE.value,
            created_at=utc_now() - timedelta(days=400),
            updated_at=utc_now()
        )
        db.add(model5)
        db.flush()

        version5 = ModelVersion(
            model_id=model5.model_id,
            version_number="2.5",
            change_type="MINOR",
            change_description="Model retraining with updated data",
            created_by_id=admin_user.user_id,
            production_date=today - timedelta(days=330),
            status="ACTIVE"
        )
        db.add(version5)
        db.flush()

        # Old completed validation (approaching 1-year mark)
        val_req5 = ValidationRequest(
            validation_type_id=type_comprehensive.value_id if type_comprehensive else type_initial.value_id,
            priority_id=priority_medium.value_id if priority_medium else priority_low.value_id,
            current_status_id=status_approved.value_id,
            requestor_id=admin_user.user_id,
            target_completion_date=today - timedelta(days=330),
            completion_date=datetime.combine(today - timedelta(days=335), datetime.min.time()),
            trigger_reason="Annual validation completed.",
            created_at=utc_now() - timedelta(days=380)
        )
        db.add(val_req5)
        db.flush()

        # Link model to validation request
        db.add(ValidationRequestModelVersion(
            request_id=val_req5.request_id,
            model_id=model5.model_id,
            version_id=version5.version_id
        ))
        db.flush()

        outcome5 = ValidationOutcome(
            request_id=val_req5.request_id,
            overall_rating_id=outcome_fit.value_id if outcome_fit else outcome_not_fit.value_id,
            executive_summary="Model meets all performance criteria.",
            effective_date=today - timedelta(days=335),
            created_at=utc_now() - timedelta(days=335)
        )
        db.add(outcome5)

        results["models_created"].append({
            "model_id": model5.model_id,
            "name": model5.model_name,
            "status": "Approaching revalidation due date"
        })

        # ========================================
        # MODEL 6: Validation in Review Stage
        # ========================================
        model6 = Model(
            model_name="LGD Workout Model",
            description="Loss Given Default model for commercial real estate portfolio.",
            development_type="In-House",
            owner_id=admin_user.user_id,
            risk_tier_id=tier_1.value_id if tier_1 else None,
            usage_frequency_id=usage_monthly.value_id,
            status=ModelStatus.ACTIVE.value,
            created_at=utc_now() - timedelta(days=200),
            updated_at=utc_now()
        )
        db.add(model6)
        db.flush()

        version6 = ModelVersion(
            model_id=model6.model_id,
            version_number="1.3",
            change_type="MINOR",
            change_description="Updated recovery assumptions",
            created_by_id=admin_user.user_id,
            production_date=today - timedelta(days=100),
            status="ACTIVE"
        )
        db.add(version6)
        db.flush()

        # Validation in review
        val_req6 = ValidationRequest(
            validation_type_id=type_targeted.value_id if type_targeted else type_initial.value_id,
            priority_id=priority_high.value_id if priority_high else priority_medium.value_id,
            current_status_id=status_review.value_id if status_review else status_in_progress.value_id,
            requestor_id=admin_user.user_id,
            target_completion_date=today + timedelta(days=7),
            trigger_reason="Targeted review of updated assumptions.",
            created_at=utc_now() - timedelta(days=60)
        )
        db.add(val_req6)
        db.flush()

        # Link model to validation request
        db.add(ValidationRequestModelVersion(
            request_id=val_req6.request_id,
            model_id=model6.model_id,
            version_id=version6.version_id
        ))
        db.flush()

        if validator_user:
            assignment6 = ValidationAssignment(
                request_id=val_req6.request_id,
                validator_id=validator_user.user_id,
                is_primary=True,
                is_reviewer=False,
                assignment_date=today - timedelta(days=55)
            )
            db.add(assignment6)

        results["models_created"].append({
            "model_id": model6.model_id,
            "name": model6.model_name,
            "status": "Validation in review stage"
        })

        # ========================================
        # MODEL 7: Tier 1 Model Overdue for Revalidation
        # Last validation 14 months ago (past 12mo + 1mo grace)
        # ========================================
        model7 = Model(
            model_name="Operational Risk Capital Model",
            description="Advanced Measurement Approach model for operational risk capital calculation under Basel framework.",
            development_type="In-House",
            owner_id=admin_user.user_id,
            developer_id=validator_user.user_id if validator_user else None,
            risk_tier_id=tier_1.value_id if tier_1 else None,
            usage_frequency_id=usage_quarterly.value_id,
            status=ModelStatus.ACTIVE.value,
            created_at=utc_now() - timedelta(days=800),
            updated_at=utc_now()
        )
        db.add(model7)
        db.flush()

        version7 = ModelVersion(
            model_id=model7.model_id,
            version_number="3.1",
            change_type="MINOR",
            change_description="Annual parameter calibration",
            created_by_id=admin_user.user_id,
            production_date=today - timedelta(days=420),
            status="ACTIVE"
        )
        db.add(version7)
        db.flush()

        # Historical completed validation - 14 months ago (430 days)
        # Tier 1 policy: 12 months + 1 month grace = overdue after 13 months
        val_req7 = ValidationRequest(
            validation_type_id=type_comprehensive.value_id if type_comprehensive else type_initial.value_id,
            priority_id=priority_high.value_id if priority_high else priority_medium.value_id,
            current_status_id=status_approved.value_id,
            requestor_id=admin_user.user_id,
            target_completion_date=today - timedelta(days=430),
            completion_date=datetime.combine(today - timedelta(days=430), datetime.min.time()),
            trigger_reason="Annual comprehensive validation completed.",
            created_at=utc_now() - timedelta(days=480)
        )
        db.add(val_req7)
        db.flush()

        # Link model to validation request
        db.add(ValidationRequestModelVersion(
            request_id=val_req7.request_id,
            model_id=model7.model_id,
            version_id=version7.version_id
        ))
        db.flush()

        # Status history showing complete workflow
        prev_status_id = None
        for status_val, days_ago in [
            (status_intake, 480), (status_planning, 475), (status_in_progress, 460),
            (status_review, 445), (status_pending_approval, 435), (status_approved, 430)
        ]:
            if status_val:
                history = ValidationStatusHistory(
                    request_id=val_req7.request_id,
                    old_status_id=prev_status_id,
                    new_status_id=status_val.value_id,
                    changed_by_id=admin_user.user_id,
                    change_reason="Workflow progression",
                    changed_at=utc_now() - timedelta(days=days_ago)
                )
                db.add(history)
                prev_status_id = status_val.value_id

        outcome7 = ValidationOutcome(
            request_id=val_req7.request_id,
            overall_rating_id=outcome_fit.value_id if outcome_fit else outcome_not_fit.value_id,
            executive_summary="Model meets performance criteria. Next validation due in 12 months.",
            effective_date=today - timedelta(days=430),
            created_at=utc_now() - timedelta(days=430)
        )
        db.add(outcome7)

        results["models_created"].append({
            "model_id": model7.model_id,
            "name": model7.model_name,
            "status": "OVERDUE for revalidation (~14 months since last validation)"
        })

        # ========================================
        # MODEL 8: Tier 1 Model Critically Overdue
        # Last validation 18 months ago (significantly past grace)
        # ========================================
        model8 = Model(
            model_name="Interest Rate Risk ALM Model",
            description="Asset-Liability Management model for interest rate risk measurement and hedging strategy.",
            development_type="In-House",
            owner_id=admin_user.user_id,
            risk_tier_id=tier_1.value_id if tier_1 else None,
            usage_frequency_id=usage_monthly.value_id,
            status=ModelStatus.ACTIVE.value,
            created_at=utc_now() - timedelta(days=1000),
            updated_at=utc_now()
        )
        db.add(model8)
        db.flush()

        version8 = ModelVersion(
            model_id=model8.model_id,
            version_number="2.8",
            change_type="MINOR",
            change_description="Curve fitting methodology update",
            created_by_id=admin_user.user_id,
            production_date=today - timedelta(days=550),
            status="ACTIVE"
        )
        db.add(version8)
        db.flush()

        # Historical completed validation - 18 months ago (550 days)
        val_req8 = ValidationRequest(
            validation_type_id=type_comprehensive.value_id if type_comprehensive else type_initial.value_id,
            priority_id=priority_high.value_id if priority_high else priority_medium.value_id,
            current_status_id=status_approved.value_id,
            requestor_id=admin_user.user_id,
            target_completion_date=today - timedelta(days=550),
            completion_date=datetime.combine(today - timedelta(days=550), datetime.min.time()),
            trigger_reason="Comprehensive annual validation.",
            created_at=utc_now() - timedelta(days=600)
        )
        db.add(val_req8)
        db.flush()

        # Link model to validation request
        db.add(ValidationRequestModelVersion(
            request_id=val_req8.request_id,
            model_id=model8.model_id,
            version_id=version8.version_id
        ))
        db.flush()

        # Status history
        prev_status_id = None
        for status_val, days_ago in [
            (status_intake, 600), (status_planning, 595), (status_in_progress, 580),
            (status_review, 565), (status_pending_approval, 555), (status_approved, 550)
        ]:
            if status_val:
                history = ValidationStatusHistory(
                    request_id=val_req8.request_id,
                    old_status_id=prev_status_id,
                    new_status_id=status_val.value_id,
                    changed_by_id=admin_user.user_id,
                    change_reason="Workflow progression",
                    changed_at=utc_now() - timedelta(days=days_ago)
                )
                db.add(history)
                prev_status_id = status_val.value_id

        outcome8 = ValidationOutcome(
            request_id=val_req8.request_id,
            overall_rating_id=outcome_fit.value_id if outcome_fit else outcome_not_fit.value_id,
            executive_summary="Model approved. Annual revalidation required.",
            effective_date=today - timedelta(days=550),
            created_at=utc_now() - timedelta(days=550)
        )
        db.add(outcome8)

        results["models_created"].append({
            "model_id": model8.model_id,
            "name": model8.model_name,
            "status": "CRITICALLY OVERDUE (~18 months since last validation)"
        })

        # ========================================
        # MODEL 9: Model with Overdue Validation Request
        # Active validation but target_completion_date in the past
        # ========================================
        model9 = Model(
            model_name="Behavioral Scoring Model",
            description="Customer behavior scoring model for credit limit management and collections prioritization.",
            development_type="In-House",
            owner_id=regular_user.user_id if regular_user else admin_user.user_id,
            developer_id=admin_user.user_id,
            risk_tier_id=tier_2.value_id if tier_2 else None,
            usage_frequency_id=usage_daily.value_id,
            status=ModelStatus.ACTIVE.value,
            created_at=utc_now() - timedelta(days=600),
            updated_at=utc_now()
        )
        db.add(model9)
        db.flush()

        version9 = ModelVersion(
            model_id=model9.model_id,
            version_number="4.0",
            change_type="MAJOR",
            change_description="Machine learning model replacement",
            created_by_id=admin_user.user_id,
            production_date=today - timedelta(days=120),
            status="ACTIVE"
        )
        db.add(version9)
        db.flush()

        # Validation request that is overdue (target date 30 days ago, still in progress)
        val_req9 = ValidationRequest(
            validation_type_id=type_comprehensive.value_id if type_comprehensive else type_initial.value_id,
            priority_id=priority_high.value_id if priority_high else priority_medium.value_id,
            current_status_id=status_in_progress.value_id if status_in_progress else status_intake.value_id,
            requestor_id=admin_user.user_id,
            target_completion_date=today - timedelta(days=30),  # OVERDUE - target was 30 days ago
            trigger_reason="Major model change requires comprehensive validation - DELAYED due to resource constraints.",
            created_at=utc_now() - timedelta(days=120)
        )
        db.add(val_req9)
        db.flush()

        # Link model to validation request
        db.add(ValidationRequestModelVersion(
            request_id=val_req9.request_id,
            model_id=model9.model_id,
            version_id=version9.version_id
        ))
        db.flush()

        # Status history showing slow progression
        prev_status_id = None
        for status_val, days_ago in [
            (status_intake, 120), (status_planning, 100), (status_in_progress, 60)
        ]:
            if status_val:
                history = ValidationStatusHistory(
                    request_id=val_req9.request_id,
                    old_status_id=prev_status_id,
                    new_status_id=status_val.value_id,
                    changed_by_id=admin_user.user_id,
                    change_reason="Workflow progression" if days_ago > 60 else "Delayed due to resource constraints",
                    changed_at=utc_now() - timedelta(days=days_ago)
                )
                db.add(history)
                prev_status_id = status_val.value_id

        # Assign validator
        if validator_user:
            assignment9 = ValidationAssignment(
                request_id=val_req9.request_id,
                validator_id=validator_user.user_id,
                is_primary=True,
                is_reviewer=False,
                assignment_date=today - timedelta(days=95)
            )
            db.add(assignment9)

        results["models_created"].append({
            "model_id": model9.model_id,
            "name": model9.model_name,
            "status": "Validation request OVERDUE (target date 30 days ago, still in progress)"
        })

        # ========================================
        # MODEL 10: Model with Overdue Recommendations
        # Completed validation with recommendations past due date
        # ========================================
        model10 = Model(
            model_name="Prepayment Risk Model",
            description="Mortgage prepayment speed model for MBS portfolio valuation and hedging.",
            development_type="Third-Party",
            owner_id=admin_user.user_id,
            vendor_id=1,  # Assumes vendor exists
            risk_tier_id=tier_1.value_id if tier_1 else None,
            usage_frequency_id=usage_monthly.value_id,
            status=ModelStatus.ACTIVE.value,
            created_at=utc_now() - timedelta(days=700),
            updated_at=utc_now()
        )
        db.add(model10)
        db.flush()

        version10 = ModelVersion(
            model_id=model10.model_id,
            version_number="5.2",
            change_type="MINOR",
            change_description="Vendor model update with recalibrated parameters",
            created_by_id=admin_user.user_id,
            production_date=today - timedelta(days=180),
            status="ACTIVE"
        )
        db.add(version10)
        db.flush()

        # Completed validation with findings - 90 days ago
        val_req10 = ValidationRequest(
            validation_type_id=type_targeted.value_id if type_targeted else type_initial.value_id,
            priority_id=priority_high.value_id if priority_high else priority_medium.value_id,
            current_status_id=status_approved.value_id,
            requestor_id=admin_user.user_id,
            target_completion_date=today - timedelta(days=90),
            completion_date=datetime.combine(today - timedelta(days=90), datetime.min.time()),
            trigger_reason="Targeted validation of vendor model update completed with recommendations.",
            created_at=utc_now() - timedelta(days=150)
        )
        db.add(val_req10)
        db.flush()

        # Link model to validation request
        db.add(ValidationRequestModelVersion(
            request_id=val_req10.request_id,
            model_id=model10.model_id,
            version_id=version10.version_id
        ))
        db.flush()

        # Status history
        prev_status_id = None
        for status_val, days_ago in [
            (status_intake, 150), (status_planning, 145), (status_in_progress, 130),
            (status_review, 105), (status_pending_approval, 95), (status_approved, 90)
        ]:
            if status_val:
                history = ValidationStatusHistory(
                    request_id=val_req10.request_id,
                    old_status_id=prev_status_id,
                    new_status_id=status_val.value_id,
                    changed_by_id=admin_user.user_id,
                    change_reason="Workflow progression",
                    changed_at=utc_now() - timedelta(days=days_ago)
                )
                db.add(history)
                prev_status_id = status_val.value_id

        outcome10 = ValidationOutcome(
            request_id=val_req10.request_id,
            overall_rating_id=outcome_fit.value_id if outcome_fit else outcome_not_fit.value_id,
            executive_summary="Model approved with conditions. Critical recommendations require immediate attention.",
            effective_date=today - timedelta(days=90),
            created_at=utc_now() - timedelta(days=90)
        )
        db.add(outcome10)
        db.flush()

        # Create OVERDUE recommendations
        # Get task completion statuses for action plan tasks
        task_status_completed = get_taxonomy_value("Action Plan Task Status", "COMPLETED")
        task_status_in_progress = get_taxonomy_value("Action Plan Task Status", "IN_PROGRESS")

        if rec_status_open and rec_priority_high:
            # High priority recommendation - 45 days overdue
            rec_overdue1 = Recommendation(
                recommendation_code=f"REC-{today.year}-00003",
                validation_request_id=val_req10.request_id,
                model_id=model10.model_id,
                title="Implement independent model benchmarking",
                description="Develop internal benchmark model to validate vendor model outputs on quarterly basis.",
                priority_id=rec_priority_high.value_id,
                current_status_id=rec_status_open.value_id,
                created_by_id=validator_user.user_id if validator_user else admin_user.user_id,
                assigned_to_id=admin_user.user_id,
                original_target_date=today - timedelta(days=45),  # OVERDUE by 45 days
                current_target_date=today - timedelta(days=45),
                created_at=utc_now() - timedelta(days=90)
            )
            db.add(rec_overdue1)

            # Critical priority recommendation - 30 days overdue
            rec_overdue2 = Recommendation(
                recommendation_code=f"REC-{today.year}-00004",
                validation_request_id=val_req10.request_id,
                model_id=model10.model_id,
                title="Document vendor model limitations and assumptions",
                description="Create comprehensive documentation of vendor model limitations, key assumptions, and usage restrictions.",
                priority_id=rec_priority_high.value_id,
                current_status_id=rec_status_in_progress.value_id if rec_status_in_progress else rec_status_open.value_id,
                created_by_id=validator_user.user_id if validator_user else admin_user.user_id,
                assigned_to_id=regular_user.user_id if regular_user else admin_user.user_id,
                original_target_date=today - timedelta(days=30),  # OVERDUE by 30 days
                current_target_date=today - timedelta(days=30),
                created_at=utc_now() - timedelta(days=90)
            )
            db.add(rec_overdue2)

        if rec_status_in_progress and rec_priority_medium:
            # Medium priority recommendation - 15 days overdue
            rec_overdue3 = Recommendation(
                recommendation_code=f"REC-{today.year}-00005",
                validation_request_id=val_req10.request_id,
                model_id=model10.model_id,
                title="Enhance prepayment factor monitoring dashboard",
                description="Add real-time monitoring of prepayment factor deviations vs. vendor predictions.",
                priority_id=rec_priority_medium.value_id,
                current_status_id=rec_status_in_progress.value_id,
                created_by_id=validator_user.user_id if validator_user else admin_user.user_id,
                assigned_to_id=admin_user.user_id,
                original_target_date=today - timedelta(days=15),  # OVERDUE by 15 days
                current_target_date=today - timedelta(days=15),
                created_at=utc_now() - timedelta(days=90)
            )
            db.add(rec_overdue3)
            db.flush()

            # Add action plan tasks for the in-progress recommendation
            if task_status_completed:
                task_overdue = ActionPlanTask(
                    recommendation_id=rec_overdue3.recommendation_id,
                    task_order=1,
                    description="Document dashboard requirements, data sources, and alert thresholds.",
                    owner_id=admin_user.user_id,
                    target_date=today - timedelta(days=45),
                    completed_date=today - timedelta(days=40),
                    completion_status_id=task_status_completed.value_id,
                    completion_notes="Dashboard specifications completed and approved.",
                    created_at=utc_now() - timedelta(days=85)
                )
                db.add(task_overdue)

            if task_status_in_progress:
                task_overdue2 = ActionPlanTask(
                    recommendation_id=rec_overdue3.recommendation_id,
                    task_order=2,
                    description="Build data pipelines and backend services for dashboard.",
                    owner_id=admin_user.user_id,
                    target_date=today - timedelta(days=20),  # OVERDUE
                    completion_status_id=task_status_in_progress.value_id,
                    created_at=utc_now() - timedelta(days=50)
                )
                db.add(task_overdue2)

        results["models_created"].append({
            "model_id": model10.model_id,
            "name": model10.model_name,
            "status": "Completed validation with OVERDUE recommendations (15-45 days past due)"
        })

        db.commit()

        results["message"] = f"Successfully created {len(results['models_created'])} models with validations and related data"

    except Exception as e:
        db.rollback()
        results["errors"].append(str(e))
        raise HTTPException(status_code=500, detail=f"Seeding failed: {str(e)}")

    return results


@router.get("/data-summary")
def get_data_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict:
    """
    Get a summary of current transactional data counts.
    Useful for verifying reset and re-seed operations.
    """
    from app.models import (
        Model, ModelVersion, ValidationRequest, Recommendation,
        MonitoringPlan, MonitoringCycle, AuditLog, DecommissioningRequest,
        ModelRiskAssessment
    )

    return {
        "transactional_data": {
            "models": db.query(Model).count(),
            "model_versions": db.query(ModelVersion).count(),
            "validation_requests": db.query(ValidationRequest).count(),
            "recommendations": db.query(Recommendation).count(),
            "monitoring_plans": db.query(MonitoringPlan).count(),
            "monitoring_cycles": db.query(MonitoringCycle).count(),
            "risk_assessments": db.query(ModelRiskAssessment).count(),
            "decommissioning_requests": db.query(DecommissioningRequest).count(),
            "audit_logs": db.query(AuditLog).count(),
        }
    }
