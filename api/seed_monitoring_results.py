"""
Seed script for monitoring cycle results - enables UAT of trend assessment.
Creates multiple completed cycles with realistic PSI and other metric results.
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

def seed_monitoring_results():
    db = Session()

    try:
        # Get admin user
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        if not admin:
            print("ERROR: admin@example.com not found. Run main seed first.")
            return

        # Get or create a monitoring team
        team = db.query(MonitoringTeam).first()
        if not team:
            team = MonitoringTeam(
                name="Model Performance Team",
                description="Responsible for ongoing model monitoring"
            )
            db.add(team)
            db.flush()
            print(f"Created team: {team.name}")

        # Get models to monitor
        models = db.query(Model).filter(Model.status != ModelStatus.RETIRED).limit(3).all()
        if not models:
            print("ERROR: No models found. Run main seed first.")
            return

        print(f"Found {len(models)} models to monitor")

        # Get or create KPM categories and KPMs
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

        performance_category = db.query(KpmCategory).filter(KpmCategory.code == "PERFORMANCE").first()
        if not performance_category:
            performance_category = KpmCategory(
                code="PERFORMANCE",
                name="Performance Metrics",
                description="Model accuracy and discrimination metrics",
                sort_order=2
            )
            db.add(performance_category)
            db.flush()

        # Create KPMs if they don't exist
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

        gini_kpm = db.query(Kpm).filter(Kpm.name == "Gini Coefficient").first()
        if not gini_kpm:
            gini_kpm = Kpm(
                category_id=performance_category.category_id,
                name="Gini Coefficient",
                description="Measures model discriminatory power. Higher is better.",
                evaluation_type="Quantitative",
                is_active=True,
                sort_order=1
            )
            db.add(gini_kpm)
            db.flush()

        ks_kpm = db.query(Kpm).filter(Kpm.name == "KS Statistic").first()
        if not ks_kpm:
            ks_kpm = Kpm(
                category_id=performance_category.category_id,
                name="KS Statistic",
                description="Kolmogorov-Smirnov statistic - maximum separation between good/bad cumulative distributions.",
                evaluation_type="Quantitative",
                is_active=True,
                sort_order=2
            )
            db.add(ks_kpm)
            db.flush()

        data_quality_kpm = db.query(Kpm).filter(Kpm.name == "Data Quality Assessment").first()
        if not data_quality_kpm:
            data_quality_kpm = Kpm(
                category_id=psi_category.category_id,
                name="Data Quality Assessment",
                description="Qualitative assessment of input data quality and completeness.",
                evaluation_type="Qualitative",
                is_active=True,
                sort_order=2
            )
            db.add(data_quality_kpm)
            db.flush()

        db.commit()
        print("KPM categories and KPMs created/verified")

        # Create or get monitoring plan
        plan_name = "Credit Risk Model Monitoring - UAT"
        plan = db.query(MonitoringPlan).filter(MonitoringPlan.name == plan_name).first()

        if plan:
            # Delete existing cycles and results for clean UAT
            print(f"Cleaning up existing plan: {plan_name}")
            db.query(MonitoringResult).filter(
                MonitoringResult.cycle_id.in_(
                    db.query(MonitoringCycle.cycle_id).filter(MonitoringCycle.plan_id == plan.plan_id)
                )
            ).delete(synchronize_session=False)
            db.query(MonitoringCycle).filter(MonitoringCycle.plan_id == plan.plan_id).delete()
            db.query(MonitoringPlanMetricSnapshot).filter(
                MonitoringPlanMetricSnapshot.version_id.in_(
                    db.query(MonitoringPlanVersion.version_id).filter(MonitoringPlanVersion.plan_id == plan.plan_id)
                )
            ).delete(synchronize_session=False)
            db.query(MonitoringPlanVersion).filter(MonitoringPlanVersion.plan_id == plan.plan_id).delete()
            db.query(MonitoringPlanMetric).filter(MonitoringPlanMetric.plan_id == plan.plan_id).delete()
            db.commit()
        else:
            plan = MonitoringPlan(
                name=plan_name,
                description="Quarterly monitoring of credit risk scorecards - seeded for UAT",
                frequency="Quarterly",
                monitoring_team_id=team.team_id,
                data_provider_user_id=admin.user_id,
                reporting_lead_days=30,
                is_active=True,
                next_submission_due_date=date.today() + timedelta(days=30)
            )
            db.add(plan)
            db.flush()

        # Associate models with plan
        plan.models = models[:2]  # First 2 models
        db.flush()

        print(f"Plan: {plan.name} (ID: {plan.plan_id})")
        print(f"Models in plan: {[m.model_name for m in plan.models]}")

        # Create plan metrics with thresholds
        # PSI: GREEN < 0.10, YELLOW 0.10-0.25, RED > 0.25 (lower is better)
        # For "lower is better": use yellow_max and red_max only
        psi_metric = MonitoringPlanMetric(
            plan_id=plan.plan_id,
            kpm_id=psi_kpm.kpm_id,
            yellow_max=0.10,  # <= 0.10 is GREEN
            red_max=0.25,     # > 0.25 is RED
            sort_order=1,
            is_active=True
        )
        db.add(psi_metric)

        # Gini: GREEN > 0.45, YELLOW 0.35-0.45, RED < 0.35 (higher is better)
        # For "higher is better": use yellow_min and red_min only
        gini_metric = MonitoringPlanMetric(
            plan_id=plan.plan_id,
            kpm_id=gini_kpm.kpm_id,
            yellow_min=0.45,  # >= 0.45 is GREEN
            red_min=0.35,     # < 0.35 is RED
            sort_order=2,
            is_active=True
        )
        db.add(gini_metric)

        # KS: GREEN > 0.35, YELLOW 0.25-0.35, RED < 0.25 (higher is better)
        # For "higher is better": use yellow_min and red_min only
        ks_metric = MonitoringPlanMetric(
            plan_id=plan.plan_id,
            kpm_id=ks_kpm.kpm_id,
            yellow_min=0.35,  # >= 0.35 is GREEN
            red_min=0.25,     # < 0.25 is RED
            sort_order=3,
            is_active=True
        )
        db.add(ks_metric)

        # Data Quality - Qualitative
        dq_metric = MonitoringPlanMetric(
            plan_id=plan.plan_id,
            kpm_id=data_quality_kpm.kpm_id,
            qualitative_guidance="Assess data completeness, accuracy, and timeliness against specifications.",
            sort_order=4,
            is_active=True
        )
        db.add(dq_metric)

        db.flush()
        print(f"Created 4 plan metrics")

        # Publish a version
        version = MonitoringPlanVersion(
            plan_id=plan.plan_id,
            version_number=1,
            version_name="Initial Thresholds",
            description="Baseline monitoring thresholds for credit risk models",
            effective_date=date.today() - timedelta(days=365),
            published_by_user_id=admin.user_id,
            published_at=datetime.now() - timedelta(days=365),
            is_active=True
        )
        db.add(version)
        db.flush()

        # Create metric snapshots for the version
        for metric in [psi_metric, gini_metric, ks_metric, dq_metric]:
            kpm = db.query(Kpm).filter(Kpm.kpm_id == metric.kpm_id).first()
            category = db.query(KpmCategory).filter(KpmCategory.category_id == kpm.category_id).first()
            snapshot = MonitoringPlanMetricSnapshot(
                version_id=version.version_id,
                original_metric_id=metric.metric_id,
                kpm_id=metric.kpm_id,
                kpm_name=kpm.name,
                kpm_category_name=category.name if category else None,
                evaluation_type=kpm.evaluation_type,
                yellow_min=metric.yellow_min,
                yellow_max=metric.yellow_max,
                red_min=metric.red_min,
                red_max=metric.red_max,
                qualitative_guidance=metric.qualitative_guidance,
                sort_order=metric.sort_order
            )
            db.add(snapshot)

        db.flush()
        print(f"Published version v{version.version_number}")

        # Create 6 quarters of historical cycles with results
        # This gives us 18 months of trend data
        quarters = [
            ("Q1 2024", date(2024, 1, 1), date(2024, 3, 31)),
            ("Q2 2024", date(2024, 4, 1), date(2024, 6, 30)),
            ("Q3 2024", date(2024, 7, 1), date(2024, 9, 30)),
            ("Q4 2024", date(2024, 10, 1), date(2024, 12, 31)),
            ("Q1 2025", date(2025, 1, 1), date(2025, 3, 31)),
            ("Q2 2025", date(2025, 4, 1), date(2025, 6, 30)),
        ]

        # Simulated metric values showing trends
        # PSI: Generally stable with one spike
        # Gini: Gradual decline over time
        # KS: Stable with slight variation
        model_results = {
            models[0].model_id: {
                "psi": [0.05, 0.07, 0.08, 0.22, 0.12, 0.09],  # Spike in Q4 2024
                "gini": [0.52, 0.50, 0.48, 0.45, 0.43, 0.41],  # Gradual decline
                "ks": [0.38, 0.37, 0.36, 0.35, 0.34, 0.33],  # Slight decline
                "dq": ["GREEN", "GREEN", "GREEN", "YELLOW", "GREEN", "GREEN"]
            },
            models[1].model_id: {
                "psi": [0.04, 0.05, 0.06, 0.08, 0.07, 0.06],  # Very stable
                "gini": [0.48, 0.47, 0.46, 0.44, 0.42, 0.40],  # Gradual decline
                "ks": [0.42, 0.41, 0.40, 0.39, 0.38, 0.36],  # Stable
                "dq": ["GREEN", "GREEN", "GREEN", "GREEN", "GREEN", "YELLOW"]
            }
        }

        for i, (quarter_name, start_date, end_date) in enumerate(quarters):
            submission_due = end_date + timedelta(days=15)
            report_due = end_date + timedelta(days=45)

            cycle = MonitoringCycle(
                plan_id=plan.plan_id,
                period_start_date=start_date,
                period_end_date=end_date,
                submission_due_date=submission_due,
                report_due_date=report_due,
                status=MonitoringCycleStatusEnum.APPROVED,
                assigned_to_user_id=admin.user_id,
                plan_version_id=version.version_id,
                version_locked_at=start_date,
                version_locked_by_user_id=admin.user_id,
                submitted_at=submission_due - timedelta(days=2),
                submitted_by_user_id=admin.user_id,
                completed_at=report_due - timedelta(days=5),
                completed_by_user_id=admin.user_id,
                notes=f"{quarter_name} monitoring cycle - completed"
            )
            db.add(cycle)
            db.flush()

            # Add results for each model
            for model in models[:2]:
                model_id = model.model_id
                if model_id not in model_results:
                    continue

                results_data = model_results[model_id]

                # PSI result
                psi_value = results_data["psi"][i]
                if psi_value < 0.10:
                    psi_outcome = "GREEN"
                elif psi_value <= 0.25:
                    psi_outcome = "YELLOW"
                else:
                    psi_outcome = "RED"

                psi_result = MonitoringResult(
                    cycle_id=cycle.cycle_id,
                    plan_metric_id=psi_metric.metric_id,
                    model_id=model_id,
                    numeric_value=psi_value,
                    calculated_outcome=psi_outcome,
                    narrative=f"PSI for {quarter_name}: {psi_value:.3f}",
                    entered_by_user_id=admin.user_id,
                    entered_at=submission_due - timedelta(days=3)
                )
                db.add(psi_result)

                # Gini result
                gini_value = results_data["gini"][i]
                if gini_value > 0.40:
                    gini_outcome = "GREEN"
                elif gini_value >= 0.30:
                    gini_outcome = "YELLOW"
                else:
                    gini_outcome = "RED"

                gini_result = MonitoringResult(
                    cycle_id=cycle.cycle_id,
                    plan_metric_id=gini_metric.metric_id,
                    model_id=model_id,
                    numeric_value=gini_value,
                    calculated_outcome=gini_outcome,
                    narrative=f"Gini coefficient for {quarter_name}: {gini_value:.2f}",
                    entered_by_user_id=admin.user_id,
                    entered_at=submission_due - timedelta(days=3)
                )
                db.add(gini_result)

                # KS result
                ks_value = results_data["ks"][i]
                if ks_value > 0.35:
                    ks_outcome = "GREEN"
                elif ks_value >= 0.25:
                    ks_outcome = "YELLOW"
                else:
                    ks_outcome = "RED"

                ks_result = MonitoringResult(
                    cycle_id=cycle.cycle_id,
                    plan_metric_id=ks_metric.metric_id,
                    model_id=model_id,
                    numeric_value=ks_value,
                    calculated_outcome=ks_outcome,
                    narrative=f"KS statistic for {quarter_name}: {ks_value:.2f}",
                    entered_by_user_id=admin.user_id,
                    entered_at=submission_due - timedelta(days=3)
                )
                db.add(ks_result)

                # Data Quality result (qualitative)
                dq_outcome = results_data["dq"][i]
                dq_result = MonitoringResult(
                    cycle_id=cycle.cycle_id,
                    plan_metric_id=dq_metric.metric_id,
                    model_id=model_id,
                    calculated_outcome=dq_outcome,
                    narrative=f"Data quality assessment for {quarter_name}: All data sources validated with {'minor issues' if dq_outcome == 'YELLOW' else 'no issues'} identified.",
                    entered_by_user_id=admin.user_id,
                    entered_at=submission_due - timedelta(days=3)
                )
                db.add(dq_result)

            db.flush()
            print(f"  Created cycle: {quarter_name} with {len(models[:2]) * 4} results")

        db.commit()

        print("\n" + "="*60)
        print("MONITORING RESULTS SEEDED SUCCESSFULLY")
        print("="*60)
        print(f"\nPlan: {plan.name}")
        print(f"Plan ID: {plan.plan_id}")
        print(f"Models: {', '.join([m.model_name for m in models[:2]])}")
        print(f"Metrics: PSI, Gini, KS, Data Quality")
        print(f"Cycles: 6 quarters (Q1 2024 - Q2 2025)")
        print(f"Total Results: {6 * 2 * 4} (6 cycles × 2 models × 4 metrics)")
        print("\nTrend highlights:")
        print("  - PSI: Generally stable, spike in Q4 2024 for Model 1")
        print("  - Gini: Gradual decline over time (potential model decay)")
        print("  - KS: Slight decline but within acceptable range")
        print("  - Data Quality: Mostly GREEN with occasional YELLOW")
        print("\nTo test the History tab:")
        print(f"  1. Navigate to: http://localhost:5174/monitoring-plans/{plan.plan_id}")
        print("  2. Click on the 'History' tab")
        print("  3. View Performance Summary and export cycle data")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    seed_monitoring_results()
