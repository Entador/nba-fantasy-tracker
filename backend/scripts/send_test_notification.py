"""Quick sanity check: fan out a fake notification over every active device.

Uses FakeNotifier by default so it runs without VAPID keys or a real browser
subscription — the point is to prove the DB → device → notifier wiring, not to
land a real push.

Usage:
  poetry run python scripts/send_test_notification.py
  poetry run python scripts/send_test_notification.py --seed   # create a stub
                                                                # device if none
  poetry run python scripts/send_test_notification.py --cleanup-seed
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import User, UserDevice  # noqa: E402
from models.database import SessionLocal  # noqa: E402
from notifications.notifier import FakeNotifier, NotifierError  # noqa: E402

SEED_TOKEN = "__test_seed_token__"


def seed_device(db) -> UserDevice | None:
    user = db.query(User).filter(User.deleted_at.is_(None)).first()
    if user is None:
        print("No user in DB to attach a seed device to.")
        return None
    device = (
        db.query(UserDevice).filter(UserDevice.push_token == SEED_TOKEN).first()
    )
    if device is None:
        device = UserDevice(
            user_id=user.id,
            push_token=SEED_TOKEN,
            platform="web",
            last_seen=datetime.now(timezone.utc),
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        print(f"Seeded device id={device.id} for user_id={user.id}.")
    else:
        print(f"Seed device already exists (id={device.id}).")
    return device


def cleanup_seed(db) -> None:
    n = db.query(UserDevice).filter(UserDevice.push_token == SEED_TOKEN).delete()
    db.commit()
    print(f"Removed {n} seed device row(s).")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Insert a stub device if none exist (cleanup with --cleanup-seed).",
    )
    parser.add_argument(
        "--cleanup-seed", action="store_true", help="Remove the stub device and exit."
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.cleanup_seed:
            cleanup_seed(db)
            return
        if args.seed:
            seed_device(db)

        devices = (
            db.query(UserDevice).filter(UserDevice.revoked_at.is_(None)).all()
        )
        print(f"Active devices: {len(devices)}")
        if not devices:
            print("Nothing to send to. Re-run with --seed to insert a stub device.")
            return

        notifier = FakeNotifier()
        for d in devices:
            try:
                notifier.send(
                    d.push_token,
                    "Fantasy test alert",
                    "This is a wiring check, not a real notification.",
                    {"kind": "wiring_check", "device_id": d.id},
                )
                print(
                    f"  ✓ device id={d.id} user_id={d.user_id} platform={d.platform}"
                )
            except NotifierError as e:
                print(f"  ✗ device id={d.id} failed: {e}")

        print("\nRecorded payloads:")
        for n in notifier.sent:
            print(f"  → token={n.token[:40]!r} title={n.title!r} data={json.dumps(n.data)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
