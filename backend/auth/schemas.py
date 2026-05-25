"""Pydantic models for auth requests/responses."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Token(BaseModel):
    access_token: str
    token_type: str


class UserCreate(BaseModel):
    """Signup payload. Email is normalized; password has a minimum length.

    We don't use pydantic's EmailStr to avoid pulling in the email-validator
    dependency — a basic '@' check is enough for now.
    """

    email: str
    password: str = Field(min_length=8)
    remember_me: bool = True  # keep a freshly registered user signed in across restarts

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v:
            raise ValueError("Invalid email address")
        return v


class UserRead(BaseModel):
    """Public view of a user. Never exposes hashed_password."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str | None
    is_active: bool
    is_verified: bool
