"""Unit tests for the notification watchers (injury alerts + deadline reminders).

Pure plan_* functions are tested against an in-memory DB; dispatch + dedup are
tested with a FakeNotifier. No real push, no VAPID keys.
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from models import (
    Game,
    NotificationPref,
    Owner,
    Pick,
    Player,
    Team,
    User,
    UserDevice,
)
from notifications import watchers
from notifications.notifier import FakeNotifier

TONIGHT = date(2026, 3, 1)


# --- Builders ------------------------------------------------------------

def make_user(db, email, *, injury=True, deadline=True, device="tok"):
    user = User(email=email, hashed_password="x", is_active=True)
    db.add(user)
    db.flush()
    db.add(Owner(user_id=user.id))
    db.add(NotificationPref(user_id=user.id, injury_alerts=injury, deadline_alerts=deadline))
    if device is not None:
        db.add(UserDevice(user_id=user.id, push_token=device, platform="web"))
    db.flush()
    return user


def make_player(db, nba_id=1, name="Player One", status=None):
    team = Team(nba_team_id=nba_id, abbreviation="AAA", full_name="Team A")
    db.add(team)
    db.flush()
    player = Player(nba_player_id=nba_id, name=name, team_id=team.id, injury_status=status)
    db.add(player)
    db.flush()
    return player


def add_pick(db, user, player, game_date=TONIGHT):
    owner = db.query(Owner).filter(Owner.user_id == user.id).first()
    pick = Pick(owner_id=owner.id, player_id=(player.id if player else None), game_date=game_date)
    db.add(pick)
    db.flush()
    return pick


# --- Injury watcher: planning --------------------------------------------

def test_injury_alert_for_listed_pick(db_session):
    user = make_user(db_session, "a@x.com")
    player = make_player(db_session, status="Out")
    add_pick(db_session, user, player)

    planned = watchers.plan_injury_notifications(db_session, TONIGHT)

    assert len(planned) == 1
    assert planned[0].user_id == user.id
    assert planned[0].payload["player_id"] == player.nba_player_id
    assert "Out" in planned[0].body


def test_no_alert_for_healthy_pick(db_session):
    user = make_user(db_session, "a@x.com")
    player = make_player(db_session, status=None)
    add_pick(db_session, user, player)

    assert watchers.plan_injury_notifications(db_session, TONIGHT) == []


def test_no_injury_alert_when_pref_off(db_session):
    user = make_user(db_session, "a@x.com", injury=False)
    player = make_player(db_session, status="Doubtful")
    add_pick(db_session, user, player)

    assert watchers.plan_injury_notifications(db_session, TONIGHT) == []


def test_no_injury_alert_without_device(db_session):
    user = make_user(db_session, "a@x.com", device=None)
    player = make_player(db_session, status="Questionable")
    add_pick(db_session, user, player)

    assert watchers.plan_injury_notifications(db_session, TONIGHT) == []


def test_no_injury_alert_for_anon_owner(db_session):
    # An anon owner (no user_id) holding the pick must never be alerted.
    player = make_player(db_session, status="Out")
    owner = Owner(identity_id=None)
    # anon owners are keyed by identity, but for this test a bare owner with no
    # user_id is enough to prove the user-only filter.
    from models import AnonIdentity

    identity = AnonIdentity()
    db_session.add(identity)
    db_session.flush()
    owner.identity_id = identity.id
    db_session.add(owner)
    db_session.flush()
    db_session.add(Pick(owner_id=owner.id, player_id=player.id, game_date=TONIGHT))
    db_session.flush()

    assert watchers.plan_injury_notifications(db_session, TONIGHT) == []


def test_skip_night_never_alerts(db_session):
    user = make_user(db_session, "a@x.com")
    add_pick(db_session, user, None)  # skip: player_id NULL

    assert watchers.plan_injury_notifications(db_session, TONIGHT) == []


# --- Injury watcher: dispatch + dedup ------------------------------------

def test_injury_dispatch_sends_and_dedupes(db_session):
    user = make_user(db_session, "a@x.com")
    player = make_player(db_session, status="Out")
    add_pick(db_session, user, player)
    fake = FakeNotifier()

    watchers.run_injury_watcher(db_session, TONIGHT, notifier_factory=lambda _: fake)
    watchers.run_injury_watcher(db_session, TONIGHT, notifier_factory=lambda _: fake)

    assert len(fake.sent) == 1  # second run is deduped via notification_log


# --- Deadline watcher ----------------------------------------------------

def add_game(db, start_utc, game_date=TONIGHT):
    home = Team(nba_team_id=10, abbreviation="HHH", full_name="Home")
    away = Team(nba_team_id=11, abbreviation="WWW", full_name="Away")
    db.add_all([home, away])
    db.flush()
    db.add(
        Game(
            nba_game_id=f"002{start_utc.timestamp():.0f}",
            home_team_id=home.id,
            away_team_id=away.id,
            game_date=game_date,
            status="scheduled",
            start_time_utc=start_utc,
        )
    )
    db.flush()


def test_deadline_reminder_in_window_without_pick(db_session):
    tip = datetime(2026, 3, 2, 0, 30, tzinfo=timezone.utc)
    add_game(db_session, tip, game_date=date(2026, 3, 2))
    make_user(db_session, "a@x.com")
    now = tip - timedelta(minutes=30)  # inside the 1h window

    planned = watchers.plan_deadline_notifications(db_session, now)

    assert len(planned) == 1
    assert planned[0].type.value == "deadline_reminder"


def test_no_deadline_reminder_outside_window(db_session):
    tip = datetime(2026, 3, 2, 0, 30, tzinfo=timezone.utc)
    add_game(db_session, tip, game_date=date(2026, 3, 2))
    make_user(db_session, "a@x.com")
    now = tip - timedelta(hours=3)  # too early

    assert watchers.plan_deadline_notifications(db_session, now) == []


def test_no_deadline_reminder_when_already_picked(db_session):
    tip = datetime(2026, 3, 2, 0, 30, tzinfo=timezone.utc)
    add_game(db_session, tip, game_date=date(2026, 3, 2))
    user = make_user(db_session, "a@x.com")
    player = make_player(db_session, status=None)
    add_pick(db_session, user, player, game_date=date(2026, 3, 2))
    now = tip - timedelta(minutes=30)

    assert watchers.plan_deadline_notifications(db_session, now) == []


def test_skip_counts_as_decided_for_deadline(db_session):
    tip = datetime(2026, 3, 2, 0, 30, tzinfo=timezone.utc)
    add_game(db_session, tip, game_date=date(2026, 3, 2))
    user = make_user(db_session, "a@x.com")
    add_pick(db_session, user, None, game_date=date(2026, 3, 2))  # deliberate skip
    now = tip - timedelta(minutes=30)

    assert watchers.plan_deadline_notifications(db_session, now) == []


def test_no_deadline_reminder_when_pref_off(db_session):
    tip = datetime(2026, 3, 2, 0, 30, tzinfo=timezone.utc)
    add_game(db_session, tip, game_date=date(2026, 3, 2))
    make_user(db_session, "a@x.com", deadline=False)
    now = tip - timedelta(minutes=30)

    assert watchers.plan_deadline_notifications(db_session, now) == []


def test_deadline_dispatch_dedupes(db_session):
    tip = datetime(2026, 3, 2, 0, 30, tzinfo=timezone.utc)
    add_game(db_session, tip, game_date=date(2026, 3, 2))
    make_user(db_session, "a@x.com")
    now = tip - timedelta(minutes=30)
    fake = FakeNotifier()

    watchers.run_deadline_watcher(db_session, now, notifier_factory=lambda _: fake)
    watchers.run_deadline_watcher(db_session, now, notifier_factory=lambda _: fake)

    assert len(fake.sent) == 1


# --- Dispatch fan-out + failure isolation --------------------------------

def test_dispatch_fans_out_to_all_devices_and_isolates_failures(db_session):
    user = make_user(db_session, "a@x.com", device="good-tok")
    db_session.add(UserDevice(user_id=user.id, push_token="bad-tok", platform="web"))
    db_session.flush()
    player = make_player(db_session, status="Out")
    add_pick(db_session, user, player)

    fake = FakeNotifier(fail_on_token="bad-tok")
    watchers.run_injury_watcher(db_session, TONIGHT, notifier_factory=lambda _: fake)

    # The good device received the push; the failure didn't stall the batch.
    assert [s.token for s in fake.sent] == ["good-tok"]

    from models import NotificationLog, NotificationStatus

    statuses = {
        log.status for log in db_session.query(NotificationLog).all()
    }
    assert NotificationStatus.sent in statuses
    assert NotificationStatus.failed in statuses
