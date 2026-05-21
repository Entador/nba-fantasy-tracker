# ADR 001 — Auth, picks sync, and notification architecture

**Date:** 2026-05-21
**Status:** Accepted

---

## Context

The app stored picks in `localStorage`. This meant picks were lost on device switch, and push notifications had no stable identity to target. Mobile apps (planned for Month 4) cannot share state with the web app.

Goals:
- Picks persist and sync across all of a user's devices once logged in.
- Push notifications go to all registered devices of a user — no per-device toggle.
- Anonymous users can use the app fully without signing up; picks are preserved locally.
- The guest experience is unchanged after auth lands.

---

## Decisions

### 1. DB-only picks — no localStorage

All picks are stored in the database from day one, even for anonymous users. A server-generated UUID (`AnonIdentity.token`) is stored in a cookie; it acts as the anonymous user's identity. There is no `LocalPicksStore` / `RemotePicksStore` split — one code path, always talks to the backend.

**Why:** dual implementations cause Next.js hydration mismatches (server sees no picks, client hydrates with localStorage picks → flash). DB-only eliminates this class of bug entirely.

### 2. Owner abstraction for pick ownership

A single `owners` table holds one row per identity — either a `user_id` (authenticated) or an `identity_id` (anonymous). All picks reference `owner_id`.

**Why:** a single non-nullable FK on `picks` is cleaner than two nullable FKs with an OR condition on every query. The unique constraint `UNIQUE(owner_id, game_date)` is simpler than two partial unique indexes. Guest → user migration is one atomic `UPDATE owners SET user_id = ?, identity_id = NULL` — all picks follow without touching a single pick row.

`owner.user_id` is `UNIQUE`: intentional. A user has exactly one canonical pick history regardless of how many devices they use. Multi-device push is handled by `UserDevice`, not by multiple Owner rows.

### 3. AnonIdentity — persistent, server-generated

`AnonIdentity` is not a "session" (which implies expiry) — it is a persistent anonymous identity. The token is generated server-side (not client-side) to prevent UUID collisions or spoofing. The client stores the token in a cookie.

Anonymous identities do not receive push notifications. To receive alerts, a user must sign up.

### 4. Multi-device push via UserDevice

One user → N `UserDevice` rows, one per registered push token. Notifications are sent to all active (non-revoked) devices. `revoked_at` is set when the user logs out of a device or disables push.

**Why separate from Owner:** Owner tracks pick history (one per user). UserDevice tracks notification delivery (many per user). Mixing them would require multiple Owner rows per user, which complicates pick queries.

### 5. Auth: fastapi-users + magic link + Google OAuth

`fastapi-users` manages users in the same PostgreSQL database as picks. No separate auth service.

Providers: email magic link (Resend) + Google OAuth. Magic links eliminate password management.

Token storage: HTTP-only cookie on web (XSS-safe), Expo `SecureStore` on mobile.

### 6. Notifications are user-only

`notification_prefs` and `notification_log` reference `user_id` directly — no Owner join, no anonymous involvement. If a user has no preference row, defaults apply (all alerts on).

### 7. Entitlements are user-only

`entitlements` has a `user_id` FK only. Anonymous identities cannot purchase. The table is a post-launch placeholder; no feature gates use it yet.

---

## Data model

```
anon_identities
  id (PK), token (unique, server-generated UUID), created_at, last_seen, deleted_at

users
  id (PK), email (unique), hashed_password, is_active, is_verified, is_superuser,
  created_at, deleted_at

owners
  id (PK),
  user_id (FK users, unique, nullable),
  identity_id (FK anon_identities, unique, nullable),
  created_at
  CHECK: exactly one of user_id / identity_id is non-null

picks
  id (PK), owner_id (FK owners), player_id (FK players), game_date, picked_at
  UNIQUE(owner_id, game_date)
  INDEX(game_date)   -- leaderboard / daily summary queries

user_devices
  id (PK), user_id (FK users), push_token (unique), platform, registered_at,
  last_seen, revoked_at

notification_prefs
  id (PK), user_id (FK users, unique), injury_alerts, deadline_alerts

notification_log
  id (PK), user_id (FK users), type (enum), payload (json), sent_at, status (enum)
  INDEX(user_id, sent_at)   -- dedup query: "did we send this type to this user today?"

entitlements
  id (PK), user_id (FK users), product_id, source (enum), external_id,
  granted_at, expires_at, status (enum)
```

---

## Migration path: guest → user

1. User completes magic link or OAuth flow.
2. Backend creates a `User` row.
3. `UPDATE owners SET user_id = new_user_id, identity_id = NULL WHERE id = owner_id` (atomic).
4. All existing picks now belong to the authenticated user — no pick rows touched.
5. `AnonIdentity` row is soft-deleted (`deleted_at = now()`).

---

## Growth notes

- **NotificationLog partitioning:** once rows exceed ~1M, partition by `sent_at` month using PostgreSQL declarative partitioning. No schema change needed on the model.
- **Leaderboards / analytics:** picks will need an `is_public` flag on `Owner` or `Pick`. The current shape supports adding it without changing foreign keys. The `ix_pick_game_date` index already supports daily aggregation queries.
- **Apple Sign-In:** add in Month 4 as a new OAuth provider. No schema changes required.

---

## Consequences

- Guest experience is unchanged — no forced signup.
- Hydration issues from a localStorage/DB split are eliminated.
- Notification identity works for all registered users via a clean `user_id` reference.
- Multi-device sync and push work without per-device preference complexity.
- Monetization can launch post-season without migrations.
