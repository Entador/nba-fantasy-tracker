"""Unit tests for the Notifier abstraction.

Real web push is exercised by mocking `pywebpush.webpush` — we never hit the
network. `FakeNotifier` is the test double used by higher-level watcher tests.
"""

import json
import sys
import types

import pytest

from notifications.notifier import (
    ExpoPushNotifier,
    FakeNotifier,
    NotifierError,
    WebPushNotifier,
    get_notifier,
)


SUBSCRIPTION = json.dumps(
    {
        "endpoint": "https://push.example/abc",
        "keys": {"p256dh": "BNc...", "auth": "xyz"},
    }
)


# --- FakeNotifier --------------------------------------------------------

def test_fake_notifier_records_each_send():
    notifier = FakeNotifier()
    notifier.send("tok", "Title", "Body", {"k": 1})
    notifier.send("tok2", "T2", "B2", {})
    assert len(notifier.sent) == 2
    first = notifier.sent[0]
    assert (first.token, first.title, first.body) == ("tok", "Title", "Body")
    assert first.data == {"k": 1}


def test_fake_notifier_copies_data_dict():
    """Mutating the caller's dict after send must not change the recorded payload."""
    notifier = FakeNotifier()
    data = {"k": 1}
    notifier.send("tok", "T", "B", data)
    data["k"] = 2
    assert notifier.sent[0].data == {"k": 1}


def test_fake_notifier_can_simulate_failure():
    notifier = FakeNotifier(fail_on_token="bad")
    notifier.send("good", "T", "B", {})
    with pytest.raises(NotifierError):
        notifier.send("bad", "T", "B", {})
    assert [n.token for n in notifier.sent] == ["good"]


# --- WebPushNotifier -----------------------------------------------------

def _install_pywebpush_stub(monkeypatch, capture: dict | None = None, raise_exc=None):
    """Inject a fake `pywebpush` module so WebPushNotifier.send() can be tested
    without the real dependency installed."""

    class WebPushException(Exception):
        pass

    def webpush(**kwargs):
        if capture is not None:
            capture.update(kwargs)
        if raise_exc is not None:
            raise raise_exc

    module = types.ModuleType("pywebpush")
    module.webpush = webpush
    module.WebPushException = WebPushException
    monkeypatch.setitem(sys.modules, "pywebpush", module)
    return WebPushException


def test_web_push_send_calls_pywebpush_with_subscription(monkeypatch):
    captured: dict = {}
    _install_pywebpush_stub(monkeypatch, capture=captured)

    notifier = WebPushNotifier(
        vapid_private_key="priv", vapid_claims_sub="mailto:ops@example.com"
    )
    notifier.send(SUBSCRIPTION, "Hi", "There", {"player_id": 42})

    assert captured["subscription_info"]["endpoint"] == "https://push.example/abc"
    assert captured["vapid_private_key"] == "priv"
    assert captured["vapid_claims"] == {"sub": "mailto:ops@example.com"}
    body = json.loads(captured["data"])
    assert body == {"title": "Hi", "body": "There", "data": {"player_id": 42}}


def test_web_push_init_requires_vapid_config(monkeypatch):
    monkeypatch.delenv("VAPID_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("VAPID_CLAIMS_SUB", raising=False)
    with pytest.raises(NotifierError):
        WebPushNotifier()


def test_web_push_send_raises_on_invalid_subscription_json(monkeypatch):
    _install_pywebpush_stub(monkeypatch)
    notifier = WebPushNotifier(vapid_private_key="priv", vapid_claims_sub="sub")
    with pytest.raises(NotifierError):
        notifier.send("not-json", "T", "B", {})


def test_web_push_wraps_provider_exception(monkeypatch):
    """When pywebpush raises, the notifier re-raises as NotifierError so the
    watcher can log status=failed without leaking provider internals."""

    class WebPushException(Exception):
        pass

    def webpush(**kwargs):
        raise WebPushException("gone")

    module = types.ModuleType("pywebpush")
    module.webpush = webpush
    module.WebPushException = WebPushException
    monkeypatch.setitem(sys.modules, "pywebpush", module)

    notifier = WebPushNotifier(vapid_private_key="priv", vapid_claims_sub="sub")
    with pytest.raises(NotifierError):
        notifier.send(SUBSCRIPTION, "T", "B", {})


# --- Factory -------------------------------------------------------------

def test_get_notifier_web(monkeypatch):
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "priv")
    monkeypatch.setenv("VAPID_CLAIMS_SUB", "mailto:ops@example.com")
    assert isinstance(get_notifier("web"), WebPushNotifier)


def test_get_notifier_mobile_platforms():
    assert isinstance(get_notifier("ios"), ExpoPushNotifier)
    assert isinstance(get_notifier("android"), ExpoPushNotifier)


def test_get_notifier_rejects_unknown_platform():
    with pytest.raises(NotifierError):
        get_notifier("symbian")
