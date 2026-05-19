import type { ReactNode } from 'react';

import type { PlayerWithEligibility, SortDirection, SortField } from './players';

export type StatGroup = 'opp' | 'fantasy' | 'playoffs';
export type StatSortField = Extract<
  SortField,
  'pace' | 'drtg' | 'season' | 'week' | 'l10' | 'l30' | 'playoffs' | 'lastround' | 'currentround'
>;

export interface PlayoffContext {
  currentPlayoffRound: number | null;
  lastPlayoffRound: number | null;
}

export interface StatColumn {
  field: StatSortField;
  label: (ctx: PlayoffContext) => ReactNode;
  group: StatGroup;
  accessor: (p: PlayerWithEligibility) => number | null;
  defaultDirection: SortDirection;
  bgClass: string;
  borderClass?: string;
  /** Inline background range key — applies a gradient based on team stat distribution. */
  rangeKey?: 'pace' | 'defRating';
}

export const formatStat = (v: number | null): string => (v === null ? '—' : v.toFixed(1));

export const STAT_COLUMNS: StatColumn[] = [
  {
    field: 'pace',
    label: () => 'Pace',
    group: 'opp',
    accessor: (p) => p.opp_pace ?? null,
    defaultDirection: 'desc',
    bgClass: 'bg-red-500/3',
    rangeKey: 'pace',
  },
  {
    field: 'drtg',
    label: () => 'DRtg',
    group: 'opp',
    accessor: (p) => p.opp_def_rating ?? null,
    defaultDirection: 'asc',
    bgClass: 'bg-red-500/3',
    rangeKey: 'defRating',
  },
  {
    field: 'season',
    label: () => 'Season',
    group: 'fantasy',
    accessor: (p) => p.avg_fantasy ?? null,
    defaultDirection: 'desc',
    bgClass: 'bg-primary/3',
    borderClass: 'border-l-[3px] border-primary/50',
  },
  {
    field: 'week',
    label: () => '-14d',
    group: 'fantasy',
    // Backend uses 0 as sentinel for "no data"; normalize to null so sort and render agree.
    accessor: (p) => (p.avg_fantasy_week_ago > 0 ? p.avg_fantasy_week_ago : null),
    defaultDirection: 'desc',
    bgClass: 'bg-primary/3',
  },
  {
    field: 'l10',
    label: () => 'L10',
    group: 'fantasy',
    accessor: (p) => p.avg_fantasy_l10 ?? null,
    defaultDirection: 'desc',
    bgClass: 'bg-primary/3',
  },
  {
    field: 'l30',
    label: () => '30d',
    group: 'fantasy',
    accessor: (p) => p.avg_fantasy_l30d ?? null,
    defaultDirection: 'desc',
    bgClass: 'bg-primary/3',
  },
  {
    field: 'playoffs',
    label: () => 'All',
    group: 'playoffs',
    accessor: (p) => p.avg_fantasy_playoffs ?? null,
    defaultDirection: 'desc',
    bgClass: 'bg-amber-500/3',
    borderClass: 'border-l-[3px] border-amber-400/50',
  },
  {
    field: 'lastround',
    label: ({ lastPlayoffRound }) => (lastPlayoffRound ? `Rnd ${lastPlayoffRound}` : '—'),
    group: 'playoffs',
    accessor: (p) => p.avg_fantasy_last_round ?? null,
    defaultDirection: 'desc',
    bgClass: 'bg-amber-500/3',
  },
  {
    field: 'currentround',
    label: ({ currentPlayoffRound }) => (currentPlayoffRound ? `Rnd ${currentPlayoffRound}` : '—'),
    group: 'playoffs',
    accessor: (p) => p.avg_fantasy_current_round ?? null,
    defaultDirection: 'desc',
    bgClass: 'bg-amber-500/3',
  },
];

export const STAT_COLUMN_BY_FIELD: Record<StatSortField, StatColumn> = Object.fromEntries(
  STAT_COLUMNS.map((c) => [c.field, c])
) as Record<StatSortField, StatColumn>;
