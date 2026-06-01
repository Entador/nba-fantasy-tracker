"""Notification watchers: decide who to notify, then fan out the push.

Two alert types, users-only (guests never get push):
- injury_alert: the user's pick for tonight is on the injury report.
- deadline_reminder: the user hasn't picked and tip-off is under an hour away.

Design: pure `plan_*` functions return a list of PlannedNotification (trivially
unit-testable — "given DB state, who gets what"); `dispatch` does the effectful
fan-out + logging. `notification_log` is the dedup + audit backstop, so re-running
the hourly job never double-sends. Dedup is filtered in Python (not JSON-path SQL)
so SQLite tests and Postgres prod behave identically.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import (
    Game,
    NotificationLog,
    NotificationPref,
    NotificationStatus,
    NotificationType,
    Owner,
    Pick,
    Player,
    User,
    UserDevice,
)
from notifications.notifier import NotifierError, get_notifier

# A player "on the report" — any of these statuses warrants an alert.
LISTED_STATUSES = {"Probable", "Questionable", "Doubtful", "Out"}

# How long before the first tip-off we nudge users who haven't picked.
DEADLINE_WINDOW = timedelta(hours=1)

NotifierFactory = Callable[[str], Any]


@dataclass
class PlannedNotification:
    user_id: int
    type: NotificationType
    title: str
    body: str
    payload: dict  # carries player_id / game_date for dedup + client routing


# --- Injury watcher ------------------------------------------------------

def plan_injury_notifications(db: Session, game_date: date) -> list[PlannedNotification]:
    """Users whose pick for `game_date` is on the injury report and not yet alerted."""
    rows = (
        db.query(Pick, Player, Owner.user_id)
        .join(Player, Pick.player_id == Player.id)  # inner join drops skips (player_id NULL)
        .join(Owner, Pick.owner_id == Owner.id)
        .join(User, Owner.user_id == User.id)
        .join(NotificationPref, NotificationPref.user_id == User.id)
        .filter(
            Pick.game_date == game_date,
            Owner.user_id.isnot(None),  # users only; anon owners never get push
            User.is_active.is_(True),
            User.deleted_at.is_(None),
            NotificationPref.injury_alerts.is_(True),
            Player.injury_status.in_(LISTED_STATUSES),
        )
        .all()
    )

    device_user_ids = _users_with_active_device(db)
    already = _injury_already_notified(db, game_date)

    planned: list[PlannedNotification] = []
    for pick, player, user_id in rows:
        if user_id not in device_user_ids:
            continue
        if (user_id, player.nba_player_id) in already:
            continue
        planned.append(
            PlannedNotification(
                user_id=user_id,
                type=NotificationType.injury_alert,
                title="Injury alert",
                body=f"{player.name} is listed {player.injury_status} tonight — check your pick.",
                payload={
                    "kind": "injury_alert",
                    "player_id": player.nba_player_id,
                    "player_name": player.name,
                    "status": player.injury_status,
                    "game_date": game_date.isoformat(),
                },
            )
        )
    return planned


# --- Deadline watcher ----------------------------------------------------

def plan_deadline_notifications(db: Session, now: datetime) -> list[PlannedNotification]:
    """Users with no pick for tonight, nudged once when tip-off is under an hour away."""
    game_date, deadline = _next_slate(db, now)
    if deadline is None:
        return []
    if not (deadline - DEADLINE_WINDOW <= now < deadline):
        return []

    picked_user_ids = {
        uid
        for (uid,) in db.query(Owner.user_id)
        .join(Pick, Pick.owner_id == Owner.id)
        .filter(Pick.game_date == game_date, Owner.user_id.isnot(None))
        # any pick row counts as "decided" — a skip (player_id NULL) still claims the slot.
    }
    device_user_ids = _users_with_active_device(db)
    already = _deadline_already_notified(db, game_date)

    candidates = (
        db.query(User.id)
        .join(NotificationPref, NotificationPref.user_id == User.id)
        .filter(
            User.is_active.is_(True),
            User.deleted_at.is_(None),
            NotificationPref.deadline_alerts.is_(True),
        )
        .all()
    )

    iso = game_date.isoformat()
    planned: list[PlannedNotification] = []
    for (user_id,) in candidates:
        if user_id not in device_user_ids:
            continue
        if user_id in picked_user_ids or user_id in already:
            continue
        planned.append(
            PlannedNotification(
                user_id=user_id,
                type=NotificationType.deadline_reminder,
                title="Pick deadline soon",
                body="Tip-off is in under an hour and you haven't picked tonight.",
                payload={"kind": "deadline_reminder", "game_date": iso},
            )
        )
    return planned


# --- Dispatch ------------------------------------------------------------

def dispatch(
    db: Session,
    planned: list[PlannedNotification],
    notifier_factory: NotifierFactory = get_notifier,
) -> None:
    """Fan out each planned notification to the user's active devices and log the result.

    One bad device/user must not stall the batch: NotifierError is caught per device
    and recorded as status=failed (so the next run retries it).
    """
    for p in planned:
        devices = (
            db.query(UserDevice)
            .filter(UserDevice.user_id == p.user_id, UserDevice.revoked_at.is_(None))
            .all()
        )
        for device in devices:
            try:
                notifier_factory(device.platform).send(
                    device.push_token, p.title, p.body, p.payload
                )
                status = NotificationStatus.sent
            except NotifierError:
                status = NotificationStatus.failed
            db.add(
                NotificationLog(
                    user_id=p.user_id,
                    type=p.type,
                    payload=p.payload,
                    status=status,
                )
            )
    db.commit()


# --- Convenience wrappers (used by the cron script) ----------------------

def run_injury_watcher(
    db: Session,
    game_date: date | None = None,
    notifier_factory: NotifierFactory = get_notifier,
) -> list[PlannedNotification]:
    game_date = game_date or date.today()
    planned = plan_injury_notifications(db, game_date)
    dispatch(db, planned, notifier_factory)
    return planned


def run_deadline_watcher(
    db: Session,
    now: datetime | None = None,
    notifier_factory: NotifierFactory = get_notifier,
) -> list[PlannedNotification]:
    now = now or datetime.now(timezone.utc)
    planned = plan_deadline_notifications(db, now)
    dispatch(db, planned, notifier_factory)
    return planned


# --- Helpers -------------------------------------------------------------

def _users_with_active_device(db: Session) -> set[int]:
    return {
        uid
        for (uid,) in db.query(UserDevice.user_id)
        .filter(UserDevice.revoked_at.is_(None))
        .distinct()
    }


def _next_slate(db: Session, now: datetime) -> tuple[date | None, datetime | None]:
    """The next upcoming game slate: its date and the earliest tip-off (the deadline)."""
    game = (
        db.query(Game)
        .filter(Game.start_time_utc.isnot(None), Game.start_time_utc > now)
        .order_by(Game.start_time_utc.asc())
        .first()
    )
    if game is None:
        return None, None
    deadline = (
        db.query(func.min(Game.start_time_utc))
        .filter(Game.game_date == game.game_date, Game.start_time_utc.isnot(None))
        .scalar()
    )
    return game.game_date, _as_utc(deadline)


def _injury_already_notified(db: Session, game_date: date) -> set[tuple[int, int]]:
    """(user_id, nba_player_id) pairs already alerted for game_date."""
    iso = game_date.isoformat()
    logs = (
        db.query(NotificationLog)
        .filter(
            NotificationLog.type == NotificationType.injury_alert,
            NotificationLog.status == NotificationStatus.sent,
        )
        .all()
    )
    return {
        (log.user_id, (log.payload or {}).get("player_id"))
        for log in logs
        if (log.payload or {}).get("game_date") == iso
    }


def _deadline_already_notified(db: Session, game_date: date) -> set[int]:
    iso = game_date.isoformat()
    logs = (
        db.query(NotificationLog)
        .filter(
            NotificationLog.type == NotificationType.deadline_reminder,
            NotificationLog.status == NotificationStatus.sent,
        )
        .all()
    )
    return {log.user_id for log in logs if (log.payload or {}).get("game_date") == iso}


def _as_utc(dt: datetime | None) -> datetime | None:
    """Treat a naive datetime (SQLite drops tzinfo) as UTC so window math is comparable."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
