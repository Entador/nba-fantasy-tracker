"""Run the notification watchers. Cron entrypoint (GitHub Actions, hourly).

Decides who to notify (injury alerts + deadline reminders) and fans out web push.
Real sends need VAPID_PRIVATE_KEY / VAPID_CLAIMS_SUB in the environment; without
them the WebPushNotifier raises and each send is logged status=failed.

Usage:
  poetry run python scripts/run_watchers.py              # both watchers
  poetry run python scripts/run_watchers.py --injuries   # injury alerts only
  poetry run python scripts/run_watchers.py --deadline   # deadline reminders only
  poetry run python scripts/run_watchers.py --dry-run    # plan + print, no send/log
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.database import SessionLocal  # noqa: E402
from notifications import watchers  # noqa: E402


def _print_planned(label: str, planned) -> None:
    print(f"{label}: {len(planned)} notification(s) planned")
    for p in planned:
        print(f"  → user_id={p.user_id} {p.type.value}: {p.body}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--injuries", action="store_true", help="Run injury watcher only.")
    parser.add_argument("--deadline", action="store_true", help="Run deadline watcher only.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan and print without sending or logging.",
    )
    args = parser.parse_args()

    # No flag = run both.
    run_injuries = args.injuries or not args.deadline
    run_deadline = args.deadline or not args.injuries

    db = SessionLocal()
    try:
        if run_injuries:
            today = date.today()
            if args.dry_run:
                _print_planned("Injury", watchers.plan_injury_notifications(db, today))
            else:
                _print_planned("Injury", watchers.run_injury_watcher(db, today))

        if run_deadline:
            now = datetime.now(timezone.utc)
            if args.dry_run:
                _print_planned("Deadline", watchers.plan_deadline_notifications(db, now))
            else:
                _print_planned("Deadline", watchers.run_deadline_watcher(db, now))
    finally:
        db.close()


if __name__ == "__main__":
    main()
