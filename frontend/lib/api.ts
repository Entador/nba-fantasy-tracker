// Use internal Docker hostname for server-side, public URL for client-side
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Get today's date in Eastern Time (America/New_York).
 * NBA schedule uses ET, so we align with it for consistent "tonight" behavior.
 */
export function getTodayET(): string {
  return new Date().toLocaleDateString('en-CA', {
    timeZone: 'America/New_York',
  });
}

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
  consistency: "High" | "Medium" | "Low";
}


/**
 * Fetch from API - works both server-side and client-side.
 * Server-side: uses cache: 'no-store' for fresh data
 * Client-side: standard fetch
 */
async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      credentials: 'include', // send/receive the anon_id (and future auth) cookie
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    // 204 No Content (e.g. DELETE) has no body to parse.
    if (response.status === 204) return undefined as T;
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

export async function getPlayerStats(playerId: number): Promise<PlayerStats> {
  return await fetchAPI<PlayerStats>(`/api/players/${playerId}/stats`);
}


// Snapshot API - returns entire season data
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

export async function getSnapshot(): Promise<SnapshotData> {
  return fetchAPI<SnapshotData>('/api/snapshot');
}

export interface PlayerBasic {
  player_id: number;
  name: string;
  team: string;
}

export async function getAllPlayers(): Promise<PlayerBasic[]> {
  return await fetchAPI<PlayerBasic[]>('/api/players/all');
}

// Picks API — owner (guest or user) is resolved server-side from the cookie/JWT.
export interface BackendPick {
  id: number;
  player_id: number | null; // null = a deliberately skipped night
  game_date: string; // YYYY-MM-DD
  picked_at: string | null;
}

export async function getPicks(): Promise<BackendPick[]> {
  return fetchAPI<BackendPick[]>('/api/picks');
}

/** Upsert this night's pick. playerId = null records a skip. */
export async function createPick(
  playerId: number | null,
  gameDate: string
): Promise<BackendPick> {
  return fetchAPI<BackendPick>('/api/picks', {
    method: 'POST',
    body: JSON.stringify({ player_id: playerId, game_date: gameDate }),
  });
}

export async function deletePick(id: number): Promise<void> {
  await fetchAPI<void>(`/api/picks/${id}`, { method: 'DELETE' });
}
