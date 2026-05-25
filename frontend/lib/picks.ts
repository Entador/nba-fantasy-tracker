/**
 * Pure helpers for reasoning about Fantasy picks.
 *
 * Picks themselves live in the backend (see `lib/hooks/usePicks`); this module
 * only holds the storage-agnostic logic — eligibility and forgotten-date
 * detection — that operates on a `Pick[]` passed in by the caller.
 */

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

export interface EligibilityInfo {
  isEligible: boolean;
  lastPickedDate: string | null;
  daysUntilEligible: number | null;
}

/**
 * Compute eligibility for multiple players at once.
 * Reads picks once and builds a lookup map — use this for bulk operations.
 *
 * Returns a Map<playerId, EligibilityInfo>.
 * Players not in the map are eligible (no recent picks found).
 *
 * @param playoffStartDate - If provided, activates playoff rules: each player can only
 *   be picked once for the entire playoff period. A pick is classified as a playoff pick
 *   by comparing its date against this threshold (not by a flag on the pick),
 *   so retroactively edited regular-season picks are never misclassified.
 */
export function computeEligibilityMap(
  picks: Pick[],
  currentDate: string,
  playoffStartDate: string | null
): Map<number, EligibilityInfo> {
  const map = new Map<number, EligibilityInfo>();

  if (playoffStartDate) {
    // Playoff rules: ineligible if picked on any other date during the playoff period
    const playoffPickedIds = new Set(
      picks
        .filter((p) => !p.isSkipped && p.date >= playoffStartDate && p.date !== currentDate)
        .map((p) => p.playerId)
    );
    playoffPickedIds.forEach((id) => {
      map.set(id, { isEligible: false, lastPickedDate: null, daysUntilEligible: null });
    });
    return map;
  }

  // Regular season: 30-day window
  const from = new Date(currentDate);

  picks.forEach((pick) => {
    if (pick.isSkipped) return;

    const pickDate = new Date(pick.date);
    const diffDays = Math.floor(
      (from.getTime() - pickDate.getTime()) / (1000 * 60 * 60 * 24)
    );

    // Pick counts if it was 1-29 days ago (within 30-day window, but NOT same day)
    if (diffDays > 0 && diffDays < 30) {
      const existing = map.get(pick.playerId);
      if (!existing || pick.date > existing.lastPickedDate!) {
        map.set(pick.playerId, {
          isEligible: false,
          lastPickedDate: pick.date,
          daysUntilEligible: 30 - diffDays,
        });
      }
    }
  });

  return map;
}

/**
 * Enrich a list of players with eligibility data from the given picks.
 * Pure function — call from a useMemo in the component.
 */
export function enrichPlayersWithEligibility<T extends { player_id: number }>(
  players: T[],
  allPicks: Pick[],
  currentDate: string,
  playoffStartDate: string | null
): Array<T & { is_eligible: boolean; last_picked_date: string | null; days_until_eligible: number | null }> {
  const eligibilityMap = computeEligibilityMap(allPicks, currentDate, playoffStartDate);

  return players.map((player) => {
    const eligibility = eligibilityMap.get(player.player_id);
    return {
      ...player,
      is_eligible: eligibility ? eligibility.isEligible : true,
      last_picked_date: eligibility?.lastPickedDate ?? null,
      days_until_eligible: eligibility?.daysUntilEligible ?? null,
    };
  });
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
