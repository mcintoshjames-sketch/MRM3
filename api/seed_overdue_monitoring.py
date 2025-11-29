"""
Seed script for overdue monitoring cycle - enables UAT of Admin Dashboard overdue monitoring widget.
Creates a cycle that is overdue (report_due_date in the past, status not APPROVED).
"""
import os
import sys
from datetime import date, datetime, timedelta

# Add the app to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import (
    User, Model, MonitoringPlan, MonitoringTeam, MonitoringPlanMetric,
    MonitoringCycle, MonitoringResult, MonitoringPlanVersion, MonitoringPlanMetricSnapshot,
    KpmCategory, Kpm
)
from app.models.model import ModelStatus
from app.schemas.monitoring import MonitoringCycleStatusEnum

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/mrm_inventory")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def seed_overdue_monitoring():
    db = Session()

    try:
        # Get admin user
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        if not admin:
            print("ERROR: admin@example.com not found. Run main seed first.")
            return

        # Get John Smith as data provider
        john = db.query(User).filter(User.email == "john.smith@contoso.com").first()
        if not john:
            john = admin
            print("Note: john.smith@contoso.com not found, using admin as data provider")

        # Get or create a monitoring team
        team = db.query(MonitoringTeam).filter(MonitoringTeam.name == "Overdue Test Team").first()
        if not team:
            team = MonitoringTeam(
                name="Overdue Test Team",
                description="Team for testing overdue monitoring cycles"
            )
            db.add(team)
            db.flush()
            print(f"Created team: {team.name}")

        # Get a model to monitor
        model = db.query(Model).filter(Model.status != ModelStatus.RETIRED).first()
        if not model:
            print("ERROR: No models found. Run main seed first.")
            return

        print(f"Using model: {model.model_name}")

        # Get or create PSI KPM
        psi_category = db.query(KpmCategory).filter(KpmCategory.code == "STABILITY").first()
        if not psi_category:
            psi_category = KpmCategory(
                code="STABILITY",
                name="Stability Metrics",
                description="Population and characteristic stability metrics",
                sort_order=1
            )
            db.add(psi_category)
            db.flush()

        psi_kpm = db.query(Kpm).filter(Kpm.name == "PSI (Population Stability Index)").first()
        if not psi_kpm:
            psi_kpm = Kpm(
                category_id=psi_category.category_id,
                name="PSI (Population Stability Index)",
                description="Measures shift in score distribution over time. Lower is better.",
                evaluation_type="Quantitative",
                is_active=True,
                sort_order=1
            )
            db.add(psi_kpm)
            db.flush()

        # Check if we already have an overdue test plan
        plan_name = "Overdue Monitoring Test Plan"
        plan = db.query(MonitoringPlan).filter(MonitoringPlan.name == plan_name).first()

        if plan:
            # Check if there's already an overdue cycle
            existing_overdue = db.query(MonitoringCycle).filter(
                MonitoringCycle.plan_id == plan.plan_id,
                MonitoringCycle.status != MonitoringCycleStatusEnum.APPROVED
            ).first()
            if existing_overdue:
                print(f"Overdue cycle already exists for plan '{plan_name}'")
                print(f"  Cycle ID: {existing_overdue.cycle_id}")
                print(f"  Status: {existing_overdue.status}")
                print(f"  Report Due: {existing_overdue.report_due_date}")
                return
        else:
            # Create new plan
            plan = MonitoringPlan(
                name=plan_name,
                description="Test plan for verifying overdue monitoring dashboard widget",
                frequency="Monthly",
                monitoring_team_id=team.team_id,
                data_provider_user_id=john.user_id,
                reporting_lead_days=15,
                is_active=True,
                next_submission_due_date=date.today() - timedelta(days=30)  # Already past due
            )
            db.add(plan)
            db.flush()

            # Associate model with plan
            plan.models = [model]
            db.flush()

        print(f"Plan: {plan.name} (ID: {plan.plan_id})")

        # Create plan metric if needed
        existing_metric = db.query(MonitoringPlanMetric).filter(
            MonitoringPlanMetric.plan_id == plan.plan_id
        ).first()

        if not existing_metric:
            psi_metric = MonitoringPlanMetric(
                plan_id=plan.plan_id,
                kpm_id=psi_kpm.kpm_id,
                yellow_max=0.10,
                red_max=0.25,
                sort_order=1,
                is_active=True
            )
            db.add(psi_metric)
            db.flush()
            print("Created PSI metric for plan")

        # Create an overdue cycle - report was due 14 days ago, still in DATA_COLLECTION
        today = date.today()
        period_start = today - timedelta(days=60)  # Period started 2 months ago
        period_end = today - timedelta(days=30)    # Period ended 1 month ago
        submission_due = today - timedelta(days=21)  # Submission was due 3 weeks ago
        report_due = today - timedelta(days=14)      # Report was due 2 weeks ago

        overdue_cycle = MonitoringCycle(
            plan_id=plan.plan_id,
            period_start_date=period_start,
            period_end_date=period_end,
            submission_due_date=submission_due,
            report_due_date=report_due,
            status=MonitoringCycleStatusEnum.DATA_COLLECTION,  # Still collecting data!
            assigned_to_user_id=john.user_id,
            notes="This cycle is overdue - awaiting data submission from model owner"
        )
        db.add(overdue_cycle)
        db.flush()

        # Add a partial result to show work in progress
        metric = db.query(MonitoringPlanMetric).filter(
            MonitoringPlanMetric.plan_id == plan.plan_id
        ).first()

        if metric:
            result = MonitoringResult(
                cycle_id=overdue_cycle.cycle_id,
                plan_metric_id=metric.metric_id,
                model_id=model.model_id,
                numeric_value=0.18,  # Yellow zone
                calculated_outcome="YELLOW",
                narrative="PSI showing moderate drift - investigation in progress",
                entered_by_user_id=john.user_id,
                entered_at=datetime.now() - timedelta(days=10)
            )
            db.add(result)

        db.commit()

        days_overdue = (today - report_due).days

        print("\n" + "="*60)
        print("OVERDUE MONITORING CYCLE SEEDED SUCCESSFULLY")
        print("="*60)
        print(f"\nPlan: {plan.name}")
        print(f"Plan ID: {plan.plan_id}")
        print(f"Cycle ID: {overdue_cycle.cycle_id}")
        print(f"Model: {model.model_name}")
        print(f"Data Provider: {john.full_name if john else 'Admin'}")
        print(f"Team: {team.name}")
        print(f"\nCycle Details:")
        print(f"  Period: {period_start} to {period_end}")
        print(f"  Submission Due: {submission_due}")
        print(f"  Report Due: {report_due}")
        print(f"  Status: {overdue_cycle.status.value}")
        print(f"  DAYS OVERDUE: {days_overdue}")
        print(f"\nTo verify in Admin Dashboard:")
        print("  1. Login as admin@example.com")
        print("  2. Check 'Overdue Monitoring' KPI card shows >= 1")
        print("  3. Scroll to 'Overdue Monitoring Cycles' widget")
        print(f"  4. Should see cycle with {days_overdue} days overdue")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    seed_overdue_monitoring()
