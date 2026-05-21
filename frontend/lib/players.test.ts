import { describe, it, expect } from 'vitest';

import { filterAndSortPlayers, parseSort, PlayerWithEligibility } from './players';

function makePlayer(overrides: Partial<PlayerWithEligibility> = {}): PlayerWithEligibility {
  return {
    player_id: 1,
    name: 'Default Player',
    team: 'LAL',
    team_id: 1,
    avg_fantasy: 30,
    avg_fantasy_week_ago: 30,
    avg_fantasy_l10: 30,
    avg_fantasy_l30d: 30,
    avg_fantasy_playoffs: null,
    avg_fantasy_current_round: null,
    avg_fantasy_last_round: null,
    rank_delta: null,
    injury_status: null,
    injury_return_date: null,
    injury_details: null,
    opponent: 'BOS',
    is_home: true,
    opp_pace: 100,
    opp_def_rating: 110,
    is_back_to_back: false,
    is_eligible: true,
    last_picked_date: null,
    days_until_eligible: null,
    ...overrides,
  };
}

describe('parseSort', () => {
  it('splits field and direction on the last hyphen', () => {
    expect(parseSort('season-desc')).toEqual({ field: 'season', direction: 'desc' });
    expect(parseSort('name-asc')).toEqual({ field: 'name', direction: 'asc' });
  });
});

describe('filterAndSortPlayers', () => {
  const alice = makePlayer({ player_id: 1, name: 'Alice', avg_fantasy: 40, is_eligible: true });
  const bob = makePlayer({ player_id: 2, name: 'Bob', avg_fantasy: 20, is_eligible: false });
  const carol = makePlayer({ player_id: 3, name: 'Carol', avg_fantasy: 30, is_eligible: true });

  it('filters to eligible players when filterBy is available', () => {
    const result = filterAndSortPlayers([alice, bob, carol], 'available', 'name-asc', null);
    expect(result.map((p) => p.name)).toEqual(['Alice', 'Carol']);
  });

  it('filters to ineligible players when filterBy is locked', () => {
    const result = filterAndSortPlayers([alice, bob, carol], 'locked', 'name-asc', null);
    expect(result.map((p) => p.name)).toEqual(['Bob']);
  });

  it('sorts by stat descending', () => {
    const result = filterAndSortPlayers([alice, bob, carol], 'all', 'season-desc', null);
    expect(result.map((p) => p.avg_fantasy)).toEqual([40, 30, 20]);
  });

  it('sorts by stat ascending', () => {
    const result = filterAndSortPlayers([alice, bob, carol], 'all', 'season-asc', null);
    expect(result.map((p) => p.avg_fantasy)).toEqual([20, 30, 40]);
  });

  it('sorts by name alphabetically', () => {
    const result = filterAndSortPlayers([carol, alice, bob], 'all', 'name-asc', null);
    expect(result.map((p) => p.name)).toEqual(['Alice', 'Bob', 'Carol']);
  });

  it('sinks null stats to the bottom regardless of direction', () => {
    // The week accessor treats 0 as a "no data" sentinel and returns null.
    const withStat = makePlayer({ player_id: 10, name: 'Has', avg_fantasy_week_ago: 25 });
    const noStat = makePlayer({ player_id: 11, name: 'None', avg_fantasy_week_ago: 0 });
    const ascResult = filterAndSortPlayers([noStat, withStat], 'all', 'week-asc', null);
    expect(ascResult.map((p) => p.name)).toEqual(['Has', 'None']);
    const descResult = filterAndSortPlayers([noStat, withStat], 'all', 'week-desc', null);
    expect(descResult.map((p) => p.name)).toEqual(['Has', 'None']);
  });

  it('filters by selected game using away-home key', () => {
    // Alice is home for LAL vs BOS -> key "BOS-LAL"
    // Make a different matchup
    const dallasPlayer = makePlayer({
      player_id: 99,
      name: 'Dirk',
      team: 'DAL',
      opponent: 'PHX',
      is_home: false, // away player: key = `${team}-${opponent}` = "DAL-PHX"
    });
    const result = filterAndSortPlayers([alice, dallasPlayer], 'all', 'name-asc', 'BOS-LAL');
    expect(result.map((p) => p.name)).toEqual(['Alice']);
  });

  it('does not mutate the input array', () => {
    const players = [bob, alice, carol];
    const snapshot = [...players];
    filterAndSortPlayers(players, 'all', 'season-desc', null);
    expect(players).toEqual(snapshot);
  });
});
