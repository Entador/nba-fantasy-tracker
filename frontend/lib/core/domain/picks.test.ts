import { describe, it, expect } from 'vitest';

import type { PlayerLock } from '../api/types';
import { enrichPlayersWithEligibility } from './picks';

const players = [{ player_id: 1 }, { player_id: 2 }];

// Regular-season window: a pick on P locks (P, P+30), open at both ends.
const regularLock: PlayerLock = {
  player_id: 1,
  locked_from: '2026-06-03',
  available_on: '2026-07-03',
};

describe('enrichPlayersWithEligibility', () => {
  it('marks a player eligible when no lock applies', () => {
    const [p1] = enrichPlayersWithEligibility([players[0]], [], '2026-06-03');
    expect(p1.is_eligible).toBe(true);
  });

  it('locks the days strictly after the pick date', () => {
    const [p1] = enrichPlayersWithEligibility(players, [regularLock], '2026-06-10');
    expect(p1.is_eligible).toBe(false);
    expect(p1.days_until_eligible).toBe(23); // 2026-07-03 - 2026-06-10
  });

  it('does NOT lock the pick date itself (window is open at locked_from)', () => {
    const [p1] = enrichPlayersWithEligibility(players, [regularLock], '2026-06-03');
    expect(p1.is_eligible).toBe(true);
  });

  it('does NOT lock dates before the pick date (backward-only window)', () => {
    const [p1] = enrichPlayersWithEligibility(players, [regularLock], '2026-06-01');
    expect(p1.is_eligible).toBe(true);
  });

  it('is eligible again on available_on (window is open at the end)', () => {
    const [p1] = enrichPlayersWithEligibility(players, [regularLock], '2026-07-03');
    expect(p1.is_eligible).toBe(true);
  });

  it('honours separate windows when the same player is picked twice', () => {
    const locks: PlayerLock[] = [
      regularLock, // (2026-06-03, 2026-07-03)
      { player_id: 1, locked_from: '2026-07-04', available_on: '2026-08-03' },
    ];
    // Between the two windows: eligible.
    expect(enrichPlayersWithEligibility(players, locks, '2026-07-03')[0].is_eligible).toBe(true);
    // Inside the second window: locked.
    expect(enrichPlayersWithEligibility(players, locks, '2026-07-10')[0].is_eligible).toBe(false);
  });

  it('ignores a stale lock for a player no longer in the picks set', () => {
    const playoffLock: PlayerLock = {
      player_id: 1,
      locked_from: '2026-04-18',
      available_on: null,
    };
    // Player 1 was just unpicked (optimistic): no longer in pickedPlayerIds, so its
    // lingering lock must not lock it — the bug where the unpicked player vanished.
    const pickedPlayerIds = new Set<number>([2]);
    const [p1] = enrichPlayersWithEligibility(
      players,
      [playoffLock],
      '2026-05-01',
      null,
      pickedPlayerIds
    );
    expect(p1.is_eligible).toBe(true);
  });

  it('treats the current pick as eligible regardless of its lock (playoffs)', () => {
    const playoffLock: PlayerLock = {
      player_id: 1,
      locked_from: '2026-04-18',
      available_on: null, // locked for the whole run
    };
    const lockedNotCurrent = enrichPlayersWithEligibility(players, [playoffLock], '2026-05-01');
    expect(lockedNotCurrent[0].is_eligible).toBe(false);
    expect(lockedNotCurrent[0].days_until_eligible).toBeNull();

    const asCurrentPick = enrichPlayersWithEligibility(players, [playoffLock], '2026-05-01', 1);
    expect(asCurrentPick[0].is_eligible).toBe(true);
  });
});
