"""Season and game-type identity.

An NBA game ID encodes both the season and the kind of game:

    0 0 2  2 6  0 0 1 2 3
    └─┬─┘  └┬┘  └───┬───┘
      │     │       └─ sequence within the season
      │     └───────── season start year, 2 digits ("26" -> 2026-27)
      └─────────────── game type (see the prefixes below)

Everything season-scoped goes through this module, so "which season is this?"
and "is this a playoff game?" are answered in one place instead of by ad-hoc
`nba_game_id.startswith(...)` tests spread across services and scripts. That
matters once a second season lands in the DB: without scoping, last season's
playoff games keep the app in playoff mode forever.
"""

from datetime import date

# Game type — the first three digits of the ID.
PRESEASON = "001"
REGULAR_SEASON = "002"
ALL_STAR = "003"
PLAYOFFS = "004"
PLAY_IN = "005"
CUP_FINAL = "006"

# Game types that count in Fantasy, and so are the only ones we import.
# Excluded: pre-season and All-Star (not real NBA games for scoring purposes)
# and the NBA Cup final — the Cup's group and knockout games are tagged '002'
# by the league and count toward the 82, but the championship game sits outside
# the regular season and its stats don't count toward season averages.
PICKABLE_TYPES = (REGULAR_SEASON, PLAYOFFS, PLAY_IN)

# The NBA season is named after the year it starts in; pre-season tips off in
# early October, so that's where one season ends and the next begins.
SEASON_START_MONTH = 10


def format_season(start_year: int) -> str:
    """2026 -> '2026-27'."""
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def current_season(today: date | None = None) -> str:
    """The season a given day belongs to, e.g. '2026-27'.

    Rolls over on October 1st: earlier months still belong to the season that
    started the previous October, since the playoffs run into June.
    """
    today = today or date.today()
    start_year = today.year if today.month >= SEASON_START_MONTH else today.year - 1
    return format_season(start_year)


def season_of_game_id(nba_game_id: str) -> str | None:
    """The season a game ID belongs to, or None if the ID isn't parseable."""
    if len(nba_game_id) < 5 or not nba_game_id[3:5].isdigit():
        return None
    return format_season(2000 + int(nba_game_id[3:5]))


def is_pickable(nba_game_id: str) -> bool:
    """True if the game counts in Fantasy — see PICKABLE_TYPES."""
    return nba_game_id.startswith(PICKABLE_TYPES)


def is_regular_season(nba_game_id: str) -> bool:
    return nba_game_id.startswith(REGULAR_SEASON)


def is_playoffs(nba_game_id: str) -> bool:
    """True for playoff games only — the play-in ('005') doesn't count.

    Pick eligibility depends on this: the once-per-playoffs rule takes over
    from the 30-day window when the playoffs start, and the play-in is still
    played under regular-season rules.
    """
    return nba_game_id.startswith(PLAYOFFS)
