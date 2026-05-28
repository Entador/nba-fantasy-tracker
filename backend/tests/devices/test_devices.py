"""Integration tests for /api/devices/* and /api/notification-prefs."""


def register_and_login(client, email="user@example.com"):
    client.post("/auth/register", json={"email": email, "password": "password123"})
    token = client.post(
        "/token", data={"username": email, "password": "password123"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def register_device(client, headers, push_token="tok-abc", platform="web"):
    return client.post(
        "/api/devices/register",
        json={"push_token": push_token, "platform": platform},
        headers=headers,
    )


# --- Auth ----------------------------------------------------------------

def test_register_device_requires_auth(client):
    r = client.post(
        "/api/devices/register", json={"push_token": "x", "platform": "web"}
    )
    assert r.status_code == 401


def test_prefs_require_auth(client):
    assert client.get("/api/notification-prefs").status_code == 401
    assert client.patch("/api/notification-prefs", json={}).status_code == 401


# --- Device register -----------------------------------------------------

def test_register_device_creates_row(client):
    headers = register_and_login(client)
    r = register_device(client, headers)
    assert r.status_code == 201
    body = r.json()
    assert body["push_token"] == "tok-abc"
    assert body["platform"] == "web"
    assert body["id"] > 0


def test_register_device_is_idempotent_for_same_token(client):
    headers = register_and_login(client)
    a = register_device(client, headers).json()
    b = register_device(client, headers).json()
    assert a["id"] == b["id"]  # same row, last_seen refreshed


def test_register_device_rejects_unknown_platform(client):
    headers = register_and_login(client)
    r = register_device(client, headers, platform="symbian")
    assert r.status_code == 422


def test_register_device_transfers_token_between_users(client, make_client):
    """A push token re-registered under another account moves to that account.

    Prevents one device fanning out notifications to two accounts after a sign-out/sign-in.
    """
    a_headers = register_and_login(client, "a@example.com")
    device = register_device(client, a_headers).json()

    b_headers = register_and_login(client, "b@example.com")
    again = register_device(client, b_headers).json()
    assert again["id"] == device["id"]

    # Account A no longer sees the device (it now belongs to B); covered indirectly:
    # B's delete succeeds, A's would 404.
    assert (
        client.delete(f"/api/devices/{device['id']}", headers=a_headers).status_code
        == 404
    )
    assert (
        client.delete(f"/api/devices/{device['id']}", headers=b_headers).status_code
        == 204
    )


# --- Device delete -------------------------------------------------------

def test_delete_device_revokes_own(client):
    headers = register_and_login(client)
    device = register_device(client, headers).json()
    r = client.delete(f"/api/devices/{device['id']}", headers=headers)
    assert r.status_code == 204


def test_delete_other_users_device_404(client):
    a_headers = register_and_login(client, "a@example.com")
    device = register_device(client, a_headers).json()
    b_headers = register_and_login(client, "b@example.com")
    r = client.delete(f"/api/devices/{device['id']}", headers=b_headers)
    assert r.status_code == 404


def test_delete_missing_device_404(client):
    headers = register_and_login(client)
    assert client.delete("/api/devices/9999", headers=headers).status_code == 404


# --- Notification prefs --------------------------------------------------

def test_get_prefs_auto_creates_with_defaults(client):
    headers = register_and_login(client)
    r = client.get("/api/notification-prefs", headers=headers)
    assert r.status_code == 200
    assert r.json() == {"injury_alerts": True, "deadline_alerts": True}


def test_patch_prefs_updates_only_provided_fields(client):
    headers = register_and_login(client)
    client.get("/api/notification-prefs", headers=headers)  # create defaults

    r = client.patch(
        "/api/notification-prefs", json={"injury_alerts": False}, headers=headers
    )
    assert r.status_code == 200
    assert r.json() == {"injury_alerts": False, "deadline_alerts": True}

    # deadline_alerts untouched on a no-op PATCH
    r = client.patch("/api/notification-prefs", json={}, headers=headers)
    assert r.json() == {"injury_alerts": False, "deadline_alerts": True}


def test_patch_prefs_auto_creates_when_missing(client):
    headers = register_and_login(client)
    r = client.patch(
        "/api/notification-prefs",
        json={"deadline_alerts": False},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json() == {"injury_alerts": True, "deadline_alerts": False}


def test_prefs_are_isolated_per_user(client):
    a = register_and_login(client, "a@example.com")
    b = register_and_login(client, "b@example.com")
    client.patch(
        "/api/notification-prefs", json={"injury_alerts": False}, headers=a
    )
    assert client.get("/api/notification-prefs", headers=b).json() == {
        "injury_alerts": True,
        "deadline_alerts": True,
    }
