"""Pydantic models for device registration and notification preferences."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Platform = Literal["ios", "android", "web"]


class DeviceRegister(BaseModel):
    """Register a push token. Idempotent: re-posting the same token refreshes last_seen
    and re-activates a previously revoked row (e.g. the user re-enabled notifications)."""

    push_token: str = Field(min_length=1, max_length=512)
    platform: Platform


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    push_token: str
    platform: Platform
    registered_at: datetime | None
    last_seen: datetime | None


class NotificationPrefRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    injury_alerts: bool
    deadline_alerts: bool


class NotificationPrefUpdate(BaseModel):
    """Partial update — only provided fields change."""

    injury_alerts: bool | None = None
    deadline_alerts: bool | None = None
