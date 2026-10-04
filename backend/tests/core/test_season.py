"""Season identity: the October rollover and game-ID parsing."""

from datetime import date

from core.season import (
    current_season,
    is_playoffs,
    is_regular_season,
    season_of_game_id,
)


class TestCurrentSeason:
    def test_october_starts_the_new_season(self):
        assert current_season(date(2026, 10, 1)) == "2026-27"

    def test_september_still_belongs_to_the_previous_season(self):
        assert current_season(date(2026, 9, 30)) == "2025-26"

    def test_spring_playoffs_belong_to_the_season_that_started_in_october(self):
        assert current_season(date(2027, 6, 15)) == "2026-27"

    def test_decade_rollover_pads_the_short_year(self):
        assert current_season(date(2029, 11, 1)) == "2029-30"


class TestSeasonOfGameId:
    def test_regular_season_game(self):
        assert season_of_game_id("0022600123") == "2026-27"

    def test_playoff_game_from_a_past_season(self):
        assert season_of_game_id("0042500101") == "2025-26"

    def test_unparseable_id_returns_none(self):
        assert season_of_game_id("00") is None
        assert season_of_game_id("002XX00123") is None


class TestGameType:
    def test_regular_season(self):
        assert is_regular_season("0022600123")
        assert not is_regular_season("0042600101")

    def test_playoffs_excludes_the_play_in(self):
        assert is_playoffs("0042600101")
        assert not is_playoffs("0052600101")  # play-in runs under 30-day rules
