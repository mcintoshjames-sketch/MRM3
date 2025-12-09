"""Seed synthetic monitoring data to demonstrate PDF report features.

This script creates a monitoring cycle with varied outcomes (GREEN, YELLOW, RED)
to showcase the breach analysis and trend chart features of the PDF report.
"""

import sys
import os
from datetime import datetime, timedelta
from random import uniform, choice, seed as random_seed

# Add the app to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.monitoring import (
    MonitoringPlan, MonitoringCycle, MonitoringResult, MonitoringPlanMetric,
    MonitoringCycleApproval, MonitoringCycleStatus
)
from app.models.user import User
from app.core.monitoring_constants import OUTCOME_GREEN, OUTCOME_YELLOW, OUTCOME_RED


def seed_demo_monitoring_data():
    """Seed demonstration data with varied outcomes."""
    # Set seed for reproducibility
    random_seed(42)
    
    db: Session = SessionLocal()

    try:
        # Get Plan 2 (Credit Risk Model Performance) which has 5 metrics and 4 models
        plan = db.query(MonitoringPlan).filter(MonitoringPlan.plan_id == 2).first()
        if not plan:
            print("Plan 2 not found!")
            return

        print(f"Using plan: {plan.name}")
        print(f"  - Models: {len(plan.models)}")

        # Get all metrics for this plan
        metrics = db.query(MonitoringPlanMetric).filter(
            MonitoringPlanMetric.plan_id == plan.plan_id
        ).all()
        print(f"  - Metrics: {len(metrics)}")

        # Find an approved cycle to update, or use cycle 6
        cycle = db.query(MonitoringCycle).filter(
            MonitoringCycle.cycle_id == 6
        ).first()

        if not cycle:
            print("Cycle 6 not found!")
            return

        print(f"\nUpdating cycle {cycle.cycle_id} ({cycle.period_start_date} to {cycle.period_end_date})")

        # Delete existing results for this cycle
        db.query(MonitoringResult).filter(MonitoringResult.cycle_id == cycle.cycle_id).delete()
        db.commit()
        print("Cleared existing results")

        # Get admin user for entered_by
        admin = db.query(User).filter(User.email == "admin@example.com").first()

        # Create varied results for each metric and model combination
        result_count = 0
        green_count = 0
        yellow_count = 0
        red_count = 0

        # Define outcome distribution for each metric (to create interesting patterns)
        metric_outcomes = {}
        for i, metric in enumerate(metrics):
            # Assign a tendency to each metric
            if i == 0:
                metric_outcomes[metric.metric_id] = "mostly_green"
            elif i == 1:
                metric_outcomes[metric.metric_id] = "some_yellow"
            elif i == 2:
                metric_outcomes[metric.metric_id] = "some_red"
            elif i == 3:
                metric_outcomes[metric.metric_id] = "mixed"
            else:
                metric_outcomes[metric.metric_id] = "mostly_green"

        for metric in metrics:
            tendency = metric_outcomes.get(metric.metric_id, "mostly_green")

            for model in plan.models:
                # Determine outcome based on metric tendency
                if tendency == "mostly_green":
                    outcome = choice([OUTCOME_GREEN] * 8 + [OUTCOME_YELLOW] * 2)
                elif tendency == "some_yellow":
                    outcome = choice([OUTCOME_GREEN] * 4 + [OUTCOME_YELLOW] * 5 + [OUTCOME_RED])
                elif tendency == "some_red":
                    outcome = choice([OUTCOME_GREEN] * 3 + [OUTCOME_YELLOW] * 3 + [OUTCOME_RED] * 4)
                else:  # mixed
                    outcome = choice([OUTCOME_GREEN, OUTCOME_YELLOW, OUTCOME_RED])

                # Generate realistic numeric value based on outcome and thresholds
                yellow_max = metric.yellow_max or 0.15
                red_max = metric.red_max or 0.20
                
                if outcome == OUTCOME_GREEN:
                    # Value within acceptable range (below yellow threshold)
                    value = uniform(0.05, yellow_max * 0.85)
                    green_count += 1
                elif outcome == OUTCOME_YELLOW:
                    # Value in yellow zone (between yellow and red thresholds)
                    value = uniform(yellow_max, red_max * 0.95)
                    yellow_count += 1
                else:  # RED
                    # Value in red zone (above red threshold)
                    value = uniform(red_max * 1.05, red_max * 1.4)
                    red_count += 1

                # Create narrative for breaches
                narrative = None
                if outcome == OUTCOME_YELLOW:
                    narrative = f"Metric value of {value:.4f} exceeded yellow threshold of {yellow_max:.2f}. This deviation is being monitored closely. The variance is attributed to recent market volatility and seasonal portfolio adjustments. A remediation plan has been initiated with expected resolution within 60 days. Weekly monitoring escalation in place."
                elif outcome == OUTCOME_RED:
                    narrative = f"CRITICAL: Metric value of {value:.4f} exceeded red threshold of {red_max:.2f}, triggering immediate review by Model Risk Committee. Root cause analysis completed - identified data quality issue in upstream credit bureau feed combined with unexpected portfolio concentration shift. Escalated to Senior Risk Officer on {(datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')}. Corrective actions: (1) Data remediation completed, (2) Enhanced monitoring implemented, (3) Model recalibration scheduled for next quarter."

                # Create the result
                result = MonitoringResult(
                    cycle_id=cycle.cycle_id,
                    plan_metric_id=metric.metric_id,
                    model_id=model.model_id,
                    numeric_value=round(value, 6),
                    calculated_outcome=outcome,
                    narrative=narrative,
                    entered_by_user_id=admin.user_id
                )
                db.add(result)
                result_count += 1

        db.commit()
        print(f"\nCreated {result_count} results:")
        print(f"  - GREEN:  {green_count}")
        print(f"  - YELLOW: {yellow_count}")
        print(f"  - RED:    {red_count}")

        # Also seed some historical cycles with trend data
        print("\nSeeding historical trend data for trend charts...")

        # Get historical cycles (cycles 3, 4, 5 are also APPROVED for plan 2)
        historical_cycles = db.query(MonitoringCycle).filter(
            MonitoringCycle.plan_id == 2,
            MonitoringCycle.cycle_id.in_([3, 4, 5])
        ).order_by(MonitoringCycle.period_end_date).all()

        for hist_cycle in historical_cycles:
            # Clear existing results
            db.query(MonitoringResult).filter(MonitoringResult.cycle_id == hist_cycle.cycle_id).delete()

            # Create results with a trend pattern (values gradually increasing toward breach)
            cycle_offset = historical_cycles.index(hist_cycle)  # 0, 1, 2

            for metric in metrics:
                yellow_max = metric.yellow_max or 0.15
                red_max = metric.red_max or 0.20
                
                for model in plan.models:
                    # Create a trending pattern - values gradually increase over time
                    # This shows metrics trending toward breach in cycle 6
                    base_value = 0.06 + (cycle_offset * 0.025)  # 0.06, 0.085, 0.11
                    value = base_value + uniform(-0.015, 0.015)

                    # Determine outcome based on value vs thresholds
                    if value >= red_max:
                        outcome = OUTCOME_RED
                    elif value >= yellow_max:
                        outcome = OUTCOME_YELLOW
                    else:
                        outcome = OUTCOME_GREEN

                    result = MonitoringResult(
                        cycle_id=hist_cycle.cycle_id,
                        plan_metric_id=metric.metric_id,
                        model_id=model.model_id,
                        numeric_value=round(value, 6),
                        calculated_outcome=outcome,
                        narrative=None,
                        entered_by_user_id=admin.user_id
                    )
                    db.add(result)

        db.commit()
        print(f"Seeded trend data for {len(historical_cycles)} historical cycles")

        print("\n" + "="*60)
        print("✅ Demo data seeded successfully!")
        print("="*60)
        print(f"\nTo generate the PDF report with breach data, use:")
        print(f"  GET /monitoring/cycles/6/report/pdf")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_monitoring_data()
