import useSWR from 'swr';

import { BackendPick, createPick, deletePick, getPicks } from '@/lib/api';
import { Pick } from '@/lib/picks';

const KEY = '/api/picks';

/** Map a backend pick to the shape the UI logic expects (-1 = skipped night). */
function toPick(bp: BackendPick): Pick {
  return {
    id: bp.id,
    playerId: bp.player_id ?? -1,
    date: bp.game_date,
    isSkipped: bp.player_id === null,
  };
}

/** Optimistically upsert one night's entry into the cached backend list. */
function upsert(list: BackendPick[], playerId: number | null, date: string): BackendPick[] {
  const others = list.filter((p) => p.game_date !== date);
  return [{ id: -1, player_id: playerId, game_date: date, picked_at: null }, ...others];
}

/**
 * Picks state, backed by the server (guest via the anon_id cookie, or the
 * signed-in user). Mutations update the SWR cache optimistically and roll back
 * if the request fails, so the UI stays snappy without going stale.
 */
export function usePicks() {
  const { data, error, isLoading, mutate } = useSWR<BackendPick[]>(KEY, getPicks, {
    revalidateOnFocus: false,
  });

  const list = data ?? [];
  const picks: Pick[] = list.map(toPick);

  async function setPick(playerId: number, date: string) {
    await mutate(
      async () => {
        await createPick(playerId, date);
        return getPicks();
      },
      { optimisticData: upsert(list, playerId, date), rollbackOnError: true, revalidate: false }
    );
  }

  async function skip(date: string) {
    await mutate(
      async () => {
        await createPick(null, date); // null player = skip
        return getPicks();
      },
      { optimisticData: upsert(list, null, date), rollbackOnError: true, revalidate: false }
    );
  }

  async function clearPick(date: string) {
    const target = list.find((p) => p.game_date === date);
    if (!target) return;
    await mutate(
      async () => {
        await deletePick(target.id);
        return getPicks();
      },
      {
        optimisticData: list.filter((p) => p.game_date !== date),
        rollbackOnError: true,
        revalidate: false,
      }
    );
  }

  /** Bulk import (e.g. TTFL history). Picks that violate eligibility are counted as skipped. */
  async function importMany(newPicks: { playerId: number; date: string }[]) {
    let imported = 0;
    let skipped = 0;
    for (const p of newPicks) {
      try {
        await createPick(p.playerId, p.date);
        imported++;
      } catch {
        skipped++;
      }
    }
    await mutate();
    return { imported, skipped };
  }

  return { picks, isLoading, error, setPick, skip, clearPick, importMany, mutate };
}
