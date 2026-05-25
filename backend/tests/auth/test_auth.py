"""Integration tests for email/password auth: register, login, current user."""

VALID = {"email": "player@example.com", "password": "password123"}


def register(client, **overrides):
    return client.post("/auth/register", json={**VALID, **overrides})


def login(client, email=VALID["email"], password=VALID["password"]):
    # /token expects form-encoded data (OAuth2PasswordRequestForm), not JSON.
    return client.post("/token", data={"username": email, "password": password})


def test_register_creates_user(client):
    r = register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == VALID["email"]
    assert body["is_active"] is True
    assert body["is_verified"] is False
    assert "hashed_password" not in body  # never leak the hash


def test_register_duplicate_email_conflicts(client):
    assert register(client).status_code == 201
    assert register(client).status_code == 409


def test_register_normalizes_email(client):
    assert register(client, email="Player@Example.com  ").status_code == 201
    # Same address in canonical form is rejected as a duplicate.
    assert register(client, email="player@example.com").status_code == 409


def test_register_rejects_short_password(client):
    assert register(client, password="short").status_code == 422


def test_register_rejects_invalid_email(client):
    assert register(client, email="not-an-email").status_code == 422


def test_login_after_register_returns_bearer_token(client):
    register(client)
    r = login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_is_case_insensitive_on_email(client):
    register(client)
    assert login(client, email="PLAYER@EXAMPLE.COM").status_code == 200


def test_login_wrong_password_is_unauthorized(client):
    register(client)
    assert login(client, password="wrongpassword").status_code == 401


def test_login_unknown_email_is_unauthorized(client):
    assert login(client, email="ghost@example.com").status_code == 401


def test_me_requires_authentication(client):
    assert client.get("/users/me").status_code == 401


def test_me_returns_current_user(client):
    register(client)
    token = login(client).json()["access_token"]
    r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == VALID["email"]
