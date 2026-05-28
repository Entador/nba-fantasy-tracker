/**
 * Import utility for TTFL historical picks.
 * Parses TSV data from TTFL website and matches player names to IDs.
 */

import { getAllPlayers } from '../api/players';
import type { PlayerBasic } from '../api/types';
import type { Pick } from './picks';

/** Remove diacritics, lowercase, collapse whitespace. */
function normalizeName(name: string): string {
  return name
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()
    .replace(/\s+/g, ' ');
}

/**
 * Parse TSV data from TTFL website.
 * Expected format (tab-separated):
 * Date\tJoueur\tPts\tReb\tAst\tStl\tBlk\tFtm\tFgm\tFg3m\tMalus\tScore\t[Bonus x2]
 */
function parseTTFLData(tsvData: string): { date: string; playerName: string }[] {
  const lines = tsvData.trim().split('\n');
  const results: { date: string; playerName: string }[] = [];

  for (const line of lines) {
    const columns = line.split('\t');
    if (columns.length < 2) continue;
    if (columns[0] === 'Date' || columns[0] === 'Joueur') continue;

    const date = columns[0]?.trim();
    const playerName = columns[1]?.trim();

    if (!date || !playerName || !/^\d{4}-\d{2}-\d{2}$/.test(date)) continue;
    results.push({ date, playerName });
  }

  return results;
}

function matchPlayerNames(
  parsedData: { date: string; playerName: string }[],
  allPlayers: PlayerBasic[]
): { matches: Pick[]; unmatched: string[] } {
  const playersByNormalizedName = new Map<string, PlayerBasic>();
  allPlayers.forEach((player) => {
    playersByNormalizedName.set(normalizeName(player.name), player);
  });

  const matches: Pick[] = [];
  const unmatched: string[] = [];

  for (const { date, playerName } of parsedData) {
    const player = playersByNormalizedName.get(normalizeName(playerName));
    if (player) {
      matches.push({ playerId: player.player_id, date });
    } else {
      unmatched.push(playerName);
    }
  }

  return { matches, unmatched };
}

export interface ImportResult {
  success: boolean;
  imported: number;
  skipped: number;
  unmatched: string[];
  error?: string;
}

/** Validate, parse, and match TTFL TSV data to player IDs. */
export async function parseAndMatchTTFLData(tsvData: string): Promise<{
  picks: Pick[];
  unmatched: string[];
  error?: string;
}> {
  try {
    const parsedData = parseTTFLData(tsvData);
    if (parsedData.length === 0) {
      return {
        picks: [],
        unmatched: [],
        error: 'No valid data found. Please paste tab-separated data from the TTFL website.',
      };
    }

    const allPlayers = await getAllPlayers();
    const { matches, unmatched } = matchPlayerNames(parsedData, allPlayers);

    if (matches.length === 0) {
      return {
        picks: [],
        unmatched,
        error: 'No players could be matched. Please check the data format.',
      };
    }

    return { picks: matches, unmatched };
  } catch (error) {
    return {
      picks: [],
      unmatched: [],
      error: error instanceof Error ? error.message : 'Unknown error occurred',
    };
  }
}
