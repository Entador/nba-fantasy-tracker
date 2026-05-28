import useSWR from 'swr';

import { getSnapshot, type SnapshotData } from '@/lib/core/api';

/**
 * SWR hook for fetching and caching snapshot data.
 * Cache is shared across all pages — eliminates re-fetching on navigation.
 * Data updates once daily via GitHub Actions, so we cache aggressively;
 * the user can refresh the page for fresh data.
 */
export function useSnapshot() {
  return useSWR<SnapshotData>('/api/snapshot', getSnapshot, {
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
    dedupingInterval: 60_000,
  });
}
