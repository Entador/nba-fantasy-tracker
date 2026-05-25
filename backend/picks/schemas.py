"""Pydantic models for pick requests/responses."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PickCreate(BaseModel):
    """Create (or change) the pick for a given night."""

    player_id: int
    game_date: date


class PickRead(BaseModel):
    """A stored pick. Owner is implicit (the caller), so it is never exposed."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    player_id: int
    game_date: date
    picked_at: datetime | None
