"""Pydantic models for pick requests/responses."""

from datetime import date, datetime

from pydantic import BaseModel

from core.schemas import ORMModel


class PickCreate(BaseModel):
    """Create (or change) the pick for a given night.

    player_id = None records a deliberate skip (the night is acknowledged with no
    pick) so the forgotten-pick reminder stops nagging.
    """

    player_id: int | None = None
    game_date: date


class PickBatchCreate(BaseModel):
    """Bulk import of picks (e.g. TTFL history). Authoritative: overwrites clashes
    and bypasses eligibility, since the imported history is the source of truth."""

    picks: list[PickCreate]


class PickImportResult(BaseModel):
    """imported = picks stored; skipped = items whose player_id was unknown."""

    imported: int
    skipped: int


class PickRead(ORMModel):
    """A stored pick. Owner is implicit (the caller), so it is never exposed.

    player_id is None for a skipped night.
    fantasy_score is None when the game hasn't been played yet or for skipped nights.
    """

    id: int
    player_id: int | None
    game_date: date
    picked_at: datetime | None
    fantasy_score: int | None = None


class PlayerLock(BaseModel):
    """A locked window for a player the caller has already picked — one entry per pick.

    The window is the open interval `(locked_from, available_on)`, exclusive at both ends, so a
    player is NOT locked on (or before) the date they were picked — only strictly after:
    - regular season: locked_from = the pick date, available_on = pick date + 30 days.
    - playoffs: locked_from = playoff start, available_on = None (locked for the whole run).

    The client owns no rule logic: a player is locked on date D iff some entry has
    `locked_from < D` and `(available_on is None or D < available_on)`. The bounds are
    independent of the viewed date, so the client computes them once and reuses them
    across date navigation. Players with no entry are eligible.
    """

    player_id: int  # nba_player_id, like the rest of the API
    locked_from: date
    available_on: date | None


class PicksRead(BaseModel):
    """List response: the caller's picks plus the per-player eligibility locks
    derived from them (the 30-day / playoff rule lives server-side)."""

    picks: list[PickRead]
    locks: list[PlayerLock]
