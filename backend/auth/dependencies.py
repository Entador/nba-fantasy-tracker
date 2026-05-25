"""FastAPI dependencies for resolving the current user from a bearer token.

Other routers can protect endpoints by depending on `get_current_active_user`.
"""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from auth.config import ALGORITHM, SECRET_KEY
from models import User
from models.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
# auto_error=False: a missing/invalid token yields None instead of a 401, so
# endpoints open to guests (e.g. picks) can fall back to anonymous identity.
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def _user_from_token(token: str | None, db: Session) -> User | None:
    """Decode a bearer token and return the matching active user, or None."""
    if token is None:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
    except InvalidTokenError:
        return None

    return (
        db.query(User)
        .filter(User.id == int(user_id), User.deleted_at.is_(None))
        .first()
    )


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    user = _user_from_token(token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_optional_user(
    token: Annotated[str | None, Depends(optional_oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    """Like get_current_user but returns None for guests instead of raising."""
    return _user_from_token(token, db)


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
