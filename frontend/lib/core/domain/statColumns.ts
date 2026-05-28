/**
 * Stat column metadata — portable across web and mobile.
 *
 * Only the fields needed by sorting/filtering live here. Render-time concerns
 * (label text, Tailwind classes, background gradients) live in lib/web and
 * are merged with this metadata at the call site.
 */

import type { PlayerWithEligibility, SortDirection, SortField } from './players';

export type StatGroup = 'opp' | 'fantasy' | 'playoffs';
export type StatSortField = Extract<
  SortField,
  'pace' | 'drtg' | 'season' | 'week' | 'l10' | 'l30' | 'playoffs' | 'lastround' | 'currentround'
>;

export interface StatColumnMeta {
  field: StatSortField;
  group: StatGroup;
  accessor: (p: PlayerWithEligibility) => number | null;
  defaultDirection: SortDirection;
}

export const STAT_COLUMN_META: StatColumnMeta[] = [
  {
    field: 'pace',
    group: 'opp',
    accessor: (p) => p.opp_pace ?? null,
    defaultDirection: 'desc',
  },
  {
    field: 'drtg',
    group: 'opp',
    accessor: (p) => p.opp_def_rating ?? null,
    defaultDirection: 'asc',
  },
  {
    field: 'season',
    group: 'fantasy',
    accessor: (p) => p.avg_fantasy ?? null,
    defaultDirection: 'desc',
  },
  {
    field: 'week',
    group: 'fantasy',
    // Backend uses 0 as sentinel for "no data"; normalize to null so sort and render agree.
    accessor: (p) => (p.avg_fantasy_week_ago > 0 ? p.avg_fantasy_week_ago : null),
    defaultDirection: 'desc',
  },
  {
    field: 'l10',
    group: 'fantasy',
    accessor: (p) => p.avg_fantasy_l10 ?? null,
    defaultDirection: 'desc',
  },
  {
    field: 'l30',
    group: 'fantasy',
    accessor: (p) => p.avg_fantasy_l30d ?? null,
    defaultDirection: 'desc',
  },
  {
    field: 'playoffs',
    group: 'playoffs',
    accessor: (p) => p.avg_fantasy_playoffs ?? null,
    defaultDirection: 'desc',
  },
  {
    field: 'lastround',
    group: 'playoffs',
    accessor: (p) => p.avg_fantasy_last_round ?? null,
    defaultDirection: 'desc',
  },
  {
    field: 'currentround',
    group: 'playoffs',
    accessor: (p) => p.avg_fantasy_current_round ?? null,
    defaultDirection: 'desc',
  },
];

export const STAT_COLUMN_META_BY_FIELD: Record<StatSortField, StatColumnMeta> =
  Object.fromEntries(STAT_COLUMN_META.map((c) => [c.field, c])) as Record<
    StatSortField,
    StatColumnMeta
  >;

export const formatStat = (v: number | null): string => (v === null ? '—' : v.toFixed(1));
