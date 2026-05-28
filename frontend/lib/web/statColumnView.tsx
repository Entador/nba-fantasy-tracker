/**
 * Web-side stat column presentation: extends the portable metadata with
 * Tailwind classes, range-key gradient hints, and ReactNode header labels.
 */

import type { ReactNode } from 'react';

import {
  STAT_COLUMN_META,
  type StatColumnMeta,
  type StatSortField,
} from '@/lib/core/domain/statColumns';

export interface PlayoffContext {
  currentPlayoffRound: number | null;
  lastPlayoffRound: number | null;
}

export interface StatColumn extends StatColumnMeta {
  label: (ctx: PlayoffContext) => ReactNode;
  bgClass: string;
  borderClass?: string;
  /** Inline background range key — applies a gradient based on team stat distribution. */
  rangeKey?: 'pace' | 'defRating';
}

type StatColumnView = Omit<StatColumn, keyof StatColumnMeta>;

const VIEW_BY_FIELD: Record<StatSortField, StatColumnView> = {
  pace: {
    label: () => 'Pace',
    bgClass: 'bg-red-500/3',
    rangeKey: 'pace',
  },
  drtg: {
    label: () => 'DRtg',
    bgClass: 'bg-red-500/3',
    rangeKey: 'defRating',
  },
  season: {
    label: () => 'Season',
    bgClass: 'bg-primary/3',
    borderClass: 'border-l-[3px] border-primary/50',
  },
  week: {
    label: () => '-14d',
    bgClass: 'bg-primary/3',
  },
  l10: {
    label: () => 'L10',
    bgClass: 'bg-primary/3',
  },
  l30: {
    label: () => '30d',
    bgClass: 'bg-primary/3',
  },
  playoffs: {
    label: () => 'All',
    bgClass: 'bg-amber-500/3',
    borderClass: 'border-l-[3px] border-amber-400/50',
  },
  lastround: {
    label: ({ lastPlayoffRound }) => (lastPlayoffRound ? `Rnd ${lastPlayoffRound}` : '—'),
    bgClass: 'bg-amber-500/3',
  },
  currentround: {
    label: ({ currentPlayoffRound }) =>
      currentPlayoffRound ? `Rnd ${currentPlayoffRound}` : '—',
    bgClass: 'bg-amber-500/3',
  },
};

export const STAT_COLUMNS: StatColumn[] = STAT_COLUMN_META.map((meta) => ({
  ...meta,
  ...VIEW_BY_FIELD[meta.field],
}));

export { formatStat } from '@/lib/core/domain/statColumns';
