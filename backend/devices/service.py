"""Device registration and notification-prefs business logic."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models import NotificationPref, User, UserDevice


def register_device(
    db: Session, user: User, push_token: str, platform: str
) -> UserDevice:
    """Upsert by push_token. Re-registering the same token from another account
    transfers ownership (a phone shared between accounts shouldn't fan out both).
    """
    now = datetime.now(timezone.utc)
    device = db.query(UserDevice).filter(UserDevice.push_token == push_token).first()
    if device is None:
        device = UserDevice(
            user_id=user.id,
            push_token=push_token,
            platform=platform,
            last_seen=now,
        )
        db.add(device)
    else:
        device.user_id = user.id
        device.platform = platform
        device.last_seen = now
        device.revoked_at = None
    db.commit()
    db.refresh(device)
    return device


def revoke_device(db: Session, user: User, device_id: int) -> None:
    device = (
        db.query(UserDevice)
        .filter(UserDevice.id == device_id, UserDevice.user_id == user.id)
        .first()
    )
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    if device.revoked_at is None:
        device.revoked_at = datetime.now(timezone.utc)
        db.commit()


def get_or_create_prefs(db: Session, user: User) -> NotificationPref:
    prefs = (
        db.query(NotificationPref)
        .filter(NotificationPref.user_id == user.id)
        .first()
    )
    if prefs is None:
        prefs = NotificationPref(user_id=user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


def update_prefs(
    db: Session,
    user: User,
    injury_alerts: bool | None,
    deadline_alerts: bool | None,
) -> NotificationPref:
    prefs = get_or_create_prefs(db, user)
    if injury_alerts is not None:
        prefs.injury_alerts = injury_alerts
    if deadline_alerts is not None:
        prefs.deadline_alerts = deadline_alerts
    db.commit()
    db.refresh(prefs)
    return prefs
