"""
Seed script for generating synthetic monitoring data with historical cycles.

This script creates realistic performance monitoring data including:
- 4 monitoring plans with different scopes and frequencies
- Historical cycles spanning 18 months
- Mix of GREEN, YELLOW, and RED outcomes with realistic breach patterns
- Cycles in various workflow states (mostly APPROVED, some in-progress)

Run with: docker compose exec api python seed_monitoring_demo.py
"""

from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import random
from typing import Dict, List, Optional, Any
from decimal import Decimal

from app.core.database import SessionLocal
from app.core.time import utc_now
from app.models import User, Region
from app.models.model import Model
from app.models.kpm import Kpm, KpmCategory
from app.models.monitoring import (
    MonitoringTeam, MonitoringPlan, MonitoringPlanMetric,
    MonitoringPlanVersion, MonitoringPlanMetricSnapshot, MonitoringPlanModelSnapshot,
    MonitoringCycle, MonitoringResult, MonitoringCycleApproval,
    monitoring_team_members, monitoring_plan_models
)
from app.models.taxonomy import TaxonomyValue

# Set random seed for reproducibility
random.seed(42)


# ============================================================================
# PLAN CONFIGURATIONS
# ============================================================================

PLAN_CONFIGS = [
    {
        'name': 'Credit Risk Model Performance',
        'description': 'Quarterly monitoring of credit risk model discrimination, calibration, and stability metrics.',
        'frequency': 'Quarterly',
        'model_indices': [0, 1, 2, 3],  # First 4 models
        'metrics': [
            {
                'kpm_name': 'ROC AUC',
                'yellow_min': 0.72, 'yellow_max': None,
                'red_min': 0.65, 'red_max': None,
                'base_value': 0.79, 'std_dev': 0.015,
                'trend_per_model': {1: -0.012}  # Model index 1 degrades over time
            },
            {
                'kpm_name': 'Kolmogorov-Smirnov (KS)',
                'yellow_min': 0.25, 'yellow_max': None,
                'red_min': 0.18, 'red_max': None,
                'base_value': 0.38, 'std_dev': 0.025,
                'trend_per_model': {}
            },
            {
                'kpm_name': 'Brier Score',
                'yellow_min': None, 'yellow_max': 0.22,
                'red_min': None, 'red_max': 0.28,
                'base_value': 0.15, 'std_dev': 0.02,
                'trend_per_model': {1: 0.008}  # Degrades (higher is worse)
            },
            {
                'kpm_name': 'Score Distribution PSI',
                'yellow_min': None, 'yellow_max': 0.12,
                'red_min': None, 'red_max': 0.20,
                'base_value': 0.06, 'std_dev': 0.025,
                'trend_per_model': {}
            },
            {
                'kpm_name': 'Calibration Slope',
                'yellow_min': 0.85, 'yellow_max': 1.15,
                'red_min': 0.75, 'red_max': 1.25,
                'base_value': 1.0, 'std_dev': 0.05,
                'trend_per_model': {}
            },
        ],
        'num_cycles': 6,
        'current_cycle_status': 'DATA_COLLECTION',
    },
    {
        'name': 'Data Quality Monitoring',
        'description': 'Monthly monitoring of input data quality metrics across model population.',
        'frequency': 'Monthly',
        'model_indices': [4, 5, 6, 7],  # Models 5-8
        'metrics': [
            {
                'kpm_name': 'Missing Data Rate',
                'yellow_min': None, 'yellow_max': 0.03,
                'red_min': None, 'red_max': 0.05,
                'base_value': 0.012, 'std_dev': 0.006,
                'trend_per_model': {},
                'breach_cycles': {5: 0.065}  # Force RED in cycle 5 (June)
            },
            {
                'kpm_name': 'New Category Rate',
                'yellow_min': None, 'yellow_max': 0.02,
                'red_min': None, 'red_max': 0.04,
                'base_value': 0.008, 'std_dev': 0.004,
                'trend_per_model': {}
            },
            {
                'kpm_name': 'Feature Distribution Drift (PSI)',
                'yellow_min': None, 'yellow_max': 0.10,
                'red_min': None, 'red_max': 0.18,
                'base_value': 0.05, 'std_dev': 0.025,
                'trend_per_model': {}
            },
        ],
        'num_cycles': 10,
        'current_cycle_status': 'UNDER_REVIEW',
    },
    {
        'name': 'Model Governance & Attestations',
        'description': 'Semi-annual qualitative assessment of model governance, attestations, and policy compliance.',
        'frequency': 'Semi-Annual',
        'model_indices': [8, 9, 10],  # Models 9-11
        'metrics': [
            {
                'kpm_name': 'Model Owner Attestation',
                'is_qualitative': True,
                'evaluation_type': 'Outcome Only',
                'outcome_weights': {'GREEN': 0.75, 'YELLOW': 0.20, 'RED': 0.05}
            },
            {
                'kpm_name': 'Business Strategy Alignment',
                'is_qualitative': True,
                'evaluation_type': 'Qualitative',
                'outcome_weights': {'GREEN': 0.80, 'YELLOW': 0.15, 'RED': 0.05}
            },
            {
                'kpm_name': 'Policy Limit Compliance',
                'is_qualitative': True,
                'evaluation_type': 'Qualitative',
                'outcome_weights': {'GREEN': 0.70, 'YELLOW': 0.20, 'RED': 0.10},
                'breach_cycles': {1: 'RED'}  # Force RED in cycle 1
            },
            {
                'kpm_name': 'Validation Condition Compliance',
                'is_qualitative': True,
                'evaluation_type': 'Qualitative',
                'outcome_weights': {'GREEN': 0.75, 'YELLOW': 0.20, 'RED': 0.05}
            },
        ],
        'num_cycles': 3,
        'current_cycle_status': 'PENDING_APPROVAL',
    },
    {
        'name': 'Model Stability & Interpretability',
        'description': 'Quarterly monitoring of model stability and interpretability metrics.',
        'frequency': 'Quarterly',
        'model_indices': [11, 12, 13],  # Models 12-14
        'metrics': [
            {
                'kpm_name': 'Score Distribution PSI',
                'yellow_min': None, 'yellow_max': 0.10,
                'red_min': None, 'red_max': 0.18,
                'base_value': 0.05, 'std_dev': 0.02,
                'trend_per_model': {}
            },
            {
                'kpm_name': 'Performance Drift (Metric Change)',
                'yellow_min': -0.03, 'yellow_max': None,
                'red_min': -0.05, 'red_max': None,
                'base_value': -0.01, 'std_dev': 0.012,
                'trend_per_model': {0: -0.008},  # Model 0 shows increasing drift
                'breach_cycles': {2: -0.06}  # Force RED in cycle 2
            },
            {
                'kpm_name': 'Feature Importance',
                'yellow_min': None, 'yellow_max': 0.40,
                'red_min': None, 'red_max': 0.55,
                'base_value': 0.28, 'std_dev': 0.05,
                'trend_per_model': {}
            },
            {
                'kpm_name': 'Surrogate Model Fidelity',
                'yellow_min': 0.75, 'yellow_max': None,
                'red_min': 0.60, 'red_max': None,
                'base_value': 0.85, 'std_dev': 0.04,
                'trend_per_model': {}
            },
        ],
        'num_cycles': 5,
        'current_cycle_status': 'DATA_COLLECTION',
    },
]

# Frequency to relativedelta mapping
FREQUENCY_DELTAS = {
    'Monthly': relativedelta(months=1),
    'Quarterly': relativedelta(months=3),
    'Semi-Annual': relativedelta(months=6),
    'Annual': relativedelta(years=1),
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_outcome(value: float, metric_config: dict) -> str:
    """Calculate outcome (GREEN, YELLOW, RED) based on thresholds."""
    if value is None:
        return "N/A"

    # Check red thresholds first (highest severity)
    red_min = metric_config.get('red_min')
    red_max = metric_config.get('red_max')
    if red_min is not None and value < red_min:
        return "RED"
    if red_max is not None and value > red_max:
        return "RED"

    # Check yellow thresholds
    yellow_min = metric_config.get('yellow_min')
    yellow_max = metric_config.get('yellow_max')
    if yellow_min is not None and value < yellow_min:
        return "YELLOW"
    if yellow_max is not None and value > yellow_max:
        return "YELLOW"

    return "GREEN"


def generate_metric_value(config: dict, cycle_num: int, model_idx: int) -> float:
    """Generate a realistic metric value with trend, noise, and optional breach injection."""
    # Check for forced breach
    breach_cycles = config.get('breach_cycles', {})
    if cycle_num in breach_cycles:
        return breach_cycles[cycle_num]

    base = config['base_value']
    std = config['std_dev']

    # Apply model-specific trend
    trend_per_model = config.get('trend_per_model', {})
    trend = trend_per_model.get(model_idx, 0)
    drift = trend * cycle_num

    # Add random noise
    noise = random.gauss(0, std)

    value = base + drift + noise

    # Ensure value stays in reasonable bounds
    if config.get('red_max') is not None:
        value = min(value, config['red_max'] * 1.1)
    if config.get('red_min') is not None:
        value = max(value, config['red_min'] * 0.9)

    return round(value, 4)


def generate_qualitative_outcome(config: dict, cycle_num: int) -> str:
    """Generate a qualitative outcome based on weights or forced breach."""
    # Check for forced breach
    breach_cycles = config.get('breach_cycles', {})
    if cycle_num in breach_cycles:
        return breach_cycles[cycle_num]

    weights = config.get('outcome_weights', {'GREEN': 0.75, 'YELLOW': 0.20, 'RED': 0.05})
    outcomes = list(weights.keys())
    probabilities = list(weights.values())

    return random.choices(outcomes, weights=probabilities, k=1)[0]


def get_period_dates(frequency: str, cycle_num: int, base_date: date) -> tuple:
    """Calculate period start and end dates for a cycle."""
    delta = FREQUENCY_DELTAS[frequency]

    # Work backwards from base_date
    period_end = base_date - (delta * cycle_num)
    period_start = period_end - delta + timedelta(days=1)

    return period_start, period_end


def generate_narrative(outcome: str, kpm_name: str) -> str:
    """Generate a realistic narrative for qualitative metrics."""
    narratives = {
        'GREEN': [
            f"{kpm_name} assessment completed with satisfactory results. All criteria met.",
            f"No material concerns identified for {kpm_name}. Performance within expected parameters.",
            f"{kpm_name} review indicates strong compliance with policy requirements.",
        ],
        'YELLOW': [
            f"{kpm_name} shows minor deviations requiring attention. Monitoring enhanced.",
            f"Some concerns noted for {kpm_name}. Remediation plan in progress.",
            f"{kpm_name} assessment indicates borderline performance. Action items identified.",
        ],
        'RED': [
            f"{kpm_name} breach identified. Immediate escalation required.",
            f"Significant concerns with {kpm_name}. Formal remediation plan required.",
            f"{kpm_name} failed to meet policy requirements. Management attention required.",
        ],
    }
    return random.choice(narratives.get(outcome, narratives['GREEN']))


# ============================================================================
# MAIN SEEDING FUNCTIONS
# ============================================================================

def get_existing_data(db):
    """Query database for models, users, KPMs to ensure consistency."""
    models = db.query(Model).order_by(Model.model_id).limit(20).all()
    users = db.query(User).all()
    admin = db.query(User).filter(User.email == "admin@example.com").first()
    validator = db.query(User).filter(User.email == "validator@example.com").first()

    kpms = db.query(Kpm).all()
    kpm_by_name = {k.name: k for k in kpms}

    regions = db.query(Region).all()

    # Get qualitative outcome taxonomy values (GREEN, YELLOW, RED)
    outcome_values = db.query(TaxonomyValue).filter(
        TaxonomyValue.code.in_(['GREEN', 'YELLOW', 'RED'])
    ).all()
    outcome_by_code = {v.code: v for v in outcome_values}

    return {
        'models': models,
        'users': users,
        'admin': admin,
        'validator': validator,
        'kpm_by_name': kpm_by_name,
        'regions': regions,
        'outcome_by_code': outcome_by_code,
    }


def create_monitoring_team(db, name: str, description: str, member_ids: List[int]) -> MonitoringTeam:
    """Create a monitoring team with members."""
    # Check if team already exists
    existing = db.query(MonitoringTeam).filter(MonitoringTeam.name == name).first()
    if existing:
        print(f"  Team '{name}' already exists (id={existing.team_id})")
        return existing

    team = MonitoringTeam(
        name=name,
        description=description,
        is_active=True,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(team)
    db.flush()

    # Add members
    for user_id in member_ids:
        db.execute(
            monitoring_team_members.insert().values(
                team_id=team.team_id,
                user_id=user_id
            )
        )

    print(f"  Created team '{name}' (id={team.team_id}) with {len(member_ids)} members")
    return team


def create_monitoring_plan(db, config: dict, team: MonitoringTeam, models: List[Model],
                          kpm_by_name: dict, data_provider: User) -> MonitoringPlan:
    """Create a monitoring plan with metrics and models."""
    # Check if plan already exists
    existing = db.query(MonitoringPlan).filter(MonitoringPlan.name == config['name']).first()
    if existing:
        print(f"  Plan '{config['name']}' already exists (id={existing.plan_id})")
        return existing

    plan = MonitoringPlan(
        name=config['name'],
        description=config['description'],
        frequency=config['frequency'],
        monitoring_team_id=team.team_id,
        data_provider_user_id=data_provider.user_id,
        reporting_lead_days=30,
        is_active=True,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(plan)
    db.flush()

    # Add models to plan
    plan_models = [models[i] for i in config['model_indices'] if i < len(models)]
    for model in plan_models:
        db.execute(
            monitoring_plan_models.insert().values(
                plan_id=plan.plan_id,
                model_id=model.model_id
            )
        )

    # Add metrics to plan
    for i, metric_config in enumerate(config['metrics']):
        kpm_name = metric_config['kpm_name']
        kpm = kpm_by_name.get(kpm_name)
        if not kpm:
            print(f"    WARNING: KPM '{kpm_name}' not found, skipping")
            continue

        metric = MonitoringPlanMetric(
            plan_id=plan.plan_id,
            kpm_id=kpm.kpm_id,
            yellow_min=metric_config.get('yellow_min'),
            yellow_max=metric_config.get('yellow_max'),
            red_min=metric_config.get('red_min'),
            red_max=metric_config.get('red_max'),
            qualitative_guidance=metric_config.get('qualitative_guidance'),
            sort_order=i + 1,
            is_active=True,
        )
        db.add(metric)

    db.flush()
    print(f"  Created plan '{config['name']}' (id={plan.plan_id}) with {len(config['metrics'])} metrics and {len(plan_models)} models")
    return plan


def publish_plan_version(db, plan: MonitoringPlan, admin: User, effective_date: date) -> MonitoringPlanVersion:
    """Publish a version of the plan, creating metric and model snapshots."""
    # Check if version already exists
    existing = db.query(MonitoringPlanVersion).filter(
        MonitoringPlanVersion.plan_id == plan.plan_id,
        MonitoringPlanVersion.version_number == 1
    ).first()
    if existing:
        print(f"    Version already exists for plan {plan.plan_id}")
        return existing

    version = MonitoringPlanVersion(
        plan_id=plan.plan_id,
        version_number=1,
        version_name="Initial Version",
        description="Initial published version for monitoring",
        effective_date=effective_date,
        published_by_user_id=admin.user_id,
        published_at=datetime.combine(effective_date, datetime.min.time()),
        is_active=True,
        created_at=utc_now(),
    )
    db.add(version)
    db.flush()

    # Create metric snapshots
    metrics = db.query(MonitoringPlanMetric).filter(
        MonitoringPlanMetric.plan_id == plan.plan_id,
        MonitoringPlanMetric.is_active == True
    ).all()

    for metric in metrics:
        kpm = db.query(Kpm).filter(Kpm.kpm_id == metric.kpm_id).first()
        category = db.query(KpmCategory).filter(KpmCategory.category_id == kpm.category_id).first()

        snapshot = MonitoringPlanMetricSnapshot(
            version_id=version.version_id,
            original_metric_id=metric.metric_id,
            kpm_id=metric.kpm_id,
            yellow_min=metric.yellow_min,
            yellow_max=metric.yellow_max,
            red_min=metric.red_min,
            red_max=metric.red_max,
            qualitative_guidance=metric.qualitative_guidance,
            sort_order=metric.sort_order,
            is_active=metric.is_active,
            kpm_name=kpm.name,
            kpm_category_name=category.name if category else None,
            evaluation_type=kpm.evaluation_type,
            created_at=utc_now(),
        )
        db.add(snapshot)

    # Create model snapshots
    plan_model_ids = db.execute(
        monitoring_plan_models.select().where(monitoring_plan_models.c.plan_id == plan.plan_id)
    ).fetchall()

    for row in plan_model_ids:
        model = db.query(Model).filter(Model.model_id == row.model_id).first()
        if model:
            model_snapshot = MonitoringPlanModelSnapshot(
                version_id=version.version_id,
                model_id=model.model_id,
                model_name=model.model_name,
                created_at=utc_now(),
            )
            db.add(model_snapshot)

    db.flush()
    print(f"    Published version {version.version_id} for plan {plan.plan_id}")
    return version


def create_cycle_with_results(db, plan: MonitoringPlan, version: MonitoringPlanVersion,
                             config: dict, cycle_num: int, period_start: date, period_end: date,
                             admin: User, regions: List[Region], kpm_by_name: dict,
                             outcome_by_code: dict, is_historical: bool = True,
                             target_status: str = 'APPROVED') -> MonitoringCycle:
    """Create a monitoring cycle with results and approvals."""

    submission_due = period_end + timedelta(days=15)
    report_due = period_end + timedelta(days=45)

    # Determine status and timestamps based on whether this is historical
    if is_historical and target_status == 'APPROVED':
        status = 'APPROVED'
        submitted_at = datetime.combine(period_end + timedelta(days=10), datetime.min.time())
        completed_at = datetime.combine(period_end + timedelta(days=40), datetime.min.time())
        version_locked_at = datetime.combine(period_start, datetime.min.time())
    elif target_status == 'PENDING_APPROVAL':
        status = 'PENDING_APPROVAL'
        submitted_at = datetime.combine(period_end + timedelta(days=10), datetime.min.time())
        completed_at = None
        version_locked_at = datetime.combine(period_start, datetime.min.time())
    elif target_status == 'UNDER_REVIEW':
        status = 'UNDER_REVIEW'
        submitted_at = datetime.combine(period_end + timedelta(days=10), datetime.min.time())
        completed_at = None
        version_locked_at = datetime.combine(period_start, datetime.min.time())
    else:  # DATA_COLLECTION or PENDING
        status = target_status
        submitted_at = None
        completed_at = None
        version_locked_at = datetime.combine(period_start, datetime.min.time()) if status != 'PENDING' else None

    cycle = MonitoringCycle(
        plan_id=plan.plan_id,
        period_start_date=period_start,
        period_end_date=period_end,
        submission_due_date=submission_due,
        report_due_date=report_due,
        status=status,
        plan_version_id=version.version_id if version_locked_at else None,
        version_locked_at=version_locked_at,
        version_locked_by_user_id=admin.user_id if version_locked_at else None,
        submitted_at=submitted_at,
        submitted_by_user_id=admin.user_id if submitted_at else None,
        completed_at=completed_at,
        completed_by_user_id=admin.user_id if completed_at else None,
        report_url=f'https://reports.example.com/monitoring/{plan.name.replace(" ", "_")}/cycle_{cycle_num}.pdf' if status in ['PENDING_APPROVAL', 'APPROVED'] else None,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(cycle)
    db.flush()

    # Get plan models
    plan_model_ids = db.execute(
        monitoring_plan_models.select().where(monitoring_plan_models.c.plan_id == plan.plan_id)
    ).fetchall()
    plan_models = [db.query(Model).filter(Model.model_id == row.model_id).first() for row in plan_model_ids]

    # Get plan metrics
    plan_metrics = db.query(MonitoringPlanMetric).filter(
        MonitoringPlanMetric.plan_id == plan.plan_id,
        MonitoringPlanMetric.is_active == True
    ).all()

    # Generate results for each metric and model
    result_count = 0
    for metric in plan_metrics:
        kpm = db.query(Kpm).filter(Kpm.kpm_id == metric.kpm_id).first()
        metric_config = next((m for m in config['metrics'] if m['kpm_name'] == kpm.name), None)

        if not metric_config:
            continue

        for model_idx, model in enumerate(plan_models):
            if not model:
                continue

            # Skip some results for in-progress cycles
            if status == 'DATA_COLLECTION' and random.random() < 0.3:
                continue

            is_qualitative = metric_config.get('is_qualitative', False)

            if is_qualitative:
                outcome = generate_qualitative_outcome(metric_config, cycle_num)
                outcome_value = outcome_by_code.get(outcome)

                result = MonitoringResult(
                    cycle_id=cycle.cycle_id,
                    plan_metric_id=metric.metric_id,
                    model_id=model.model_id,
                    numeric_value=None,
                    outcome_value_id=outcome_value.value_id if outcome_value else None,
                    calculated_outcome=outcome,
                    narrative=generate_narrative(outcome, kpm.name),
                    entered_by_user_id=admin.user_id,
                    entered_at=submitted_at or utc_now(),
                    updated_at=utc_now(),
                )
            else:
                numeric_value = generate_metric_value(metric_config, cycle_num, model_idx)
                outcome = calculate_outcome(numeric_value, metric_config)

                result = MonitoringResult(
                    cycle_id=cycle.cycle_id,
                    plan_metric_id=metric.metric_id,
                    model_id=model.model_id,
                    numeric_value=numeric_value,
                    outcome_value_id=None,
                    calculated_outcome=outcome,
                    narrative=None,
                    entered_by_user_id=admin.user_id,
                    entered_at=submitted_at or utc_now(),
                    updated_at=utc_now(),
                )

            db.add(result)
            result_count += 1

    # Create approvals for completed or pending approval cycles
    if status in ['APPROVED', 'PENDING_APPROVAL']:
        # Global approval
        global_approval = MonitoringCycleApproval(
            cycle_id=cycle.cycle_id,
            approval_type='Global',
            is_required=True,
            approval_status='Approved' if status == 'APPROVED' else 'Pending',
            approver_id=admin.user_id if status == 'APPROVED' else None,
            approved_at=completed_at - timedelta(days=2) if completed_at else None,
            comments='Monitoring results reviewed and approved.' if status == 'APPROVED' else None,
            created_at=utc_now(),
        )
        db.add(global_approval)

        # Regional approvals (US and UK)
        for region in regions[:2]:
            regional = MonitoringCycleApproval(
                cycle_id=cycle.cycle_id,
                approval_type='Regional',
                region_id=region.region_id,
                is_required=True,
                approval_status='Approved' if status == 'APPROVED' else 'Pending',
                approver_id=admin.user_id if status == 'APPROVED' else None,
                represented_region_id=region.region_id if status == 'APPROVED' else None,
                approved_at=completed_at - timedelta(days=1) if completed_at else None,
                comments=f'{region.name} regional approval complete.' if status == 'APPROVED' else None,
                created_at=utc_now(),
            )
            db.add(regional)

    db.flush()
    return cycle, result_count


def seed_monitoring_data():
    """Main function to seed all monitoring data."""
    db = SessionLocal()

    try:
        print("\n" + "="*70)
        print("SEEDING MONITORING DEMO DATA")
        print("="*70)

        # Get existing data
        print("\n1. Querying existing database entities...")
        data = get_existing_data(db)

        if not data['models']:
            print("ERROR: No models found in database. Please run main seed first.")
            return

        if not data['admin']:
            print("ERROR: Admin user not found. Please run main seed first.")
            return

        print(f"   Found {len(data['models'])} models")
        print(f"   Found {len(data['users'])} users")
        print(f"   Found {len(data['kpm_by_name'])} KPMs")
        print(f"   Found {len(data['regions'])} regions")

        # Create teams and plans
        print("\n2. Creating monitoring teams and plans...")

        total_cycles = 0
        total_results = 0
        breach_counts = {'GREEN': 0, 'YELLOW': 0, 'RED': 0}

        for plan_idx, plan_config in enumerate(PLAN_CONFIGS):
            print(f"\n--- Plan {plan_idx + 1}: {plan_config['name']} ---")

            # Create team
            team = create_monitoring_team(
                db,
                name=f"{plan_config['name']} Team",
                description=f"Monitoring team for {plan_config['name']}",
                member_ids=[data['admin'].user_id, data['validator'].user_id] if data['validator'] else [data['admin'].user_id]
            )

            # Create plan
            plan = create_monitoring_plan(
                db, plan_config, team, data['models'],
                data['kpm_by_name'], data['admin']
            )

            # Calculate base date for cycles (working backwards from today)
            today = date.today()
            base_date = today.replace(day=1)  # First of current month

            # Publish version with effective date 18 months ago
            effective_date = base_date - relativedelta(months=18)
            version = publish_plan_version(db, plan, data['admin'], effective_date)

            # Generate cycles
            num_cycles = plan_config['num_cycles']
            current_status = plan_config.get('current_cycle_status', 'DATA_COLLECTION')

            print(f"    Generating {num_cycles} cycles...")

            for cycle_num in range(num_cycles):
                period_start, period_end = get_period_dates(
                    plan_config['frequency'],
                    num_cycles - 1 - cycle_num,  # Work backwards
                    base_date
                )

                # Determine status for this cycle
                if cycle_num == num_cycles - 1:  # Current cycle
                    target_status = current_status
                    is_historical = False
                elif cycle_num == num_cycles - 2 and current_status in ['DATA_COLLECTION', 'PENDING']:
                    # Previous cycle might be pending approval
                    target_status = 'PENDING_APPROVAL'
                    is_historical = False
                else:
                    target_status = 'APPROVED'
                    is_historical = True

                cycle, result_count = create_cycle_with_results(
                    db, plan, version, plan_config, cycle_num,
                    period_start, period_end, data['admin'],
                    data['regions'], data['kpm_by_name'],
                    data['outcome_by_code'], is_historical, target_status
                )

                total_cycles += 1
                total_results += result_count

                # Count breaches
                results = db.query(MonitoringResult).filter(
                    MonitoringResult.cycle_id == cycle.cycle_id
                ).all()
                for r in results:
                    if r.calculated_outcome in breach_counts:
                        breach_counts[r.calculated_outcome] += 1

            db.commit()

        # Final summary
        print("\n" + "="*70)
        print("SEEDING COMPLETE - SUMMARY")
        print("="*70)
        print(f"\nTotal cycles created: {total_cycles}")
        print(f"Total results created: {total_results}")
        print(f"\nOutcome distribution:")
        print(f"  GREEN:  {breach_counts['GREEN']} ({100*breach_counts['GREEN']/max(total_results,1):.1f}%)")
        print(f"  YELLOW: {breach_counts['YELLOW']} ({100*breach_counts['YELLOW']/max(total_results,1):.1f}%)")
        print(f"  RED:    {breach_counts['RED']} ({100*breach_counts['RED']/max(total_results,1):.1f}%)")

        print("\nVerify with:")
        print("  - GET /monitoring/plans")
        print("  - GET /monitoring/admin-overview")
        print("  - GET /monitoring/plans/{id}/cycles")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_monitoring_data()
