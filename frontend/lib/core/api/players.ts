import { fetchAPI } from './client';
import type { PlayerBasic, PlayerStats, SnapshotData } from './types';

export async function getPlayerStats(playerId: number): Promise<PlayerStats> {
  return fetchAPI<PlayerStats>(`/api/players/${playerId}/stats`);
}

export async function getSnapshot(): Promise<SnapshotData> {
  return fetchAPI<SnapshotData>('/api/snapshot');
}

export async function getAllPlayers(): Promise<PlayerBasic[]> {
  return fetchAPI<PlayerBasic[]>('/api/players/all');
}
