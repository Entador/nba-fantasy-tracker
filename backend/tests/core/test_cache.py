"""Injury-refresh behaviour of the in-memory cache.

The cache holds player rows for the life of the process, so a daily injury
update must reach a server that was already running. These tests pin the
invalidation contract: the `injury_updated_at` stamp, with the TTL as backstop.
"""

from datetime import datetime, timedelta, timezone

import pytest

from sqlalchemy.orm import sessionmaker

from core.cache import INJURY_TTL_SECONDS, AppCache
from models import AppMetadata, Player, Team


@pytest.fixture
def cache(db_session):
    team = Team(nba_team_id=1610612738, abbreviation="BOS", full_name="Boston Celtics")
    db_session.add(team)
    db_session.flush()
    db_session.add(Player(nba_player_id=1630202, name="Payton Pritchard", team_id=team.id))
    db_session.add(AppMetadata(key="injury_updated_at", value="2026-11-06T10:00:00+00:00"))
    db_session.commit()

    # Load the cache from its own session, as the app does at startup: the
    # cached rows must be instances a later request session can't mutate
    # in place, or these tests would pass for the wrong reason.
    startup_session = sessionmaker(bind=db_session.get_bind())()
    c = AppCache()
    c.load_schedule(startup_session)
    startup_session.close()
    return c


def _set_status(db, status):
    player = db.query(Player).filter(Player.nba_player_id == 1630202).first()
    player.injury_status = status
    db.commit()


def _bump_stamp(db, value):
    row = db.query(AppMetadata).filter(AppMetadata.key == "injury_updated_at").first()
    row.value = value
    db.commit()


def _cached_status(cache):
    return cache.players_by_nba_id[1630202].injury_status


def test_no_refresh_while_stamp_unchanged(cache, db_session):
    # A write that doesn't bump the stamp is invisible until the TTL fires —
    # this is what makes the fresh case cheap.
    _set_status(db_session, "Questionable")

    assert cache.refresh_injuries_if_stale(db_session, "2026-11-06T10:00:00+00:00") is False
    assert _cached_status(cache) is None


def test_refresh_when_stamp_changes(cache, db_session):
    _set_status(db_session, "Questionable")
    _bump_stamp(db_session, "2026-11-06T16:08:34+00:00")

    assert cache.refresh_injuries_if_stale(db_session, "2026-11-06T16:08:34+00:00") is True
    assert _cached_status(cache) == "Questionable"


def test_refresh_is_not_repeated_for_the_same_stamp(cache, db_session):
    _set_status(db_session, "Questionable")
    _bump_stamp(db_session, "2026-11-06T16:08:34+00:00")

    assert cache.refresh_injuries_if_stale(db_session, "2026-11-06T16:08:34+00:00") is True
    assert cache.refresh_injuries_if_stale(db_session, "2026-11-06T16:08:34+00:00") is False


def test_ttl_is_a_backstop_for_writes_that_skip_the_stamp(cache, db_session):
    _set_status(db_session, "Out")
    cache._injuries_loaded_at = datetime.now(timezone.utc) - timedelta(
        seconds=INJURY_TTL_SECONDS + 1
    )

    assert cache.refresh_injuries_if_stale(db_session, "2026-11-06T10:00:00+00:00") is True
    assert _cached_status(cache) == "Out"


def test_reads_the_stamp_itself_when_the_caller_has_none(cache, db_session):
    _set_status(db_session, "Probable")
    _bump_stamp(db_session, "2026-11-06T16:08:34+00:00")

    assert cache.refresh_injuries_if_stale(db_session) is True
    assert _cached_status(cache) == "Probable"


def test_noop_until_the_cache_is_loaded(db_session):
    assert AppCache().refresh_injuries_if_stale(db_session) is False
