"""Integration tests for pick endpoints: guest + user ownership, isolation, 30-day rule."""

from datetime import date, timedelta

import pytest

from models import Game, Player

D = date(2026, 1, 15)
PLAYOFF_START = date(2026, 4, 18)


@pytest.fixture
def players(db_session):
    """Three pickable players. Returns their DB ids."""
    rows = [Player(nba_player_id=1000 + i, name=f"Player {i}") for i in range(3)]
    db_session.add_all(rows)
    db_session.commit()
    return [p.id for p in rows]


@pytest.fixture
def playoffs(db_session):
    """Schedule a playoff game so get_playoff_start_date() returns PLAYOFF_START."""
    db_session.add(Game(nba_game_id="0042400101", game_date=PLAYOFF_START))
    db_session.commit()
    return PLAYOFF_START


def pick(client, player_id, game_date=D):
    return client.post("/api/picks", json={"player_id": player_id, "game_date": game_date.isoformat()})


def register_and_login(client, email):
    client.post("/auth/register", json={"email": email, "password": "password123"})
    token = client.post("/token", data={"username": email, "password": "password123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- Guest flow -----------------------------------------------------------

def test_guest_create_returns_pick(make_client, players):
    c = make_client()
    r = pick(c, players[0])
    assert r.status_code == 201
    body = r.json()
    assert body["player_id"] == players[0]
    assert body["game_date"] == D.isoformat()


def test_guest_retrieves_picks_via_cookie(make_client, players):
    c = make_client()
    pick(c, players[0])
    # The anon identity is set as a cookie; a follow-up request carries it.
    assert "anon_id" in c.cookies
    listed = c.get("/api/picks").json()
    assert [p["player_id"] for p in listed] == [players[0]]


def test_two_guests_are_isolated(make_client, players):
    a, b = make_client(), make_client()
    pick(a, players[0])
    assert a.get("/api/picks").json() != []
    assert b.get("/api/picks").json() == []  # different cookie -> different owner


# --- Pick rules -----------------------------------------------------------

def test_repick_same_night_replaces_player(make_client, players):
    c = make_client()
    pick(c, players[0])
    pick(c, players[1])
    listed = c.get("/api/picks").json()
    assert len(listed) == 1
    assert listed[0]["player_id"] == players[1]


def test_same_player_within_30_days_is_rejected(make_client, players):
    c = make_client()
    assert pick(c, players[0], D).status_code == 201
    assert pick(c, players[0], D + timedelta(days=5)).status_code == 409


def test_same_player_outside_30_days_is_allowed(make_client, players):
    c = make_client()
    assert pick(c, players[0], D).status_code == 201
    assert pick(c, players[0], D + timedelta(days=31)).status_code == 201


def test_pick_unknown_player_404(make_client, players):
    c = make_client()
    assert pick(c, 999999).status_code == 404


# --- Playoff rule: each player only once for the whole playoffs --------------

def test_playoffs_block_repick_even_outside_30_days(make_client, players, playoffs):
    c = make_client()
    # +40 days would be fine in the regular season, but not during playoffs.
    assert pick(c, players[0], PLAYOFF_START + timedelta(days=2)).status_code == 201
    assert pick(c, players[0], PLAYOFF_START + timedelta(days=42)).status_code == 409


def test_regular_season_pick_does_not_block_playoff_pick(make_client, players, playoffs):
    c = make_client()
    # A pick from before the playoffs must not count against the playoff run.
    assert pick(c, players[0], PLAYOFF_START - timedelta(days=3)).status_code == 201
    assert pick(c, players[0], PLAYOFF_START).status_code == 201


# --- Delete + authorization ----------------------------------------------

def test_delete_own_pick(make_client, players):
    c = make_client()
    pick_id = pick(c, players[0]).json()["id"]
    assert c.delete(f"/api/picks/{pick_id}").status_code == 204
    assert c.get("/api/picks").json() == []


def test_cannot_delete_another_owners_pick(make_client, players):
    a, b = make_client(), make_client()
    pick_id = pick(a, players[0]).json()["id"]
    assert b.delete(f"/api/picks/{pick_id}").status_code == 404  # not yours -> looks missing
    assert len(a.get("/api/picks").json()) == 1  # still there


# --- Authenticated users --------------------------------------------------

def test_user_picks_isolated_from_guest(make_client, players):
    guest = make_client()
    user = make_client()
    headers = register_and_login(user, "u1@example.com")

    user.post("/api/picks", json={"player_id": players[0], "game_date": D.isoformat()}, headers=headers)
    assert len(user.get("/api/picks", headers=headers).json()) == 1
    assert guest.get("/api/picks").json() == []


def test_two_users_are_isolated(make_client, players):
    a, b = make_client(), make_client()
    ha = register_and_login(a, "a@example.com")
    hb = register_and_login(b, "b@example.com")

    a.post("/api/picks", json={"player_id": players[0], "game_date": D.isoformat()}, headers=ha)
    assert len(a.get("/api/picks", headers=ha).json()) == 1
    assert b.get("/api/picks", headers=hb).json() == []
