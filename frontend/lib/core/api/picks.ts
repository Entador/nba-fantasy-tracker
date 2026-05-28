import { fetchAPI } from './client';
import type { BackendPick, PickImportResult, PicksResponse } from './types';

export async function getPicks(): Promise<PicksResponse> {
  return fetchAPI<PicksResponse>('/api/picks');
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

/**
 * Bulk import picks in a single request. Authoritative (TTFL history is the source
 * of truth): bypasses eligibility and overwrites any existing pick on the same night.
 */
export async function createPicksBatch(
  picks: { playerId: number | null; date: string }[]
): Promise<PickImportResult> {
  return fetchAPI<PickImportResult>('/api/picks/batch', {
    method: 'POST',
    body: JSON.stringify({
      picks: picks.map((p) => ({ player_id: p.playerId, game_date: p.date })),
    }),
  });
}
