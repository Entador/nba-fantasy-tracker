"""Pydantic models for pick requests/responses."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


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


class PickRead(BaseModel):
    """A stored pick. Owner is implicit (the caller), so it is never exposed.

    player_id is None for a skipped night.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    player_id: int | None
    game_date: date
    picked_at: datetime | None


class PlayerLock(BaseModel):
    """When a player the caller has already picked becomes eligible again.

    available_on is the first date the player can be picked again:
    - regular season: their latest pick + 30 days.
    - playoffs: None — a playoff pick locks the player for the whole playoff run.

    The list only contains locked players; anyone absent is eligible. The dates are
    independent of the date being viewed, so the client computes them once and reuses
    them across date navigation (eligible on a date D  ⟺  available_on is not None and
    D >= available_on).
    """

    player_id: int  # nba_player_id, like the rest of the API
    available_on: date | None


class PicksRead(BaseModel):
    """List response: the caller's picks plus the per-player eligibility locks
    derived from them (the 30-day / playoff rule lives server-side)."""

    picks: list[PickRead]
    locks: list[PlayerLock]
