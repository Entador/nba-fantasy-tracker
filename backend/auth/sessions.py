"""Refresh-session lifecycle: create, rotate, revoke.

Backs the "remember me" flow. A session is a server-side, revocable record of a
long-lived login. The raw refresh token only ever exists in the client cookie;
we store its hash. On every refresh we *rotate*: revoke the presented session and
issue a fresh one (sliding expiry), so a leaked token has a short useful life.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from auth.config import REFRESH_TOKEN_EXPIRE_DAYS
from auth.security import generate_refresh_token, hash_refresh_token
from models import RefreshSession, User


def create_session(
    db: Session, user: User, *, persistent: bool, user_agent: str | None = None
) -> str:
    """Create a refresh session for `user` and return the raw token (store the hash)."""
    raw_token = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(
        RefreshSession(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_token),
            persistent=persistent,
            expires_at=expires_at,
            user_agent=user_agent,
        )
    )
    db.commit()
    return raw_token


def _active_session(db: Session, raw_token: str) -> RefreshSession | None:
    return (
        db.query(RefreshSession)
        .filter(
            RefreshSession.token_hash == hash_refresh_token(raw_token),
            RefreshSession.revoked_at.is_(None),
            RefreshSession.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )


def rotate_session(
    db: Session, raw_token: str, *, user_agent: str | None = None
) -> tuple[User, str, bool] | None:
    """Validate the presented token, revoke it, and issue a new one.

    Returns (user, new_raw_token, persistent) on success, or None if the token is
    unknown / expired / revoked or the user is gone/inactive.
    """
    session = _active_session(db, raw_token)
    if session is None:
        return None

    user = (
        db.query(User)
        .filter(User.id == session.user_id, User.deleted_at.is_(None))
        .first()
    )
    if user is None or not user.is_active:
        return None

    now = datetime.now(timezone.utc)
    session.revoked_at = now
    session.last_used_at = now
    new_token = create_session(
        db, user, persistent=session.persistent, user_agent=user_agent
    )
    return user, new_token, session.persistent


def revoke_session(db: Session, raw_token: str) -> None:
    """Revoke the session for this token, if it exists (used on logout)."""
    session = _active_session(db, raw_token)
    if session is not None:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()


def revoke_all_sessions(db: Session, user: User) -> int:
    """Revoke every active session for a user ("log out everywhere"). Returns count."""
    now = datetime.now(timezone.utc)
    count = (
        db.query(RefreshSession)
        .filter(
            RefreshSession.user_id == user.id,
            RefreshSession.revoked_at.is_(None),
        )
        .update({RefreshSession.revoked_at: now})
    )
    db.commit()
    return count
