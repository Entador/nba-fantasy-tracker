import { EnrichedPlayer } from './snapshot';
import { STAT_COLUMN_BY_FIELD, StatSortField } from './statColumns';

export type SortField =
  | 'name'
  | 'matchup'
  | 'pace'
  | 'drtg'
  | 'season'
  | 'week'
  | 'l10'
  | 'l30'
  | 'playoffs'
  | 'lastround'
  | 'currentround';
export type SortDirection = 'asc' | 'desc';
export type SortOption = `${SortField}-${SortDirection}`;
export type FilterOption = 'all' | 'available' | 'locked';

export interface PlayerWithEligibility extends EnrichedPlayer {
  is_eligible: boolean;
  last_picked_date: string | null;
  days_until_eligible: number | null;
}

export function parseSort(sort: SortOption): { field: SortField; direction: SortDirection } {
  const idx = sort.lastIndexOf('-');
  return {
    field: sort.slice(0, idx) as SortField,
    direction: sort.slice(idx + 1) as SortDirection,
  };
}

// Null-aware numeric compare; nulls always sink to the bottom regardless of direction.
function compareNumbers(a: number | null, b: number | null, flip: 1 | -1): number {
  if (a === null && b === null) return 0;
  if (a === null) return 1;
  if (b === null) return -1;
  return (a - b) * flip;
}

export function filterAndSortPlayers(
  players: PlayerWithEligibility[],
  filterBy: FilterOption,
  sortBy: SortOption,
  selectedGame: string | null
): PlayerWithEligibility[] {
  let filtered = [...players];

  if (filterBy === 'available') {
    filtered = filtered.filter((p) => p.is_eligible);
  } else if (filterBy === 'locked') {
    filtered = filtered.filter((p) => !p.is_eligible);
  }

  if (selectedGame) {
    filtered = filtered.filter((player) => {
      const gameKey = player.is_home
        ? `${player.opponent}-${player.team}`
        : `${player.team}-${player.opponent}`;
      return gameKey === selectedGame;
    });
  }

  const { field, direction } = parseSort(sortBy);
  const flip: 1 | -1 = direction === 'asc' ? 1 : -1;

  filtered.sort((a, b) => {
    if (field === 'name') return a.name.localeCompare(b.name) * flip;
    if (field === 'matchup') return a.opponent.localeCompare(b.opponent) * flip;
    const column = STAT_COLUMN_BY_FIELD[field as StatSortField];
    return compareNumbers(column.accessor(a), column.accessor(b), flip);
  });

  return filtered;
}
