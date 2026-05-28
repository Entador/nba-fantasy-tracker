// API request/response shapes. No runtime dependencies — safe to import anywhere.

export interface Player {
  player_id: number;
  name: string;
  team: string;
  opponent: string;
  is_home: boolean;
  avg_fantasy: number;
  avg_fantasy_l10: number;
  avg_fantasy_l30d: number;
  opp_pace: number | null;
  opp_def_rating: number | null;
  injury_status: string | null;
  injury_return_date: string | null;
  injury_details: string | null;
}

export interface PlayerStats {
  player: {
    id: number;
    name: string;
    team: string;
  };
  recent_games: Array<{
    game_date: string;
    opponent: string;
    is_home: boolean;
    fantasy_score: number;
    minutes: number;
    dnp: boolean;
  }>;
  avg_fantasy: number;
  best_score: number;
  worst_score: number;
  std_dev: number;
  consistency: 'High' | 'Medium' | 'Low';
}

export interface SnapshotMetadata {
  generated_at: string;
  total_players: number;
  total_games: number;
  total_teams: number;
  injury_updated_at: string | null;
  earliest_game_times: Record<string, string>; // date (YYYY-MM-DD) -> ISO timestamp
  is_playoff_period: boolean;
  playoff_start_date: string | null; // YYYY-MM-DD, earliest date of a playoff game
  current_playoff_round: number | null;
  last_playoff_round: number | null;
}

export interface PlayerSnapshot {
  player_id: number;
  name: string;
  team: string;
  team_id: number;
  avg_fantasy: number;
  avg_fantasy_week_ago: number;
  avg_fantasy_l10: number;
  avg_fantasy_l30d: number;
  avg_fantasy_playoffs: number | null;
  avg_fantasy_current_round: number | null;
  avg_fantasy_last_round: number | null;
  rank_delta: number | null;
  injury_status: string | null;
  injury_return_date: string | null;
  injury_details: string | null;
}

export interface GameSnapshot {
  game_date: string;
  home_team: string;
  away_team: string;
  home_team_id: number;
  away_team_id: number;
}

export interface TeamSnapshot {
  team_id: number;
  abbreviation: string;
  full_name: string;
  pace: number;
  def_rating: number;
}

export interface SnapshotData {
  metadata: SnapshotMetadata;
  players: PlayerSnapshot[];
  games: GameSnapshot[];
  teams: TeamSnapshot[];
}

export interface PlayerBasic {
  player_id: number;
  name: string;
  team: string;
}

// Picks — owner (guest or user) resolved server-side from the cookie/JWT.
export interface BackendPick {
  id: number;
  player_id: number | null; // null = a deliberately skipped night
  game_date: string; // YYYY-MM-DD
  picked_at: string | null;
}

// Per-player eligibility lock derived server-side from the caller's picks (the
// 30-day / playoff rule lives in the backend). available_on is the first date the
// player can be picked again; null = locked for the rest of the playoff run.
// Only locked players appear; anyone absent is eligible.
export interface PlayerLock {
  player_id: number;
  available_on: string | null; // YYYY-MM-DD, or null during the playoffs
}

export interface PicksResponse {
  picks: BackendPick[];
  locks: PlayerLock[];
}

export interface PickImportResult {
  imported: number;
  skipped: number; // player_id not found in the backend (matched names should be 0)
}

// Auth — JWT lives in HttpOnly cookie on web; mobile will swap to a bearer token.
export interface AuthUser {
  id: number;
  email: string | null;
  is_active: boolean;
  is_verified: boolean;
}
