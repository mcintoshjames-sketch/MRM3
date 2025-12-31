"""Backfill monitoring result outcomes using versioned thresholds."""
import argparse
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the app to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.monitoring_backfill import backfill_monitoring_results_outcomes


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill monitoring result outcomes.")
    parser.add_argument("--apply", action="store_true", help="Apply updates (default is dry-run).")
    parser.add_argument("--user-id", type=int, default=None, help="User ID for audit log entries.")
    parser.add_argument("--cycle-id", type=int, default=None, help="Limit backfill to a single cycle.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of results processed.")
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/mrm_inventory")
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)

    db = Session()
    try:
        summary = backfill_monitoring_results_outcomes(
            db=db,
            dry_run=not args.apply,
            user_id=args.user_id,
            cycle_id=args.cycle_id,
            limit=args.limit,
        )
        mode = "APPLY" if args.apply else "DRY-RUN"
        print(f"[{mode}] Backfill summary: {summary}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
