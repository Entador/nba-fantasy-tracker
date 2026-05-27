/**
 * Pure helpers for reasoning about Fantasy picks.
 *
 * Picks themselves live in the backend (see `lib/hooks/usePicks`); this module
 * only holds the storage-agnostic logic — eligibility and forgotten-date
 * detection — that operates on a `Pick[]` passed in by the caller.
 */

import { PlayerLock } from '@/lib/api';

export interface Pick {
  id?: number; // backend pick id (used to delete); absent for optimistic entries
  playerId: number; // -1 = a deliberately skipped night (see isSkipped)
  date: string; // YYYY-MM-DD format
  isSkipped?: boolean; // true if the night was intentionally skipped (no pick made)
}

/**
 * Convert a Date object to a YYYY-MM-DD string.
 */
export function toDateKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
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
 * Resolve one player's eligibility on `currentDate` from their server-computed lock.
 * `availableOn` is undefined when the player has no lock (eligible), null when locked
 * for the whole playoff run, or the date they become pickable again.
 */
function resolveEligibility(
  availableOn: string | null | undefined,
  currentDate: string
): Eligibility {
  if (availableOn === undefined) return ELIGIBLE;
  if (availableOn === null) {
    return { is_eligible: false, last_picked_date: null, days_until_eligible: null };
  }
  if (currentDate >= availableOn) return ELIGIBLE; // ISO dates compare lexicographically

  const days = Math.round(
    (new Date(availableOn).getTime() - new Date(currentDate).getTime()) / 86_400_000
  );
  return { is_eligible: false, last_picked_date: null, days_until_eligible: days };
}

/**
 * Enrich players with eligibility derived from the server-computed `locks`.
 *
 * The 30-day / playoff rule lives in the backend (picks/service.compute_locks); each
 * lock just says when a picked player is eligible again, independent of the viewed
 * date — so this stays a cheap pure read across all date navigation.
 *
 * The player currently selected for `currentDate` is always eligible: that's your
 * active pick, not a lock against keeping it tonight. (A player picked today can't
 * have any other lock — you can't pick the same player twice within the window.)
 *
 * Pure function — call from a useMemo in the component.
 */
export function enrichPlayersWithEligibility<T extends { player_id: number }>(
  players: T[],
  locks: PlayerLock[],
  currentDate: string,
  currentPickId: number | null = null
): Array<T & Eligibility> {
  const availableByPlayer = new Map(locks.map((l) => [l.player_id, l.available_on]));

  return players.map((player) => ({
    ...player,
    ...resolveEligibility(
      player.player_id === currentPickId
        ? undefined
        : availableByPlayer.get(player.player_id),
      currentDate
    ),
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

  // Build a Set of dates with picks/skips for O(1) lookup
  const pickedDates = new Set(picks.map((p) => p.date));

  // Check each of the last 30 days (1-30 days ago, NOT including current date)
  for (let i = 1; i <= 30; i++) {
    const checkDate = new Date(current);
    checkDate.setDate(current.getDate() - i);
    const dateStr = toDateKey(checkDate);

    // Skip if a pick/skip already exists for this date
    if (pickedDates.has(dateStr)) continue;

    // Only count dates that actually had scheduled games
    const gamesForDate = snapshot.games.filter((g) => g.game_date === dateStr);
    if (gamesForDate.length > 0) {
      forgottenDates.push(dateStr);
    }
  }

  return forgottenDates.sort(); // Oldest first
}
