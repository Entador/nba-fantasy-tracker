"""Pick ownership and CRUD.

Every read/write is scoped to a single Owner — that scoping IS the authorization
boundary (one owner can never see or touch another's picks).
"""

from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from models import AnonIdentity, Owner, Pick, Player, User
from picks.schemas import PickRead, PlayerLock
from players.service import get_playoff_start_date

# Regular season: the same player cannot be picked twice within 30 days.
# Playoffs: each player may be picked only once for the whole playoff run.
ELIGIBILITY_WINDOW_DAYS = 30


def get_or_create_owner_for_user(db: Session, user: User) -> Owner:
    if user.owner:
        return user.owner
    owner = Owner(user_id=user.id)
    db.add(owner)
    db.commit()
    db.refresh(owner)
    return owner


def get_or_create_owner_for_anon(db: Session, token: str | None) -> tuple[Owner, str]:
    """Resolve the Owner behind an anon cookie token, creating one if needed.

    Returns (owner, token) so the caller can (re)set the cookie. A missing or
    unknown token transparently mints a fresh identity rather than erroring.
    """
    if token:
        identity = (
            db.query(AnonIdentity)
            .filter(AnonIdentity.token == token, AnonIdentity.deleted_at.is_(None))
            .first()
        )
        if identity:
            return get_or_create_owner_for_anon_identity(db, identity), identity.token

    identity = AnonIdentity()
    db.add(identity)
    db.flush()  # assign id + default token before creating the Owner
    owner = Owner(identity_id=identity.id)
    db.add(owner)
    db.commit()
    db.refresh(owner)
    return owner, identity.token


def get_or_create_owner_for_anon_identity(db: Session, identity: AnonIdentity) -> Owner:
    if identity.owner:
        return identity.owner
    owner = Owner(identity_id=identity.id)
    db.add(owner)
    db.commit()
    db.refresh(owner)
    return owner


def list_picks(db: Session, owner: Owner) -> list[Pick]:
    rows = (
        db.query(Pick, Player.nba_player_id)
        .outerjoin(Player, Pick.player_id == Player.id)  # outer: skips have no player
        .filter(Pick.owner_id == owner.id)
        .order_by(Pick.game_date.desc())
        .all()
    )
    return [_to_read(pick, nba_player_id) for pick, nba_player_id in rows]


def compute_locks(db: Session, owner: Owner) -> list[PlayerLock]:
    """Per-player 'eligible again on' dates for this owner — the read-side mirror of
    the write-side _is_eligible rule, so the client never re-derives it.

    Skips (player_id NULL) never lock anyone: the inner join to Player drops them.
    Returns one entry per locked player; anyone absent is eligible.
    - Playoffs: any pick on/after playoff_start locks the player for the whole run
      (available_on=None), ignoring the 30-day window. Regular-season picks don't
      count, matching _is_eligible.
    - Regular season: the player's latest pick locks them until that date + 30 days.
    """
    playoff_start = get_playoff_start_date(db)

    latest_by_player = (
        db.query(Player.nba_player_id, func.max(Pick.game_date).label("last_picked"))
        .join(Pick, Pick.player_id == Player.id)
        .filter(Pick.owner_id == owner.id)
    )
    if playoff_start is not None:
        latest_by_player = latest_by_player.filter(Pick.game_date >= playoff_start)
    rows = latest_by_player.group_by(Player.nba_player_id).all()

    if playoff_start is not None:
        return [PlayerLock(player_id=nba_id, available_on=None) for nba_id, _ in rows]
    return [
        PlayerLock(
            player_id=nba_id,
            available_on=last_picked + timedelta(days=ELIGIBILITY_WINDOW_DAYS),
        )
        for nba_id, last_picked in rows
    ]


def create_pick(
    db: Session, owner: Owner, nba_player_id: int | None, game_date: date
) -> PickRead:
    """Create or replace this owner's pick for game_date.

    The API speaks nba_player_id (like the rest of the app); we resolve it to the
    internal players.id for storage. Re-picking the same night replaces the player
    (TTFL lets you change your pick before the deadline); the 30-day rule and player
    existence are enforced first.

    nba_player_id is None records a skip: no player to validate and no eligibility to
    check — it just claims the night's slot so the forgotten-pick reminder skips it.
    """
    player = None
    if nba_player_id is not None:
        player = db.query(Player).filter(Player.nba_player_id == nba_player_id).first()
        if player is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Player not found")

        playoff_start = get_playoff_start_date(db)
        if not _is_eligible(db, owner, player.id, game_date, playoff_start):
            detail = (
                "Player already picked this playoffs"
                if playoff_start is not None
                else f"Player already picked within {ELIGIBILITY_WINDOW_DAYS} days"
            )
            raise HTTPException(status.HTTP_409_CONFLICT, detail)

    internal_id = player.id if player else None
    pick = (
        db.query(Pick)
        .filter(Pick.owner_id == owner.id, Pick.game_date == game_date)
        .first()
    )
    if pick:
        pick.player_id = internal_id  # change tonight's pick (or convert to/from a skip)
    else:
        pick = Pick(owner_id=owner.id, player_id=internal_id, game_date=game_date)
        db.add(pick)
    db.commit()
    db.refresh(pick)
    return _to_read(pick, nba_player_id)


def create_picks_batch(
    db: Session, owner: Owner, items: list[tuple[int | None, date]]
) -> tuple[int, int]:
    """Authoritative bulk import (TTFL history is the source of truth).

    Bypasses eligibility (the 30-day / playoff rules) and overwrites any existing
    pick on the same night — the imported history always wins. One commit, not N,
    so a full-season import is a single round-trip.

    Returns (imported, skipped); skipped counts items whose player_id doesn't match a
    known player (None player_id is a valid skip and is always imported).
    """
    if not items:
        return 0, 0

    # Resolve every referenced player in one query (skips reference no player).
    wanted_ids = {pid for pid, _ in items if pid is not None}
    internal_by_nba = {
        nba_id: internal_id
        for internal_id, nba_id in db.query(Player.id, Player.nba_player_id)
        .filter(Player.nba_player_id.in_(wanted_ids))
        .all()
    }

    # Pre-load existing picks for the affected nights so clashes overwrite in place.
    affected_dates = {game_date for _, game_date in items}
    by_date = {
        pick.game_date: pick
        for pick in db.query(Pick).filter(
            Pick.owner_id == owner.id, Pick.game_date.in_(affected_dates)
        )
    }

    imported = 0
    skipped = 0
    for nba_player_id, game_date in items:
        if nba_player_id is not None and nba_player_id not in internal_by_nba:
            skipped += 1  # unknown player id — nothing to store
            continue
        internal_id = internal_by_nba.get(nba_player_id)

        pick = by_date.get(game_date)
        if pick:
            pick.player_id = internal_id  # overwrite the clashing night
        else:
            pick = Pick(owner_id=owner.id, player_id=internal_id, game_date=game_date)
            db.add(pick)
            by_date[game_date] = pick  # later items for this night overwrite earlier ones
        imported += 1

    db.commit()
    return imported, skipped


def _to_read(pick: Pick, nba_player_id: int | None) -> PickRead:
    """Serialize a Pick, exposing the NBA player id rather than the internal FK."""
    return PickRead(
        id=pick.id,
        player_id=nba_player_id,
        game_date=pick.game_date,
        picked_at=pick.picked_at,
    )


def delete_pick(db: Session, owner: Owner, pick_id: int) -> None:
    pick = (
        db.query(Pick)
        .filter(Pick.id == pick_id, Pick.owner_id == owner.id)
        .first()
    )
    # Filtering by owner_id means another owner's pick looks identical to a
    # missing one — no information leak about whether the id exists.
    if not pick:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pick not found")
    db.delete(pick)
    db.commit()


def migrate_anon_to_user(db: Session, anon_token: str | None, user: User) -> bool:
    """Move a guest's picks onto their account after sign-in.

    Returns True if a migration happened (so the caller can clear the anon cookie).
    Three cases:
    - no anon identity / no anon picks owner -> nothing to do.
    - user has no owner yet -> reassign the anon owner wholesale; picks follow for
      free (no rows move), and the identity is retired.
    - user already has an owner -> merge: move anon picks onto the user's owner,
      but keep the user's existing pick on any night both hold (uq_pick_owner_date
      forbids two picks per date).
    """
    if not anon_token:
        return False

    identity = (
        db.query(AnonIdentity)
        .filter(AnonIdentity.token == anon_token, AnonIdentity.deleted_at.is_(None))
        .first()
    )
    if identity is None or identity.owner is None:
        return False
    anon_owner = identity.owner

    if user.owner is None:
        anon_owner.user_id = user.id
        anon_owner.identity_id = None
        identity.deleted_at = datetime.now(timezone.utc)
        db.commit()
        return True

    user_owner = user.owner
    owned_dates = {
        d for (d,) in db.query(Pick.game_date).filter(Pick.owner_id == user_owner.id)
    }
    for pick in list(anon_owner.picks):
        if pick.game_date in owned_dates:
            db.delete(pick)  # the signed-in account's pick for that night wins
        else:
            # Reassign via the relationship (not the FK column) so the pick leaves
            # anon_owner.picks; otherwise deleting anon_owner would null its owner_id.
            pick.owner = user_owner
    db.flush()
    db.delete(anon_owner)
    identity.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True


def _is_eligible(
    db: Session,
    owner: Owner,
    player_id: int,
    game_date: date,
    playoff_start: date | None,
) -> bool:
    """True if this player can be picked for game_date.

    Mirrors the frontend rule exactly (lib/picks.ts):
    - Playoffs (playoff_start set): ineligible if picked on any *other* date on or
      after playoff_start — once per playoffs, ignoring the 30-day window.
    - Regular season: ineligible only if picked in the 29 days *before* game_date.
      The window looks backward only, so a later pick never blocks an earlier date.
    """
    clash = db.query(Pick).filter(
        Pick.owner_id == owner.id,
        Pick.player_id == player_id,
        Pick.game_date != game_date,  # replacing this night's pick is fine
    )
    if playoff_start is not None:
        clash = clash.filter(Pick.game_date >= playoff_start)
    else:
        clash = clash.filter(
            Pick.game_date > game_date - timedelta(days=ELIGIBILITY_WINDOW_DAYS),
            Pick.game_date < game_date,
        )
    return clash.first() is None
