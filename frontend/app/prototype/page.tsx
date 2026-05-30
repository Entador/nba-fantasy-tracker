"use client";

/**
 * PROTOTYPE — "Courtside" mobile dashboard concept (compact ranked list).
 *
 * Isolated route (/prototype) with mock data. Nothing here touches the live app.
 *
 * Model:
 *  - Ranked list is the default high-signal view: best AVAILABLE picks on top,
 *    locked players demoted below a divider. One score column.
 *  - The timeframe toggle (L10 / Season / 30d) re-sorts the list by that window.
 *  - Discovery for the long tail / niche players: a sticky search field + chips
 *    to filter by availability or by game. Ranking serves the masses; search and
 *    filters reach everyone else.
 *
 * Theme: inherits the app's design tokens, so it follows the light theme.
 * Anton is kept only for the date + score numerals (the signature of this look).
 *
 * Safe to delete this whole folder.
 */

import {
  Ban,
  Check,
  ChevronLeft,
  ChevronRight,
  Lock,
  Plus,
  Search,
  TriangleAlert,
  X,
} from "lucide-react";
import { Anton } from "next/font/google";
import { useMemo, useState } from "react";

const anton = Anton({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-anton",
});

type Timeframe = "l10" | "szn" | "l30";

interface MockPlayer {
  id: number;
  name: string;
  team: string;
  color: string; // team accent
  opp: string;
  home: boolean;
  b2b: boolean;
  injury: "OUT" | "GTD" | null;
  game: string; // "AWAY @ HOME" — shared by both teams in the matchup
  szn: number;
  l10: number;
  l30: number;
  daysUntil: number | null; // null = eligible
}

const PLAYERS: MockPlayer[] = [
  // POR @ DEN
  { id: 1, name: "Nikola Jokić", team: "DEN", color: "#FEC524", opp: "POR", home: true, b2b: false, injury: null, game: "POR @ DEN", szn: 54.0, l10: 61.2, l30: 59.0, daysUntil: null },
  { id: 2, name: "Jamal Murray", team: "DEN", color: "#FEC524", opp: "POR", home: true, b2b: false, injury: null, game: "POR @ DEN", szn: 38.5, l10: 41.0, l30: 39.2, daysUntil: null },
  { id: 3, name: "Anfernee Simons", team: "POR", color: "#C8102E", opp: "DEN", home: false, b2b: false, injury: null, game: "POR @ DEN", szn: 31.0, l10: 33.2, l30: 32.0, daysUntil: null },
  // DAL @ MEM
  { id: 4, name: "Luka Dončić", team: "DAL", color: "#2563eb", opp: "MEM", home: false, b2b: true, injury: "GTD", game: "DAL @ MEM", szn: 55.1, l10: 57.8, l30: 56.3, daysUntil: null },
  { id: 5, name: "Jaren Jackson Jr.", team: "MEM", color: "#1d4ed8", opp: "DAL", home: true, b2b: false, injury: null, game: "DAL @ MEM", szn: 36.0, l10: 38.4, l30: 37.0, daysUntil: null },
  // SAS @ OKC
  { id: 6, name: "Shai Gilgeous-Alexander", team: "OKC", color: "#0ea5e9", opp: "SAS", home: true, b2b: false, injury: null, game: "SAS @ OKC", szn: 52.7, l10: 54.0, l30: 53.1, daysUntil: null },
  { id: 7, name: "Cason Wallace", team: "OKC", color: "#0ea5e9", opp: "SAS", home: true, b2b: false, injury: null, game: "SAS @ OKC", szn: 18.0, l10: 22.4, l30: 20.0, daysUntil: null },
  { id: 8, name: "Devin Vassell", team: "SAS", color: "#374151", opp: "OKC", home: false, b2b: false, injury: null, game: "SAS @ OKC", szn: 26.0, l10: 28.1, l30: 27.0, daysUntil: null },
  // CHI @ MIL
  { id: 9, name: "Giannis Antetokounmpo", team: "MIL", color: "#16a34a", opp: "CHI", home: true, b2b: false, injury: null, game: "CHI @ MIL", szn: 54.9, l10: 49.3, l30: 52.0, daysUntil: 12 },
  // LAL @ PHX
  { id: 10, name: "Kevin Durant", team: "PHX", color: "#ea580c", opp: "LAL", home: true, b2b: false, injury: "OUT", game: "LAL @ PHX", szn: 45.5, l10: 0, l30: 44.0, daysUntil: null },
  { id: 11, name: "Devin Booker", team: "PHX", color: "#ea580c", opp: "LAL", home: true, b2b: false, injury: null, game: "LAL @ PHX", szn: 41.3, l10: 44.7, l30: 42.5, daysUntil: null },
  { id: 12, name: "LeBron James", team: "LAL", color: "#9333ea", opp: "PHX", home: false, b2b: false, injury: null, game: "LAL @ PHX", szn: 47.2, l10: 50.6, l30: 48.8, daysUntil: null },
  { id: 13, name: "Rui Hachimura", team: "LAL", color: "#9333ea", opp: "PHX", home: false, b2b: false, injury: "GTD", game: "LAL @ PHX", szn: 24.0, l10: 26.1, l30: 25.0, daysUntil: null },
  { id: 14, name: "Grayson Allen", team: "PHX", color: "#ea580c", opp: "LAL", home: true, b2b: false, injury: null, game: "LAL @ PHX", szn: 19.0, l10: 23.0, l30: 21.0, daysUntil: null },
  // UTA @ MIN
  { id: 15, name: "Anthony Edwards", team: "MIN", color: "#1d4ed8", opp: "UTA", home: true, b2b: false, injury: null, game: "UTA @ MIN", szn: 44.0, l10: 46.9, l30: 45.2, daysUntil: null },
  { id: 16, name: "Walker Kessler", team: "UTA", color: "#0b4ea2", opp: "MIN", home: false, b2b: false, injury: null, game: "UTA @ MIN", szn: 28.0, l10: 30.5, l30: 29.0, daysUntil: null },
  // BOS @ MIA
  { id: 17, name: "Jayson Tatum", team: "BOS", color: "#047857", opp: "MIA", home: false, b2b: true, injury: null, game: "BOS @ MIA", szn: 46.8, l10: 43.1, l30: 45.0, daysUntil: 4 },
  { id: 18, name: "Jrue Holiday", team: "BOS", color: "#047857", opp: "MIA", home: false, b2b: true, injury: null, game: "BOS @ MIA", szn: 30.0, l10: 32.2, l30: 31.0, daysUntil: null },
  // SAC @ HOU
  { id: 19, name: "Domantas Sabonis", team: "SAC", color: "#7c3aed", opp: "HOU", home: false, b2b: false, injury: null, game: "SAC @ HOU", szn: 43.9, l10: 42.0, l30: 43.1, daysUntil: null },
  { id: 20, name: "Alperen Şengün", team: "HOU", color: "#dc2626", opp: "SAC", home: true, b2b: false, injury: null, game: "SAC @ HOU", szn: 39.0, l10: 40.8, l30: 40.0, daysUntil: null },
];

const TIMEFRAMES: { key: Timeframe; label: string }[] = [
  { key: "l10", label: "L10" },
  { key: "szn", label: "Season" },
  { key: "l30", label: "30 Days" },
];

type Filter = "all" | "available" | string; // string = a game label

export default function PrototypePage() {
  const [pickedId, setPickedId] = useState<number | null>(null);
  const [tf, setTf] = useState<Timeframe>("l10");
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");

  const games = useMemo(
    () => Array.from(new Set(PLAYERS.map((p) => p.game))),
    []
  );
  const activeLabel = TIMEFRAMES.find((t) => t.key === tf)!.label;

  const { available, locked, total } = useMemo(() => {
    const q = query.trim().toLowerCase();
    const base = PLAYERS.filter((p) => {
      if (filter === "available" && p.daysUntil !== null) return false;
      if (filter !== "all" && filter !== "available" && p.game !== filter)
        return false;
      if (q && !p.name.toLowerCase().includes(q)) return false;
      return true;
    });
    const byStat = (a: MockPlayer, b: MockPlayer) => b[tf] - a[tf];
    return {
      available: base.filter((p) => p.daysUntil === null).sort(byStat),
      locked: base.filter((p) => p.daysUntil !== null).sort(byStat),
      total: base.length,
    };
  }, [filter, query, tf]);

  return (
    <div className={`${anton.variable} cs-root`}>
      <style>{CSS}</style>
      <div className="cs-glow" aria-hidden />

      <div className="cs-wrap">
        {/* Header */}
        <header className="cs-datebar">
          <button className="cs-navbtn" aria-label="Previous day">
            <ChevronLeft size={18} />
          </button>
          <div className="cs-datestack">
            <span className="cs-overline">Pick Night</span>
            <span className="cs-date">TONIGHT</span>
            <span className="cs-datesub">Thu · May 29 · Locks 1:00 AM</span>
          </div>
          <button className="cs-navbtn" aria-label="Next day">
            <ChevronRight size={18} />
          </button>
        </header>

        {/* Timeframe toggle — drives + re-sorts the score column */}
        <div className="cs-seg" role="tablist" aria-label="Stat window">
          {TIMEFRAMES.map((t) => (
            <button
              key={t.key}
              role="tab"
              aria-selected={tf === t.key}
              className={`cs-segbtn ${tf === t.key ? "is-active" : ""}`}
              onClick={() => setTf(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Discovery — sticky search + filter chips */}
        <div className="cs-controls">
          <div className="cs-search">
            <Search size={16} className="cs-searchicon" />
            <input
              type="text"
              placeholder="Search players…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Search players"
            />
            {query && (
              <button
                className="cs-clear"
                onClick={() => setQuery("")}
                aria-label="Clear search"
              >
                <X size={15} />
              </button>
            )}
          </div>

          <div className="cs-chips">
            <Chip on={filter === "all"} onClick={() => setFilter("all")}>
              All
            </Chip>
            <Chip
              on={filter === "available"}
              onClick={() => setFilter("available")}
            >
              Available
            </Chip>
            {games.map((g) => (
              <Chip key={g} on={filter === g} onClick={() => setFilter(g)}>
                {g}
              </Chip>
            ))}
          </div>
        </div>

        {/* Column legend */}
        <div className="cs-listhead">
          <span>{available.length} available</span>
          <span className="cs-lhval">{activeLabel} TTFL</span>
        </div>

        {total === 0 ? (
          <p className="cs-empty">No players match.</p>
        ) : (
          <>
            <ul className="cs-list">
              {available.map((p, i) => (
                <Row
                  key={p.id}
                  p={p}
                  rank={i + 1}
                  tf={tf}
                  idx={i}
                  picked={pickedId === p.id}
                  onPick={() =>
                    setPickedId(pickedId === p.id ? null : p.id)
                  }
                />
              ))}
            </ul>

            {locked.length > 0 && (
              <>
                <div className="cs-divider">
                  <span>Locked · 30-day rule</span>
                </div>
                <ul className="cs-list">
                  {locked.map((p, i) => (
                    <Row key={p.id} p={p} rank={i + 1} tf={tf} idx={0} locked />
                  ))}
                </ul>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function Chip({
  on,
  onClick,
  children,
}: {
  on: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button className={`cs-chip ${on ? "is-active" : ""}`} onClick={onClick}>
      {children}
    </button>
  );
}

interface RowProps {
  p: MockPlayer;
  rank: number;
  tf: Timeframe;
  idx: number;
  picked?: boolean;
  locked?: boolean;
  onPick?: () => void;
}

function Row({ p, rank, tf, idx, picked = false, locked = false, onPick }: RowProps) {
  const v = p[tf];
  const style = {
    "--team": p.color,
    animationDelay: `${idx * 45}ms`,
  } as unknown as React.CSSProperties;

  const injuryClass =
    p.injury === "OUT" ? "is-out" : p.injury === "GTD" ? "is-gtd" : "";

  return (
    <li
      className={`cs-row ${injuryClass} ${picked ? "is-picked" : ""} ${locked ? "is-locked" : ""}`}
      style={style}
    >
      <span className="cs-bar" aria-hidden />
      <span className="cs-rank">{String(rank).padStart(2, "0")}</span>

      <div className="cs-id">
        <span className="cs-nameline">
          <span className="cs-name">{p.name}</span>
          {p.injury && (
            <span className={`cs-health ${p.injury === "OUT" ? "out" : "gtd"}`}>
              {p.injury === "OUT" ? (
                <Ban size={11} strokeWidth={2.5} />
              ) : (
                <TriangleAlert size={11} strokeWidth={2.5} />
              )}
              {p.injury}
            </span>
          )}
        </span>
        <span className="cs-meta">
          <span className="cs-team" style={{ color: p.color }}>
            {p.team}
          </span>
          {p.home ? "vs" : "@"} {p.opp}
          {p.b2b && <span className="cs-tag">B2B</span>}
        </span>
      </div>

      <span className="cs-fig">{v ? v.toFixed(1) : "—"}</span>

      {locked ? (
        <span className="cs-lock">
          <Lock size={12} />
          {p.daysUntil}d
        </span>
      ) : (
        <button
          className={`cs-pick ${picked ? "is-on" : ""}`}
          onClick={onPick}
          aria-label={picked ? "Remove pick" : "Pick player"}
        >
          {picked ? (
            <Check size={18} strokeWidth={3} />
          ) : (
            <Plus size={18} strokeWidth={2.5} />
          )}
        </button>
      )}
    </li>
  );
}

const CSS = `
.cs-root {
  /* Local aliases mapped onto the app's design tokens */
  --ink: var(--foreground);
  --sub: var(--muted-foreground);
  --line: var(--border);
  --paper: var(--card);
  --brand: var(--primary);      /* blue — primary action */
  --hot: var(--accent);         /* orange — highlights */
  --danger: var(--destructive); /* red — remove */

  position: relative;
  min-height: 100vh;
  /* Break out of the root layout's padded container for a full-bleed concept */
  width: 100vw;
  margin-left: calc(50% - 50vw);
  margin-top: -12px;
  background: var(--muted);
  color: var(--ink);
  font-family: var(--font-sans), system-ui, sans-serif;
  overflow-x: hidden;
}
.cs-glow {
  position: fixed;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(
    70% 30% at 85% -10%,
    color-mix(in srgb, var(--hot) 12%, transparent),
    transparent 70%
  );
}
.cs-wrap {
  position: relative;
  max-width: 460px;
  margin: 0 auto;
  padding: 18px 16px 56px;
}

/* Header */
.cs-datebar { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.cs-navbtn {
  display: grid;
  place-items: center;
  height: 38px;
  width: 38px;
  border-radius: var(--radius);
  background: var(--paper);
  border: 1px solid var(--line);
  color: var(--ink);
  cursor: pointer;
  box-shadow: var(--shadow-xs);
  transition: background 0.15s, transform 0.1s;
}
.cs-navbtn:active { transform: scale(0.92); }
.cs-navbtn:hover { background: var(--muted); }
.cs-datestack { display: flex; flex-direction: column; align-items: center; line-height: 1; }
.cs-overline {
  font-size: 10px;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: var(--hot);
  font-weight: 700;
  margin-bottom: 3px;
}
.cs-date {
  font-family: var(--font-anton), sans-serif;
  font-size: 30px;
  letter-spacing: 0.01em;
  text-transform: uppercase;
}
.cs-datesub { font-size: 11px; color: var(--sub); margin-top: 4px; letter-spacing: 0.01em; }

.cs-seg {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 3px;
  margin-top: 14px;
  padding: 3px;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: calc(var(--radius) + 2px);
  box-shadow: var(--shadow-xs);
}
.cs-segbtn {
  border: 0;
  background: transparent;
  color: var(--sub);
  font-family: inherit;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 7px 0;
  border-radius: calc(var(--radius) - 2px);
  cursor: pointer;
  transition: color 0.18s, background 0.18s;
}
.cs-segbtn.is-active { color: var(--accent-foreground); background: var(--hot); }

/* Discovery controls — sticky under the app nav (h-14 = 56px on mobile) */
.cs-controls {
  position: sticky;
  top: 56px;
  z-index: 20;
  margin-top: 14px;
  padding: 10px 0;
  background: var(--muted);
  border-bottom: 1px solid var(--line);
}
.cs-search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  height: 40px;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow-xs);
  transition: border-color 0.15s, box-shadow 0.15s;
}
.cs-search:focus-within {
  border-color: var(--ring);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--ring) 22%, transparent);
}
.cs-searchicon { color: var(--sub); flex-shrink: 0; }
.cs-search input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--ink);
  font-family: inherit;
  font-size: 14px;
}
.cs-search input::placeholder { color: var(--sub); }
.cs-clear {
  display: grid;
  place-items: center;
  height: 22px;
  width: 22px;
  border: 0;
  border-radius: 999px;
  background: var(--muted);
  color: var(--sub);
  cursor: pointer;
  flex-shrink: 0;
}
.cs-clear:hover { color: var(--ink); }

.cs-chips {
  display: flex;
  gap: 6px;
  margin-top: 8px;
  overflow-x: auto;
  scrollbar-width: none;
  -webkit-overflow-scrolling: touch;
}
.cs-chips::-webkit-scrollbar { display: none; }
.cs-chip {
  flex-shrink: 0;
  border: 1px solid var(--line);
  background: var(--paper);
  color: var(--sub);
  font-family: inherit;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.03em;
  white-space: nowrap;
  padding: 6px 11px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.15s;
}
.cs-chip.is-active {
  background: var(--ink);
  color: var(--background);
  border-color: var(--ink);
}

/* Column legend */
.cs-listhead {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin: 14px 4px 8px;
  font-size: 10.5px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--sub);
  font-weight: 700;
}
.cs-lhval { color: var(--hot); }

.cs-empty {
  text-align: center;
  color: var(--sub);
  font-size: 13px;
  padding: 32px 0;
}

/* Rows */
.cs-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.cs-row {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  gap: 11px;
  min-height: 54px;
  padding: 8px 12px 8px 15px;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: calc(var(--radius) + 2px);
  box-shadow: var(--shadow-xs);
  opacity: 0;
  transform: translateY(10px);
  animation: cs-in 0.45s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}
@keyframes cs-in { to { opacity: 1; transform: none; } }
.cs-row.is-locked { opacity: 0.55; animation: none; box-shadow: none; background: transparent; }
.cs-row.is-picked {
  border-color: var(--brand);
  box-shadow: 0 0 0 1px var(--brand), var(--shadow-md);
}
.cs-bar {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 4px;
  background: var(--team);
}
.cs-rank {
  font-family: var(--font-anton), sans-serif;
  font-size: 16px;
  color: transparent;
  -webkit-text-stroke: 1px color-mix(in srgb, var(--ink) 32%, transparent);
  letter-spacing: 0.02em;
  min-width: 22px;
  text-align: center;
}
.cs-id { display: flex; flex-direction: column; gap: 3px; min-width: 0; flex: 1; }
.cs-nameline { display: flex; align-items: center; gap: 7px; min-width: 0; }
.cs-name {
  font-family: var(--font-anton), sans-serif;
  font-size: 15px;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  line-height: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cs-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--sub);
  white-space: nowrap;
}
.cs-team { font-weight: 800; letter-spacing: 0.03em; }
.cs-tag {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 1px 5px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  color: var(--sub);
}

/* Health status — loud: filled pill + icon, sits next to the name */
.cs-health {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.06em;
  padding: 2px 8px 2px 6px;
  border-radius: 999px;
  line-height: 1.4;
}
.cs-health.out {
  background: var(--danger);
  color: var(--destructive-foreground);
  animation: cs-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
.cs-health.gtd { background: #f59e0b; color: #422006; }
@keyframes cs-pulse {
  0%, 100% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--danger) 55%, transparent); }
  50% { box-shadow: 0 0 0 4px color-mix(in srgb, var(--danger) 0%, transparent); }
}

/* OUT rows read as "do not pick": red bar, faint tint, dimmed score */
.cs-row.is-out {
  background: color-mix(in srgb, var(--danger) 6%, var(--paper));
  border-color: color-mix(in srgb, var(--danger) 30%, var(--line));
}
.cs-row.is-out .cs-bar { background: var(--danger); }
.cs-row.is-out .cs-fig { color: var(--sub); }
.cs-row.is-gtd .cs-bar { background: #f59e0b; }

.cs-fig {
  font-family: var(--font-anton), sans-serif;
  font-size: 27px;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
  min-width: 56px;
  text-align: right;
}

.cs-pick {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  height: 38px;
  width: 38px;
  border: 0;
  border-radius: var(--radius);
  color: var(--primary-foreground);
  background: var(--brand);
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: transform 0.1s, filter 0.15s;
}
.cs-pick:hover { filter: brightness(1.08); }
.cs-pick:active { transform: scale(0.9); }
.cs-pick.is-on { background: var(--danger); color: var(--destructive-foreground); }

.cs-lock {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
  color: var(--sub);
  background: var(--paper);
  border: 1px dashed var(--line);
  border-radius: var(--radius);
  padding: 9px 11px;
  white-space: nowrap;
}

.cs-divider {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 18px 4px 8px;
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--sub);
}
.cs-divider span { white-space: nowrap; }
.cs-divider::after { content: ""; flex: 1; height: 1px; background: var(--line); }
`;
