"""Pydantic models for auth requests/responses."""

from pydantic import BaseModel, ConfigDict


class Token(BaseModel):
    access_token: str
    token_type: str


class UserRead(BaseModel):
    """Public view of a user. Never exposes hashed_password."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str | None
    is_active: bool
    is_verified: bool
