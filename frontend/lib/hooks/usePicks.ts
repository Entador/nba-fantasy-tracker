import useSWR from 'swr';

import { PicksResponse, createPick, createPicksBatch, deletePick, getPicks } from '@/lib/api';
import { Pick } from '@/lib/picks';
import { useAuth } from '@/lib/hooks/useAuth';

const KEY = '/api/picks';
const EMPTY: PicksResponse = { picks: [], locks: [] };

/** Map a backend pick to the shape the UI logic expects (-1 = skipped night). */
function toPick(bp: PicksResponse['picks'][number]): Pick {
  return {
    id: bp.id,
    playerId: bp.player_id ?? -1,
    date: bp.game_date,
    isSkipped: bp.player_id === null,
  };
}

/**
 * Optimistically upsert one night's entry. Locks are left untouched: they're
 * recomputed server-side and refreshed by the getPicks() that resolves the mutation,
 * so a brief staleness between the optimistic write and the response is harmless.
 */
function upsert(data: PicksResponse, playerId: number | null, date: string): PicksResponse {
  const others = data.picks.filter((p) => p.game_date !== date);
  return {
    picks: [{ id: -1, player_id: playerId, game_date: date, picked_at: null }, ...others],
    locks: data.locks,
  };
}

/**
 * Picks state, backed by the server (guest via the anon_id cookie, or the
 * signed-in user). Mutations update the SWR cache optimistically and roll back
 * if the request fails, so the UI stays snappy without going stale.
 */
export function usePicks() {
  // Gate the picks fetch on auth resolving. /api/picks now 401s a lapsed login (the
  // server tells an expired session from a guest by the access_token cookie's
  // presence), which fetchAPI transparently refreshes and retries — so correctness
  // no longer depends on this gate. We keep it as an optimization: useAuth() already
  // refreshes the token while resolving /users/me, so waiting for it means the picks
  // request goes out once with a fresh token instead of fetching, 401ing, refetching.
  const { isLoading: authLoading } = useAuth();
  const { data, error, isLoading, mutate } = useSWR<PicksResponse>(
    authLoading ? null : KEY,
    getPicks,
    { revalidateOnFocus: false }
  );

  const current = data ?? EMPTY;
  const picks: Pick[] = current.picks.map(toPick);
  const locks = current.locks;

  async function setPick(playerId: number, date: string) {
    await mutate(
      async () => {
        await createPick(playerId, date);
        return getPicks();
      },
      { optimisticData: upsert(current, playerId, date), rollbackOnError: true, revalidate: false }
    );
  }

  async function skip(date: string) {
    await mutate(
      async () => {
        await createPick(null, date); // null player = skip
        return getPicks();
      },
      { optimisticData: upsert(current, null, date), rollbackOnError: true, revalidate: false }
    );
  }

  async function clearPick(date: string) {
    const target = current.picks.find((p) => p.game_date === date);
    if (!target) return;
    await mutate(
      async () => {
        await deletePick(target.id);
        return getPicks();
      },
      {
        optimisticData: {
          picks: current.picks.filter((p) => p.game_date !== date),
          locks: current.locks,
        },
        rollbackOnError: true,
        revalidate: false,
      }
    );
  }

  /**
   * Bulk import (e.g. TTFL history) in a single request. Authoritative: overwrites
   * clashing nights and bypasses eligibility. `skipped` counts unknown player ids.
   */
  async function importMany(newPicks: { playerId: number; date: string }[]) {
    const result = await createPicksBatch(newPicks);
    await mutate();
    return result;
  }

  // authLoading counts as loading: while the key is null SWR reports isLoading=false,
  // but picks aren't ready yet — callers must keep showing the skeleton, not an empty list.
  return { picks, locks, isLoading: authLoading || isLoading, error, setPick, skip, clearPick, importMany, mutate };
}
