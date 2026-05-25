"""FastAPI dependencies for resolving the current user from a bearer token.

Other routers can protect endpoints by depending on `get_current_active_user`.
"""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from auth.config import ACCESS_COOKIE_NAME, ALGORITHM, SECRET_KEY
from models import User
from models.database import get_db

# auto_error=False: a missing/invalid header yields None instead of a 401, so we
# can fall back to the cookie (web) and guests can stay anonymous on open endpoints.
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def _token_from_request(request: Request, header_token: str | None) -> str | None:
    """Prefer the Authorization header (native clients); fall back to the cookie (web)."""
    return header_token or request.cookies.get(ACCESS_COOKIE_NAME)


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
    request: Request,
    header_token: Annotated[str | None, Depends(optional_oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    user = _user_from_token(_token_from_request(request, header_token), db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_optional_user(
    request: Request,
    header_token: Annotated[str | None, Depends(optional_oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    """Like get_current_user but returns None for guests instead of raising."""
    return _user_from_token(_token_from_request(request, header_token), db)


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
