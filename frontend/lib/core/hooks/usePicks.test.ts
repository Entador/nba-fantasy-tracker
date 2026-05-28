import { describe, it, expect, beforeEach, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import React from 'react';
import { SWRConfig } from 'swr';

import { usePicks } from './usePicks';
import type { PicksResponse } from '@/lib/core/api';

vi.mock('@/lib/core/hooks/useAuth', () => ({
  useAuth: () => ({ isLoading: false }),
}));

vi.mock('@/lib/core/api', () => ({
  getPicks: vi.fn(),
  createPick: vi.fn(),
  deletePick: vi.fn(),
  createPicksBatch: vi.fn(),
}));

import { getPicks, createPick, deletePick } from '@/lib/core/api';

const empty: PicksResponse = { picks: [], locks: [] };

function wrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(
    SWRConfig,
    { value: { provider: () => new Map(), dedupingInterval: 0 } },
    children
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('usePicks', () => {
  it('reflects a newly created pick after the round-trip', async () => {
    vi.mocked(getPicks).mockResolvedValueOnce(empty).mockResolvedValueOnce({
      picks: [{ id: 1, player_id: 42, game_date: '2026-05-28', picked_at: '2026-05-28T18:00:00Z' }],
      locks: [],
    });
    vi.mocked(createPick).mockResolvedValueOnce({
      id: 1, player_id: 42, game_date: '2026-05-28', picked_at: '2026-05-28T18:00:00Z',
    });

    const { result } = renderHook(() => usePicks(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.picks).toEqual([]);

    await act(async () => {
      await result.current.setPick(42, '2026-05-28');
    });

    expect(createPick).toHaveBeenCalledWith(42, '2026-05-28');
    expect(result.current.picks).toEqual([
      { id: 1, playerId: 42, date: '2026-05-28', isSkipped: false },
    ]);
  });

  it('removes a pick after clearPick resolves', async () => {
    const seeded: PicksResponse = {
      picks: [{ id: 7, player_id: 99, game_date: '2026-05-28', picked_at: null }],
      locks: [],
    };
    vi.mocked(getPicks).mockResolvedValueOnce(seeded).mockResolvedValueOnce(empty);
    vi.mocked(deletePick).mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => usePicks(), { wrapper });
    await waitFor(() => expect(result.current.picks).toHaveLength(1));

    await act(async () => {
      await result.current.clearPick('2026-05-28');
    });

    expect(deletePick).toHaveBeenCalledWith(7);
    expect(result.current.picks).toEqual([]);
  });
});
