from core.fantasy import calculate_fantasy_score


def test_calculate_fantasy_score_when_empty_box_then_zero():
    assert calculate_fantasy_score({}) == 0


def test_calculate_fantasy_score_when_none_values_then_treated_as_zero():
    box = {"PTS": None, "REB": None, "AST": None, "FGA": None, "FGM": None}
    assert calculate_fantasy_score(box) == 0


def test_calculate_fantasy_score_when_perfect_shooting_then_positives_only():
    # 20 PTS, 5 REB, 5 AST, 1 STL, 1 BLK, 8/8 FG, 2/2 3P, 2/2 FT, 0 TOV
    box = {
        "PTS": 20, "REB": 5, "AST": 5, "STL": 1, "BLK": 1,
        "FGM": 8, "FGA": 8, "FG3M": 2, "FG3A": 2, "FTM": 2, "FTA": 2,
        "TOV": 0,
    }
    # positives: 20+5+5+1+1+8+2+2 = 44, no misses, no TOV
    assert calculate_fantasy_score(box) == 44


def test_calculate_fantasy_score_subtracts_misses_and_turnovers():
    # 10 PTS, 4/10 FG (6 missed), 1/4 3P (3 missed), 2/4 FT (2 missed), 3 TOV
    box = {
        "PTS": 10, "REB": 3, "AST": 2, "STL": 0, "BLK": 0,
        "FGM": 4, "FGA": 10, "FG3M": 1, "FG3A": 4, "FTM": 2, "FTA": 4,
        "TOV": 3,
    }
    # positives: 10+3+2+0+0+4+1+2 = 22
    # negatives: 3 (TOV) + 6 (FG miss) + 3 (3P miss) + 2 (FT miss) = 14
    assert calculate_fantasy_score(box) == 8


def test_calculate_fantasy_score_returns_int():
    box = {"PTS": 10.0, "REB": 5.0}
    result = calculate_fantasy_score(box)
    assert isinstance(result, int)
