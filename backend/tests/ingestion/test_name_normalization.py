import pytest

from ingestion.injuries_nba import _normalize_player_name
from ingestion.utils import normalize_name


@pytest.mark.parametrize(
    "pdf_name, expected",
    [
        ("Allen,Jarrett", "Jarrett Allen"),
        ("MurphyIII,Trey", "Trey Murphy III"),
        ("MooreJr.,Wendell", "Wendell Moore Jr."),
        # Extra comma before the suffix — split on the last one only.
        ("Udeh,Jr.,Ernest", "Ernest Udeh Jr."),
        # Suffix without a trailing period.
        ("ShannonJr,Terrence", "Terrence Shannon Jr"),
        # Lowercase particle glued to the surname.
        ("deLarrea,Sergio", "Sergio de Larrea"),
        # Capitalized prefixes must not be split.
        ("McCullarJr.,Kevin", "Kevin McCullar Jr."),
        ("DeRozan,DeMar", "DeMar DeRozan"),
    ],
)
def test_normalize_player_name(pdf_name, expected):
    assert _normalize_player_name(pdf_name) == expected


@pytest.mark.parametrize(
    "a, b",
    [
        # Suffix punctuation differs between nba_api and the injury report.
        ("Ernest Udeh, Jr.", "Ernest Udeh Jr."),
        ("Terrence Shannon Jr.", "Terrence Shannon Jr"),
        # Accents, apostrophes and hyphens.
        ("Luka Dončić", "Luka Doncic"),
        ("De'Aaron Fox", "DeAaron Fox"),
        ("Shai Gilgeous-Alexander", "Shai Gilgeous Alexander"),
    ],
)
def test_normalize_name_matches_across_sources(a, b):
    assert normalize_name(a) == normalize_name(b)


def test_normalize_name_keeps_distinct_players_distinct():
    assert normalize_name("Jalen Williams") != normalize_name("Jaylin Williams")
