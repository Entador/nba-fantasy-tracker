"""Tests for the refresh-token "remember me" flow: rotation, revocation, expiry."""

from datetime import datetime, timedelta, timezone

from auth.security import hash_refresh_token
from models import RefreshSession

VALID = {"email": "player@example.com", "password": "password123"}


def register(client, **overrides):
    return client.post("/auth/register", json={**VALID, **overrides})


def login(client, remember_me=True):
    return client.post(
        "/token",
        data={**{"username": VALID["email"], "password": VALID["password"]}, "remember_me": str(remember_me)},
    )


def test_login_sets_refresh_cookie(client):
    register(client)
    cookie = login(client).headers["set-cookie"]
    assert "refresh_token=" in cookie
    assert "httponly" in cookie.lower()


def test_refresh_rotates_token_and_renews_access(client):
    register(client)
    old_refresh = client.cookies["refresh_token"]
    r = client.post("/auth/refresh")
    assert r.status_code == 200
    assert r.json()["access_token"]
    assert client.cookies["refresh_token"] != old_refresh  # rotated


def test_refresh_keeps_user_authenticated(client):
    register(client)
    assert client.post("/auth/refresh").status_code == 200
    assert client.get("/users/me").json()["email"] == VALID["email"]


def test_rotated_out_token_is_rejected(client, make_client):
    register(client)
    stale = client.cookies["refresh_token"]
    client.post("/auth/refresh")  # rotates `stale` out

    replay = make_client()
    replay.cookies.set("refresh_token", stale, path="/auth")
    assert replay.post("/auth/refresh").status_code == 401


def test_logout_revokes_session(client):
    register(client)
    assert client.post("/auth/logout").status_code == 200
    assert client.post("/auth/refresh").status_code == 401


def test_refresh_without_cookie_is_unauthorized(client):
    assert client.post("/auth/refresh").status_code == 401


def test_expired_session_is_rejected(client, db_session):
    register(client)
    raw = client.cookies["refresh_token"]
    session = (
        db_session.query(RefreshSession)
        .filter(RefreshSession.token_hash == hash_refresh_token(raw))
        .one()
    )
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()
    assert client.post("/auth/refresh").status_code == 401


def _refresh_set_cookie(response) -> str:
    """The Set-Cookie line for refresh_token (a response sets several cookies)."""
    return next(
        c for c in response.headers.get_list("set-cookie") if c.startswith("refresh_token=")
    )


def test_remember_me_false_makes_session_cookie(client):
    register(client)
    cookie = _refresh_set_cookie(login(client, remember_me=False))
    # A session cookie has neither Max-Age nor Expires → cleared on browser close.
    assert "max-age" not in cookie.lower()
    assert "expires" not in cookie.lower()


def test_remember_me_true_makes_persistent_cookie(client):
    register(client)
    cookie = _refresh_set_cookie(login(client, remember_me=True))
    assert "max-age" in cookie.lower()  # persistent → survives browser close
