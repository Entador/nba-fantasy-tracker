"""Player statistics calculation services."""
from collections import defaultdict
from datetime import date, timedelta
from sqlalchemy.orm import Session

from models import Game, FantasyScore


def get_playoff_round(nba_game_id: str) -> int | None:
    """Extract round number (1-4) from an NBA playoff game ID.

    Playoff IDs follow: 004 + YY (season) + 00 (padding) + R (round) + GG (game)
    Example: '0042400201' → round 2
    """
    if nba_game_id.startswith('004') and len(nba_game_id) >= 8:
        r = nba_game_id[7]
        if r.isdigit():
            return int(r)
    return None


def batch_calculate_averages(
    db: Session,
    player_ids: list[int],
    current_playoff_round: int | None = None,
    last_playoff_round: int | None = None,
) -> dict[int, dict]:
    """
    Calculate Fantasy averages for multiple players in a single query.

    Returns dict: {player_id: {
        'avg_fantasy': all games this season,
        'avg_fantasy_l10': last 10 games,
        'avg_fantasy_l30d': last 30 days,
        'avg_fantasy_week_ago': all games before 14 days ago (for rank delta and -14d column),
        'avg_fantasy_playoffs': all playoff games (004*), None if no playoff games played,
        'avg_fantasy_current_round': games in current_playoff_round, None if no games,
        'avg_fantasy_last_round': games in last_playoff_round, None if no games,
    }}
    """
    if not player_ids:
        return {}

    today = date.today()
    cutoff_30d = today - timedelta(days=30)
    cutoff_14d = today - timedelta(days=14)

    # Single query: get all scores for all players, with game dates and game IDs
    scores_data = (
        db.query(
            FantasyScore.player_id,
            FantasyScore.fantasy_score,
            Game.game_date,
            Game.nba_game_id,
        )
        .join(Game, FantasyScore.game_id == Game.id)
        .filter(
            FantasyScore.player_id.in_(player_ids),
            FantasyScore.fantasy_score.isnot(None),
            FantasyScore.minutes > 0
        )
        .order_by(FantasyScore.player_id, Game.game_date.desc())
        .all()
    )

    # Group scores by player
    player_scores = defaultdict(list)
    for player_id, fantasy_score, game_date, nba_game_id in scores_data:
        player_scores[player_id].append((fantasy_score, game_date, nba_game_id))

    # Calculate averages for each player
    result = {}
    for player_id in player_ids:
        scores = player_scores.get(player_id, [])

        # avg_fantasy: all games this season
        all_scores = [s[0] for s in scores]
        avg_fantasy = sum(all_scores) / len(all_scores) if all_scores else 0.0

        # avg_fantasy_l10: last 10 games
        last_10 = [s[0] for s in scores[:10]]
        avg_fantasy_l10 = sum(last_10) / len(last_10) if last_10 else 0.0

        # avg_fantasy_l30d: games in last 30 days
        last_30d = [fantasy for fantasy, gd, _ in scores if gd >= cutoff_30d]
        avg_fantasy_l30d = sum(last_30d) / len(last_30d) if last_30d else 0.0

        # avg_fantasy_week_ago: all games before 14 days ago (used for rank delta)
        before_14d = [fantasy for fantasy, gd, _ in scores if gd < cutoff_14d]
        avg_fantasy_week_ago = sum(before_14d) / len(before_14d) if before_14d else 0.0

        # avg_fantasy_playoffs: all playoff games
        playoff_scores = [fantasy for fantasy, _, gid in scores if gid.startswith('004')]
        avg_fantasy_playoffs = sum(playoff_scores) / len(playoff_scores) if playoff_scores else None

        # avg_fantasy_current_round: games in the current playoff round
        if current_playoff_round is not None:
            cur_scores = [fantasy for fantasy, _, gid in scores if get_playoff_round(gid) == current_playoff_round]
            avg_fantasy_current_round = sum(cur_scores) / len(cur_scores) if cur_scores else None
        else:
            avg_fantasy_current_round = None

        # avg_fantasy_last_round: games in the previous playoff round
        if last_playoff_round is not None:
            prev_scores = [fantasy for fantasy, _, gid in scores if get_playoff_round(gid) == last_playoff_round]
            avg_fantasy_last_round = sum(prev_scores) / len(prev_scores) if prev_scores else None
        else:
            avg_fantasy_last_round = None

        result[player_id] = {
            'avg_fantasy': avg_fantasy,
            'avg_fantasy_l10': avg_fantasy_l10,
            'avg_fantasy_l30d': avg_fantasy_l30d,
            'avg_fantasy_week_ago': avg_fantasy_week_ago,
            'avg_fantasy_playoffs': avg_fantasy_playoffs,
            'avg_fantasy_current_round': avg_fantasy_current_round,
            'avg_fantasy_last_round': avg_fantasy_last_round,
        }

    return result
