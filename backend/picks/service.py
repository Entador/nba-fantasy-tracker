"""Pick ownership and CRUD.

Every read/write is scoped to a single Owner — that scoping IS the authorization
boundary (one owner can never see or touch another's picks).
"""

from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models import AnonIdentity, Owner, Pick, Player, User
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
    return (
        db.query(Pick)
        .filter(Pick.owner_id == owner.id)
        .order_by(Pick.game_date.desc())
        .all()
    )


def create_pick(db: Session, owner: Owner, player_id: int, game_date: date) -> Pick:
    """Create or replace this owner's pick for game_date.

    Re-picking the same night replaces the player (TTFL lets you change your pick
    before the deadline); the 30-day rule and player existence are enforced first.
    """
    if not db.query(Player).filter(Player.id == player_id).first():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Player not found")

    playoff_start = get_playoff_start_date(db)
    if not _is_eligible(db, owner, player_id, game_date, playoff_start):
        detail = (
            "Player already picked this playoffs"
            if playoff_start is not None
            else f"Player already picked within {ELIGIBILITY_WINDOW_DAYS} days"
        )
        raise HTTPException(status.HTTP_409_CONFLICT, detail)

    pick = (
        db.query(Pick)
        .filter(Pick.owner_id == owner.id, Pick.game_date == game_date)
        .first()
    )
    if pick:
        pick.player_id = player_id  # change tonight's pick
    else:
        pick = Pick(owner_id=owner.id, player_id=player_id, game_date=game_date)
        db.add(pick)
    db.commit()
    db.refresh(pick)
    return pick


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
