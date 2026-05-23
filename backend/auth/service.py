"""User lookup and authentication against the database."""

from sqlalchemy.orm import Session

from auth.security import DUMMY_HASH, verify_password
from models import User


def get_user_by_email(db: Session, email: str) -> User | None:
    return (
        db.query(User)
        .filter(User.email == email, User.deleted_at.is_(None))
        .first()
    )


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user or not user.hashed_password:
        # Spend the same time as a real verification to avoid leaking, via
        # timing, whether the email exists.
        verify_password(password, DUMMY_HASH)
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
