# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. Modify it if necessary and for relevant changes.

## Project Overview

NBA Fantasy Tracker is a web app to optimize daily player picks for Fantasy (NBA Fantasy), a French NBA fantasy game. Users pick one NBA player per night and earn points based on their performance. The 30-day rule prevents picking the same player twice within 30 days.

You are a senior dev that aims simplicity and maintainability in the code

**Fantasy Score Formula:**
```
POSITIVE: PTS + REB + AST + STL + BLK + FGM + 3PM + FTM
NEGATIVE: TOV + FG_missed + 3P_missed + FT_missed
FANTASY_SCORE = POSITIVE - NEGATIVE
```

## Tech Stack

- **Backend**: FastAPI (Python 3.12+), SQLAlchemy 2.0, PostgreSQL
- **Frontend**: Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4
- **Database**: PostgreSQL (Neon)
- **Hosting**: Vercel (both frontend and backend)
- **Package Managers**: Poetry (backend), pnpm (frontend)
- **Data Source**: `nba_api` Python package

## Development Commands

### Backend (from `/backend`)

```bash
# Install dependencies
poetry install

# Run development server
poetry run uvicorn app:app --reload
# API runs on http://localhost:8000
# API docs at http://localhost:8000/docs

# Create database tables (one-time setup)
poetry run python -c "from models.database import engine, Base; from models import Player, Game; Base.metadata.create_all(bind=engine)"

# Run Python scripts
poetry run python scripts/script_name.py
```

**Environment**: Requires `.env` file with `DATABASE_URL=postgresql://...`

### Frontend (from `/frontend`)

```bash
# Install dependencies
pnpm install

# Run development server
pnpm dev
# App runs on http://localhost:3000

# Build for production
pnpm build

# Run production build
pnpm start

# Lint
pnpm lint
```

**Environment**: Requires `.env.local` file with `NEXT_PUBLIC_API_URL=http://localhost:8000`

## Architecture

### Backend Structure

Organized **by feature/domain**, not by technical layer. Each domain owns its
router, service, schemas, etc. in one package. Cross-cutting logic lives in
`core/` (shared) and `ingestion/` (NBA data fetching, used by scripts).

```
backend/
├── app.py                  # FastAPI app, CORS config, router registration
├── models/
│   ├── database.py         # SQLAlchemy engine, SessionLocal, get_db()
│   └── __init__.py         # Team, Player, Game, FantasyScore, User, AnonIdentity,
│                           #   Owner, Pick, UserDevice, NotificationPref/Log, Entitlement
├── auth/                   # Auth domain (JWT access token + refresh sessions)
│   ├── router.py           # POST /auth/register, /token, /auth/refresh, /auth/logout, GET /users/me
│   ├── service.py          # user create/authenticate
│   ├── sessions.py         # refresh-session create/rotate/revoke ("remember me")
│   ├── schemas.py          # Pydantic request/response models
│   ├── security.py         # password hashing, JWT + refresh-token (SHA-256) primitives
│   ├── dependencies.py     # get_current_active_user
│   └── config.py           # SECRET_KEY, access/refresh expiry, cookie settings
├── picks/                  # Picks domain (DB-backed, guest + user)
│   ├── router.py           # GET/POST /api/picks, DELETE /api/picks/{id}
│   ├── service.py          # upsert, eligibility (30-day + playoff), anon→user migration
│   ├── schemas.py          # Pydantic request/response models
│   └── dependencies.py     # resolve_owner() from JWT user or anon_id cookie
├── players/                # Players domain
│   ├── router.py           # GET /api/players/all, GET /api/players/{id}/stats
│   └── service.py          # batch_calculate_averages(), get_playoff_round()
├── snapshot/               # Snapshot domain (read view over players/games)
│   └── router.py           # GET /api/snapshot  (imports players.service)
├── core/                   # Shared, cross-domain logic
│   ├── fantasy.py          # calculate_fantasy_score()
│   └── cache.py            # in-memory app_cache (schedule/teams/players)
├── ingestion/              # NBA data fetching (used by scripts, not request path)
│   ├── client.py           # NBAClient — nba_api wrapper
│   ├── injuries_nba.py     # Parse official NBA injury report PDFs (default source)
│   ├── injuries.py         # Fetch injury data from ESPN (fallback, INJURY_SOURCE=espn)
│   ├── email.py            # Resend email service
│   └── utils.py            # normalize_name(), shared helpers
├── scripts/
│   ├── daily_update.py     # Automated database updates (runs via GitHub Actions)
│   ├── populate_db.py      # Initial database population
│   └── *.py                # Other maintenance scripts
├── alembic/                # DB migrations (versions/ holds the migration chain)
├── tests/                  # pytest suite, mirrors backend/ (auth/, picks/, core/, services/)
└── ml/                     # Player-projection modeling (data/, training/, models/, notebooks/) — not on request path
```

**Adding a new domain** (e.g. `devices/`): create a package with `router.py` +
`service.py` (+ `schemas.py`), then register its router in `app.py`. Don't add
back a top-level `routers/` or `services/` layer.

**Key API Endpoints:**
- `GET /api/snapshot` - **Primary endpoint**: Returns entire season data (all players, games, teams) in one response for client-side filtering (30 KB)
- `GET /api/players/all` - All players (id, name, team)
- `GET /api/players/{player_id}/stats` - Recent game history for a player
- `GET /api/picks` - List the caller's picks (owner resolved from JWT user or `anon_id` cookie)
- `POST /api/picks` - Upsert tonight's pick (one per owner per date; enforces eligibility)
- `DELETE /api/picks/{id}` - Remove a pick
- `POST /auth/register`, `POST /token`, `GET /users/me` - Email/password auth (JWT bearer)
- `POST /auth/refresh` - Rotate the refresh session, mint a new short-lived access token (web auto-calls on 401)
- `POST /auth/logout` - Revoke the current refresh session and clear both cookies

### Frontend Structure

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout with metadata
│   ├── page.tsx            # Main page: dashboard with date navigation
│   ├── history/
│   │   └── page.tsx        # Pick history
│   └── players/[id]/
│       └── page.tsx        # Player detail page
├── components/
│   ├── PlayersView.tsx     # Client component: snapshot fetching, filtering, sorting
│   ├── PlayersTable.tsx    # Table display with clickable sortable headers
│   ├── PlayerFilters.tsx   # Filter controls (game, availability)
│   └── ...                 # Other components
└── lib/
    ├── api.ts              # API client functions (fetch with credentials: 'include')
    ├── hooks/
    │   ├── useSnapshot.ts  # SWR hook for the season snapshot
    │   └── usePicks.ts     # SWR hook for picks (server-backed, optimistic mutations)
    ├── snapshot.ts         # Client-side snapshot filtering utilities
    ├── picks.ts            # Pure pick logic: eligibility + forgotten-date detection
    ├── players.ts          # Sort/filter logic, SortOption type, parseSort
    └── statColumns.ts      # STAT_COLUMNS config (single source of truth for stat columns)
```

**Routing**: Uses Next.js App Router (file-based routing)

### Data Flow

The app uses a **snapshot-based architecture** optimized for instant navigation:

**Daily Update Cycle (via GitHub Actions cron):**
1. **NBA API → Daily Script**: `daily_update.py` fetches game data, scores, and injury info
2. **Daily Script → Database**: Updates game statuses, Fantasy scores, team stats, and injuries
3. **Fantasy Score Calculation**: Raw NBA stats → `fantasy.calculate_fantasy_score()` → stored in database

**Backend In-Memory Cache:**
- On startup, backend loads entire season's games, teams, and players into memory
- Cache includes: game schedules, team stats, player rosters (static/semi-static data)
- Fantasy score calculations still query DB (dynamic data)
- Significantly reduces database load for read operations

**Request Flow (Snapshot Architecture):**
1. **Frontend Initial Load**: Single `GET /api/snapshot` call fetches all season data (~30 KB JSON)
2. **Backend Response**: Combines cached data (games, teams, players) + DB queries (Fantasy averages)
3. **Client-Side Filtering**: Frontend filters snapshot by date in memory (instant, no API calls)
4. **Date Navigation**: URL changes (`?date=YYYY-MM-DD`) trigger client-side filter only
5. **Pick Management**: picks live in the DB (`/api/picks`); the `usePicks` SWR hook fetches
   them (guest via the `anon_id` cookie, or the signed-in user) and mutates optimistically.
   Eligibility is still computed client-side by the pure functions in `lib/picks.ts`.

**Key Principle**: Backend serves data from in-memory cache + database, not from NBA API directly (except for optional demo mode).

### Database Schema

Core NBA data:

**teams** — `id` (PK), `nba_team_id` (unique), `abbreviation`, `full_name`, record (`wins`/`losses`), tempo/defense (`pace`, `def_rating`), opponent stats (`opp_*`), `stats_updated_at`

**players** — `id` (PK), `nba_player_id` (unique), `name`, `team_id` (FK teams), `is_active`, injury fields (`injury_status`, `injury_return_date`, `injury_details`)

**games** — team-vs-team schedule rows: `id` (PK), `nba_game_id` (unique), `home_team_id`/`away_team_id` (FK teams), `game_date`, `status` (scheduled|live|final), `home_score`/`away_score`, `start_time_utc`

**fantasy_scores** — per-player-per-game results: `id` (PK), `player_id` (FK), `game_id` (FK), `fantasy_score`, `minutes` (0/NULL = DNP). Unique on `(player_id, game_id)`.

Picks & identity (added in migration 0002):

**users** — `id` (PK), `email` (unique, nullable), `hashed_password`, `is_active`, `is_verified`, `is_superuser`, `created_at`, `deleted_at` (soft-delete)

**anon_identities** — persistent guest identity: `id` (PK), `token` (UUID, stored in cookie), `last_seen`, `deleted_at`

**owners** — pick-ownership abstraction: `id` (PK), `user_id` (FK, unique, nullable) XOR `identity_id` (FK anon_identities, unique, nullable). CHECK enforces exactly one is set.

**picks** — `id` (PK), `owner_id` (FK owners), `player_id` (FK), `game_date`, `picked_at`. Unique on `(owner_id, game_date)` (one pick per night).

**refresh_sessions** (migration 0004) — revocable login sessions for "remember me": `id` (PK), `user_id` (FK), `token_hash` (SHA-256 of the refresh token; the raw token lives only in the client cookie), `persistent` (remember-me flag → persistent vs session cookie), `issued_at`, `expires_at`, `last_used_at`, `revoked_at` (NULL = active), `user_agent`. Rotated on every `/auth/refresh`: the presented row is revoked and a new one issued (sliding expiry). MVP rotation only — no token-reuse/family detection yet.

Also present for later months: `user_devices`, `notification_prefs`, `notification_log`, `entitlements`.

**Eligibility**: computed per-owner in `picks/service.py` — a player is ineligible if that owner already picked them within a 29-day backward window (in-season), or once during the playoffs (once playoff games are scheduled). Migration from guest to user reassigns the `owners` row (`identity_id` → `user_id`); pick rows are untouched.

## Daily Update Script

The `scripts/daily_update.py` script maintains the database with fresh NBA data. It runs daily via GitHub Actions cron job and can also be run manually.

**What it does:**
1. **Updates game statuses**: Changes games from "scheduled" → "final" based on NBA schedule
2. **Populates Fantasy scores**: Fetches box scores for completed games and calculates Fantasy scores
3. **Updates team stats**: Refreshes defensive ratings, pace, opponent stats for all teams
4. **Updates injuries**: Parses the latest official NBA injury report PDF from `official.nba.com` (statuses: Out / Doubtful / Questionable / Probable, plus reason). Players on teams flagged `NOTYETSUBMITTED` are skipped to preserve their existing status. Set `INJURY_SOURCE=espn` to use the ESPN fallback instead.

**Manual usage:**
```bash
# Run all phases
poetry run python scripts/daily_update.py

# Run specific phase only
poetry run python scripts/daily_update.py --games-only
poetry run python scripts/daily_update.py --scores-only
poetry run python scripts/daily_update.py --stats-only
poetry run python scripts/daily_update.py --injuries-only

# Preview changes without committing
poetry run python scripts/daily_update.py --dry-run
```

**Important**: The script uses `nba_api` and is subject to rate limits. It includes retry logic with exponential backoff for timeout errors.

## Important Patterns

### Backend Dependency Injection

All routers use FastAPI's dependency injection for database sessions:

```python
from models.database import get_db
from sqlalchemy.orm import Session

@router.get("/endpoint")
def endpoint(db: Session = Depends(get_db)):
    # db session is auto-managed
```

Some endpoints use `get_optional_db()` to work without a database (API-only mode).

### In-Memory Cache

The backend pre-loads static/semi-static data on startup (`core/cache.py`):
- **Cached**: Game schedules, teams, player rosters (reduces DB queries)
- **Not cached**: Fantasy scores and averages (queried from DB as they change frequently)
- Cache is refreshed by redeploying after daily updates

### NBA API Rate Limiting

The NBA API has rate limits and is only called by the daily update script and other maintenance scripts (not by the backend API during normal operation). The `NBAClient` in `ingestion/client.py` includes a 0.6s delay between requests. The daily update script has retry logic with exponential backoff for timeout errors. If you get errors when running scripts manually, wait a few minutes before retrying.

### Frontend Data Fetching

The app uses a **fetch-once, filter-client-side** pattern:
- Single `GET /api/snapshot` call on page load fetches entire season data
- Date navigation filters cached data in-browser (instant, no API calls)
- Picks come from `/api/picks` via the `usePicks` SWR hook; eligibility is computed client-side
- Skeleton loader displays during initial data fetch

Next.js App Router uses Server Components by default. Client-side fetching is done in components marked with `'use client'` directive.

### Players Table Stat Columns

Numeric columns are driven by `STAT_COLUMNS` in `lib/statColumns.ts` — the same `accessor` powers both sorting and rendering. To add a column, append one entry there and one literal to `SortField` in `lib/players.ts`.

### Fantasy Score Calculation

Always use `core.fantasy.calculate_fantasy_score(box_score)` for consistency. The function handles missing/None values gracefully with `.get()` and `or 0` fallbacks.

## Next.js & React Best Practices

**App Router (Next.js 16):**
- Server Components by default - only add `'use client'` when you need hooks, event handlers, or browser APIs
- Fetch data directly in Server Components with `cache: 'no-store'` for real-time data
- Keep client components small and low in the tree

**shadcn/ui:**
- Copy components into project: `npx shadcn@latest add button`
- Components go in `components/ui/`, customize them directly
- Built on Radix UI (already installed) + Tailwind CSS
- Use `lucide-react` for icons (tree-shakeable)

**Component Organization:**
- Composition over complex props
- One component = one responsibility
- Extract logic to custom hooks
- Define TypeScript interfaces for API responses in `types/`

**Tailwind v4:**
- Config in `app.css` using `@theme` directive (not `tailwind.config.js`)
- Use utility classes: `flex items-center gap-4`, `text-lg font-semibold`

## Design Decisions

**Why store only Fantasy score, not raw stats?**
- Simpler data model, user only cares about final score
- Trade-off: Cannot recalculate if formula changes
- Raw stats available via NBA API if needed later

**Why optional database in some endpoints?**
- Allows API to work in "demo mode" without database setup
- Useful for testing NBA API integration independently

**Why separate frontend/backend?**
- Real-world architecture pattern
- Python backend better suited for data/ML work
- Learning opportunity (FastAPI)

## Common Gotchas

1. **Database connection**: If `DATABASE_URL` is invalid, app will fail to start. Check `.env` file.
2. **No games on off-days**: the snapshot has no games for that date, so the dashboard renders an empty player list. Handle this case in the frontend filter.
3. **Next.js caching**: App Router aggressively caches. Use `cache: 'no-store'` in fetch calls for live data.
4. **SQLAlchemy 2.0**: Uses `Session.query()` pattern (legacy), not the newer `select()` style. Be consistent.
5. **Poetry shell**: Don't activate `poetry shell` - use `poetry run` prefix for commands to avoid path issues.

## Testing Strategy

Automated tests run in CI (`.github/workflows/test.yml`, path-filtered per layer):
- **Backend**: `pytest` in `backend/tests/` (mirrors the package layout). Covers `calculate_fantasy_score`,
  auth endpoints + owner isolation, picks eligibility/upsert, and guest→user migration. SQLite in-memory,
  external services mocked. Run with `poetry run pytest` (the user runs tests themselves).
- **Frontend**: `vitest` + `@testing-library/react`, tests next to source as `*.test.ts(x)`
  (e.g. `lib/players.test.ts`). Run with `pnpm test`.

Priority is business logic, auth boundaries, and (later) notification correctness — not component
rendering or styling. See the Testing strategy section in `plan.md` for the full rationale.

Still manual: FastAPI `/docs` explorer, browser testing at `http://localhost:3000`, direct SQL via Neon/`psql`.
