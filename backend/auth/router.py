"""Auth endpoints: login and current-user info."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from auth.config import (
    ACCESS_COOKIE_NAME,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    COOKIE_SAMESITE,
    COOKIE_SECURE,
    REFRESH_COOKIE_NAME,
    REFRESH_COOKIE_PATH,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from auth.dependencies import get_current_active_user
from auth.schemas import Token, UserCreate, UserRead
from auth.security import create_access_token
from auth.service import authenticate_user, create_user, get_user_by_email
from auth.sessions import create_session, revoke_session, rotate_session
from models import User
from models.database import get_db
from picks.dependencies import ANON_COOKIE_NAME
from picks.service import migrate_anon_to_user

router = APIRouter(tags=["auth"])


def _claim_guest_picks(request: Request, response: Response, db: Session, user: User) -> None:
    """Carry a guest's picks over to their account, then drop the spent anon cookie."""
    anon_token = request.cookies.get(ANON_COOKIE_NAME)
    if migrate_anon_to_user(db, anon_token, user):
        response.delete_cookie(ANON_COOKIE_NAME)


def _set_access_cookie(response: Response, user: User) -> str:
    """Issue a JWT for `user` and set it as an HttpOnly cookie. Returns the raw token.

    The cookie is a *session* cookie (no max_age) even though the JWT inside expires
    in ACCESS_TOKEN_EXPIRE_MINUTES. Keeping the cookie present after the JWT lapses
    lets open endpoints tell a logged-in-but-expired browser (cookie present, token
    invalid → 401 so the client refreshes) apart from a real guest (no cookie at all).
    The 15-min JWT is still the security boundary; a lingering expired token is inert.
    """
    token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(seconds=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=token,
        httponly=True,  # not readable by JS — mitigates XSS token theft
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
    )
    return token


def _set_refresh_cookie(response: Response, raw_token: str, *, persistent: bool) -> None:
    """Set the refresh-token cookie. persistent=False → a session cookie (cleared on
    browser close), which is how "remember me unchecked" is honored client-side."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400 if persistent else None,
        httponly=True,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    # path/SameSite/Secure must match how it was set or the browser won't clear it.
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
    )


def _start_session(
    request: Request, response: Response, db: Session, user: User, *, persistent: bool
) -> str:
    """Open a refresh session for `user`, set its cookie, and issue an access token."""
    raw_refresh = create_session(
        db, user, persistent=persistent, user_agent=request.headers.get("user-agent")
    )
    _set_refresh_cookie(response, raw_refresh, persistent=persistent)
    return _set_access_cookie(response, user)


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> UserRead:
    # payload.email is already normalized (stripped + lowercased) by the schema.
    if get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )
    user = create_user(db, email=payload.email, password=payload.password)
    _claim_guest_picks(request, response, db, user)
    # Log the new user straight in (web): open a session + set both cookies.
    _start_session(request, response, db, user, persistent=payload.remember_me)
    return user


@router.post("/token")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    # Extra form field alongside the OAuth2 form; the web client sends it, native
    # clients can omit it (defaults to a non-persistent session).
    remember_me: Annotated[bool, Form()] = False,
) -> Token:
    # OAuth2PasswordRequestForm always names the field "username"; we treat it as
    # the email. Normalize it the same way registration does, so a mixed-case
    # login still matches the stored lowercase email.
    user = authenticate_user(db, form_data.username.strip().lower(), form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    _claim_guest_picks(request, response, db, user)
    # Web reads the cookie; native clients use the returned bearer token.
    access_token = _start_session(request, response, db, user, persistent=remember_me)
    return Token(access_token=access_token, token_type="bearer")


@router.post("/auth/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> Token:
    """Rotate the refresh session and mint a fresh access token. Called by the web
    client when a request 401s; native clients can call it directly."""
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    result = rotate_session(db, raw_token, user_agent=request.headers.get("user-agent")) if raw_token else None
    if result is None:
        _clear_refresh_cookie(response)  # stale/invalid — don't keep replaying it
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user, new_refresh, persistent = result
    _set_refresh_cookie(response, new_refresh, persistent=persistent)
    access_token = _set_access_cookie(response, user)
    return Token(access_token=access_token, token_type="bearer")


@router.post("/auth/logout")
async def logout(request: Request, response: Response, db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    # Revoke the server-side session so the refresh token can't be reused.
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_token:
        revoke_session(db, raw_token)
    # SameSite/Secure must match how the cookie was set or the browser won't clear it.
    response.delete_cookie(
        ACCESS_COOKIE_NAME,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
    )
    _clear_refresh_cookie(response)
    return {"status": "ok"}


@router.get("/users/me")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserRead:
    return current_user
