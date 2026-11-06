"""Team-level gating in the injury update.

One report covers tonight's games and tomorrow's, so a team on a back-to-back
shows real statuses for tonight and NOT YET SUBMITTED for tomorrow. These tests
pin that tonight's data wins.
"""

import pytest

from ingestion import injuries_nba
from models import Player, Team


@pytest.fixture
def rosters(db_session):
    teams = {}
    for nba_id, abbr, full_name, roster in [
        (1610612764, "WAS", "Washington Wizards", ["Anthony Davis", "Reece Beekman"]),
        (1610612754, "IND", "Indiana Pacers", ["Tyrese Haliburton", "Andrew Nembhard"]),
    ]:
        team = Team(nba_team_id=nba_id, abbreviation=abbr, full_name=full_name)
        db_session.add(team)
        db_session.flush()
        teams[abbr] = team
        for i, name in enumerate(roster):
            db_session.add(Player(nba_player_id=nba_id + i, name=name, team_id=team.id))
    db_session.commit()
    return teams


def _stub_scrape(monkeypatch, injuries, not_submitted):
    monkeypatch.setattr(
        injuries_nba, "scrape_nba_injuries", lambda: (injuries, not_submitted)
    )


def test_back_to_back_team_keeps_tonights_statuses(db_session, rosters, monkeypatch):
    """WAS submitted for tonight, NOT YET SUBMITTED for tomorrow — keep tonight."""
    _stub_scrape(
        monkeypatch,
        [{"name": "Anthony Davis", "status": "Questionable", "reason": "Right Ankle Sprain"}],
        {"washingtonwizards", "indianapacers"},
    )

    result = injuries_nba.update_player_injuries_nba(db_session)

    davis = db_session.query(Player).filter(Player.name == "Anthony Davis").one()
    assert davis.injury_status == "Questionable"
    assert result["skipped_teams"] == ["Indiana Pacers"]
    assert result["not_found"] == []


def test_fully_unsubmitted_team_is_preserved(db_session, rosters, monkeypatch):
    """No IND player in the report → don't clear yesterday's statuses."""
    haliburton = db_session.query(Player).filter(Player.name == "Tyrese Haliburton").one()
    haliburton.injury_status = "Out"
    db_session.commit()

    _stub_scrape(monkeypatch, [], {"indianapacers"})

    injuries_nba.update_player_injuries_nba(db_session)

    db_session.refresh(haliburton)
    assert haliburton.injury_status == "Out"


def test_submitted_team_clears_players_absent_from_report(db_session, rosters, monkeypatch):
    """WAS submitted and Beekman isn't listed → his stale status is cleared."""
    beekman = db_session.query(Player).filter(Player.name == "Reece Beekman").one()
    beekman.injury_status = "Out"
    db_session.commit()

    _stub_scrape(
        monkeypatch,
        [{"name": "Anthony Davis", "status": "Questionable", "reason": ""}],
        {"washingtonwizards"},
    )

    injuries_nba.update_player_injuries_nba(db_session)

    db_session.refresh(beekman)
    assert beekman.injury_status is None
