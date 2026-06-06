"""Pydantic models for device registration and notification preferences."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from core.schemas import ORMModel


Platform = Literal["ios", "android", "web"]


class DeviceRegister(BaseModel):
    """Register a push token. Idempotent: re-posting the same token refreshes last_seen
    and re-activates a previously revoked row (e.g. the user re-enabled notifications)."""

    # Web subscriptions are a JSON blob (endpoint + keys); Chrome/FCM endpoints push
    # the total well past 512 chars. The DB column is unbounded String, so cap generously.
    push_token: str = Field(min_length=1, max_length=2048)
    platform: Platform


class DeviceRead(ORMModel):
    id: int
    push_token: str
    platform: Platform
    registered_at: datetime | None
    last_seen: datetime | None


class NotificationPrefRead(ORMModel):
    injury_alerts: bool
    deadline_alerts: bool


class NotificationPrefUpdate(BaseModel):
    """Partial update — only provided fields change."""

    injury_alerts: bool | None = None
    deadline_alerts: bool | None = None
