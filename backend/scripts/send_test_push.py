"""Send a test web push to a user's active devices — manual end-to-end check.

Use after enabling notifications in the browser (which registers a `web` device)
to confirm the full path works: VAPID keys → pywebpush → service worker → toast.
Needs VAPID_PRIVATE_KEY / VAPID_CLAIMS_SUB in the environment, same as the cron job.

Usage:
  poetry run python scripts/send_test_push.py you@example.com
  poetry run python scripts/send_test_push.py you@example.com --body "Custom message"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import User, UserDevice  # noqa: E402
from models.database import SessionLocal  # noqa: E402
from notifications.notifier import NotifierError, get_notifier  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("email", help="Email of the user to push to.")
    parser.add_argument(
        "--title", default="Test notification", help="Notification title."
    )
    parser.add_argument(
        "--body",
        default="If you can read this, web push works 🎉",
        help="Notification body.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == args.email).first()
        if user is None:
            sys.exit(f"No user with email {args.email!r}.")

        devices = (
            db.query(UserDevice)
            .filter(UserDevice.user_id == user.id, UserDevice.revoked_at.is_(None))
            .all()
        )
        if not devices:
            sys.exit(f"User {args.email!r} has no active devices.")

        payload = {"kind": "test", "url": "/"}
        for device in devices:
            try:
                get_notifier(device.platform).send(
                    device.push_token, args.title, args.body, payload
                )
                print(f"  → sent to device {device.id} ({device.platform})")
            except NotifierError as e:
                print(f"  ✗ device {device.id} ({device.platform}) failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
