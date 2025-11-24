"""
Import FRY 14 reporting data from FRY_ARRAY.json into database.

Usage:
    python import_fry_data.py
"""
import json
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.fry import FryReport, FrySchedule, FryMetricGroup, FryLineItem
from app.core.config import settings

def import_fry_data():
    """Import FRY 14 data from JSON file."""

    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Load JSON data
        # Script is in /app/import_fry_data.py, JSON is in /app/FRY_ARRAY.json
        json_path = Path(__file__).parent / "FRY_ARRAY.json"
        if not json_path.exists():
            raise FileNotFoundError(f"Cannot find FRY_ARRAY.json at {json_path}")

        with open(json_path, 'r') as f:
            fry_data = json.load(f)

        print(f"Loaded {len(fry_data)} entries from FRY_ARRAY.json")

        # Track created objects to avoid duplicates
        reports = {}  # report_code -> FryReport
        schedules = {}  # (report_code, schedule_code) -> FrySchedule
        metric_groups = {}  # (report_code, schedule_code, metric_group_name) -> FryMetricGroup

        # Process each entry
        for entry in fry_data:
            report_code = entry["report"]
            schedule_code = entry["schedule"]
            metric_group_name = entry["metric_group"]
            model_driven = entry["model_driven"]
            rationale = entry.get("rationale", "")
            line_items = entry.get("model_estimates_line_items", [])

            # Create or get Report
            if report_code not in reports:
                existing_report = db.query(FryReport).filter(
                    FryReport.report_code == report_code
                ).first()

                if existing_report:
                    reports[report_code] = existing_report
                    print(f"  Found existing report: {report_code}")
                else:
                    report = FryReport(
                        report_code=report_code,
                        description=f"Federal Reserve Board {report_code} Reporting",
                        is_active=True
                    )
                    db.add(report)
                    db.flush()
                    reports[report_code] = report
                    print(f"  Created report: {report_code}")

            report = reports[report_code]

            # Create or get Schedule
            schedule_key = (report_code, schedule_code)
            if schedule_key not in schedules:
                existing_schedule = db.query(FrySchedule).filter(
                    FrySchedule.report_id == report.report_id,
                    FrySchedule.schedule_code == schedule_code
                ).first()

                if existing_schedule:
                    schedules[schedule_key] = existing_schedule
                    print(f"    Found existing schedule: {report_code} - {schedule_code}")
                else:
                    schedule = FrySchedule(
                        report_id=report.report_id,
                        schedule_code=schedule_code,
                        description=None,
                        is_active=True
                    )
                    db.add(schedule)
                    db.flush()
                    schedules[schedule_key] = schedule
                    print(f"    Created schedule: {report_code} - {schedule_code}")

            schedule = schedules[schedule_key]

            # Create or get Metric Group
            metric_group_key = (report_code, schedule_code, metric_group_name)
            if metric_group_key not in metric_groups:
                existing_metric_group = db.query(FryMetricGroup).filter(
                    FryMetricGroup.schedule_id == schedule.schedule_id,
                    FryMetricGroup.metric_group_name == metric_group_name
                ).first()

                if existing_metric_group:
                    metric_groups[metric_group_key] = existing_metric_group
                    print(f"      Found existing metric group: {metric_group_name}")
                else:
                    metric_group = FryMetricGroup(
                        schedule_id=schedule.schedule_id,
                        metric_group_name=metric_group_name,
                        model_driven=model_driven,
                        rationale=rationale,
                        is_active=True
                    )
                    db.add(metric_group)
                    db.flush()
                    metric_groups[metric_group_key] = metric_group
                    print(f"      Created metric group: {metric_group_name} (model_driven={model_driven})")

            metric_group = metric_groups[metric_group_key]

            # Create Line Items (if any)
            if line_items:
                for idx, line_item_text in enumerate(line_items):
                    # Check if line item already exists
                    existing_line_item = db.query(FryLineItem).filter(
                        FryLineItem.metric_group_id == metric_group.metric_group_id,
                        FryLineItem.line_item_text == line_item_text
                    ).first()

                    if not existing_line_item:
                        line_item = FryLineItem(
                            metric_group_id=metric_group.metric_group_id,
                            line_item_text=line_item_text,
                            sort_order=idx + 1
                        )
                        db.add(line_item)
                        print(f"        Created line item: {line_item_text[:60]}...")

        # Commit all changes
        db.commit()
        print("\n✅ FRY 14 data import completed successfully!")

        # Print summary
        total_reports = db.query(FryReport).count()
        total_schedules = db.query(FrySchedule).count()
        total_metric_groups = db.query(FryMetricGroup).count()
        total_line_items = db.query(FryLineItem).count()

        print(f"\nSummary:")
        print(f"  Reports: {total_reports}")
        print(f"  Schedules: {total_schedules}")
        print(f"  Metric Groups: {total_metric_groups}")
        print(f"  Line Items: {total_line_items}")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during import: {e}", file=sys.stderr)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import_fry_data()
