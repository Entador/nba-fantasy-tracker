/**
 * Pure helpers for reasoning about Fantasy picks.
 *
 * Picks themselves live in the backend (see hooks/usePicks); this module only
 * holds the storage-agnostic logic — eligibility and forgotten-date detection —
 * that operates on a `Pick[]` passed in by the caller.
 */

import type { PlayerLock } from '../api/types';
import { toDateKey } from '../utils/date';

export interface Pick {
  id?: number; // backend pick id (used to delete); absent for optimistic entries
  playerId: number; // -1 = a deliberately skipped night (see isSkipped)
  date: string; // YYYY-MM-DD format
  isSkipped?: boolean; // true if the night was intentionally skipped (no pick made)
  fantasyScore?: number | null;
}

type Eligibility = {
  is_eligible: boolean;
  last_picked_date: string | null;
  days_until_eligible: number | null;
};

const ELIGIBLE: Eligibility = {
  is_eligible: true,
  last_picked_date: null,
  days_until_eligible: null,
};

/**
 * Resolve one player's eligibility on `currentDate` from their server-computed locks.
 *
 * Each lock is an open window `(locked_from, available_on)`: the player is locked iff
 * the viewed date sits strictly inside one of them. The backend owns the rule (window
 * size, backward-only direction, playoff semantics); this is just a membership read,
 * so a pick never locks its own date or earlier — only strictly after. `available_on`
 * null means the lock runs to the end of the playoff run. No locks ⇒ eligible.
 */
function resolveEligibility(locks: PlayerLock[], currentDate: string): Eligibility {
  // ISO dates compare lexicographically, so plain string comparison works.
  const active = locks.find(
    (l) =>
      l.locked_from < currentDate &&
      (l.available_on === null || currentDate < l.available_on)
  );
  if (!active) return ELIGIBLE;

  if (active.available_on === null) {
    return { is_eligible: false, last_picked_date: null, days_until_eligible: null };
  }
  const days = Math.round(
    (new Date(active.available_on).getTime() - new Date(currentDate).getTime()) / 86_400_000
  );
  return { is_eligible: false, last_picked_date: null, days_until_eligible: days };
}

/**
 * Enrich players with eligibility derived from the server-computed `locks`.
 *
 * The 30-day / playoff rule lives in the backend (picks/service.compute_locks); each
 * lock is a window, independent of the viewed date — so this stays a cheap pure read
 * across all date navigation.
 *
 * The player currently selected for `currentDate` is always eligible: that's your
 * active pick, not a lock against keeping it tonight. (Regular-season windows already
 * exclude the pick's own date, so this only matters during the playoffs, where a
 * pick locks the player for every other date in the run.)
 *
 * `pickedPlayerIds` is the set of players in the caller's current picks. Every lock the
 * server returns is derived from one of those picks, so a lock for a player who is no
 * longer picked is stale (the picks mutated optimistically before the recomputed locks
 * landed) and is ignored — this is what stops a just-unpicked player from briefly
 * showing as locked. Steady state it's a no-op (locks ⊆ picked players). Pass null to
 * skip the check.
 *
 * Pure function — call from a useMemo in the component.
 */
export function enrichPlayersWithEligibility<T extends { player_id: number }>(
  players: T[],
  locks: PlayerLock[],
  currentDate: string,
  currentPickId: number | null = null,
  pickedPlayerIds: Set<number> | null = null
): Array<T & Eligibility> {
  const locksByPlayer = new Map<number, PlayerLock[]>();
  for (const lock of locks) {
    if (pickedPlayerIds && !pickedPlayerIds.has(lock.player_id)) continue; // stale lock
    const existing = locksByPlayer.get(lock.player_id);
    if (existing) existing.push(lock);
    else locksByPlayer.set(lock.player_id, [lock]);
  }

  return players.map((player) => ({
    ...player,
    ...(player.player_id === currentPickId
      ? ELIGIBLE
      : resolveEligibility(locksByPlayer.get(player.player_id) ?? [], currentDate)),
  }));
}

/**
 * Detect dates in the last 30 days that had scheduled games but no pick/skip recorded.
 * Returns an array of forgotten dates sorted from oldest to newest.
 */
export function getForgottenDates(
  picks: Pick[],
  snapshot: { games: { game_date: string }[] },
  currentDate: string
): string[] {
  const current = new Date(currentDate);
  const forgottenDates: string[] = [];

  const pickedDates = new Set(picks.map((p) => p.date));

  for (let i = 1; i <= 30; i++) {
    const checkDate = new Date(current);
    checkDate.setDate(current.getDate() - i);
    const dateStr = toDateKey(checkDate);

    if (pickedDates.has(dateStr)) continue;

    const gamesForDate = snapshot.games.filter((g) => g.game_date === dateStr);
    if (gamesForDate.length > 0) {
      forgottenDates.push(dateStr);
    }
  }

  return forgottenDates.sort();
}
