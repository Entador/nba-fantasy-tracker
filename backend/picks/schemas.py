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
