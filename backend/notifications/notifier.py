"""Notifier abstraction. One Protocol, one implementation per push provider.

Why a Protocol (and not a base class): callers depend on the interface, not on
inheritance. Tests inject a `FakeNotifier`; watcher code stays the same.

Token shape per platform:
- web   : the push token is the JSON-encoded subscription object
          ({endpoint, keys: {p256dh, auth}}) produced by `PushManager.subscribe`
          in the browser. We store it as a string in `user_devices.push_token`.
- ios   : Expo push token (`ExponentPushToken[...]`). Implementation lands in Month 4.
- android: same as iOS — Expo push token.

The watcher fans out via `get_notifier(device.platform).send(device.push_token, ...)`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Protocol


class NotifierError(Exception):
    """Raised when a send fails for a reason worth logging as `status=failed`.

    Watcher code catches this, writes the failure to `notification_log`, and
    moves on — one bad device must not stall the batch.
    """


class Notifier(Protocol):
    def send(self, token: str, title: str, body: str, data: dict[str, Any]) -> None:
        ...


# --- Web push ------------------------------------------------------------

class WebPushNotifier:
    """Web push via VAPID. `token` is the JSON-encoded browser subscription."""

    def __init__(
        self,
        vapid_private_key: str | None = None,
        vapid_claims_sub: str | None = None,
    ) -> None:
        self._vapid_private_key = vapid_private_key or os.getenv("VAPID_PRIVATE_KEY")
        self._vapid_claims_sub = vapid_claims_sub or os.getenv("VAPID_CLAIMS_SUB")
        if not self._vapid_private_key or not self._vapid_claims_sub:
            raise NotifierError(
                "Missing VAPID_PRIVATE_KEY or VAPID_CLAIMS_SUB; cannot send web push."
            )

    def send(self, token: str, title: str, body: str, data: dict[str, Any]) -> None:
        # Imported lazily so the module is importable in environments that
        # don't have pywebpush installed yet (tests use FakeNotifier).
        from pywebpush import WebPushException, webpush

        try:
            subscription = json.loads(token)
        except json.JSONDecodeError as e:
            raise NotifierError(f"Invalid web push subscription JSON: {e}") from e

        payload = json.dumps({"title": title, "body": body, "data": data})
        try:
            webpush(
                subscription_info=subscription,
                data=payload,
                vapid_private_key=self._vapid_private_key,
                vapid_claims={"sub": self._vapid_claims_sub},
            )
        except WebPushException as e:
            raise NotifierError(str(e)) from e


# --- Stub for mobile (Month 4) -------------------------------------------

class ExpoPushNotifier:
    """Placeholder. Filled in when the mobile app exists."""

    def send(self, token: str, title: str, body: str, data: dict[str, Any]) -> None:
        raise NotifierError("ExpoPushNotifier not implemented yet (Month 4).")


# --- Test double ---------------------------------------------------------

@dataclass
class _SentNotification:
    token: str
    title: str
    body: str
    data: dict[str, Any]


@dataclass
class FakeNotifier:
    """Records every call so tests can assert on the fan-out."""

    sent: list[_SentNotification] = field(default_factory=list)
    fail_on_token: str | None = None  # set to simulate a per-device failure

    def send(self, token: str, title: str, body: str, data: dict[str, Any]) -> None:
        if self.fail_on_token is not None and token == self.fail_on_token:
            raise NotifierError(f"FakeNotifier configured to fail on {token!r}")
        self.sent.append(_SentNotification(token, title, body, dict(data)))


# --- Factory -------------------------------------------------------------

def get_notifier(platform: str) -> Notifier:
    """Dispatch by `UserDevice.platform`. Unknown platforms raise — they should
    never reach the watcher (schema enum is enforced at register time).
    """
    if platform == "web":
        return WebPushNotifier()
    if platform in ("ios", "android"):
        return ExpoPushNotifier()
    raise NotifierError(f"Unknown notifier platform: {platform!r}")
