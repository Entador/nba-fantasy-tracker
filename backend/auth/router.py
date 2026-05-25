"""Auth endpoints: login and current-user info."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from auth.config import (
    ACCESS_COOKIE_NAME,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    COOKIE_SAMESITE,
    COOKIE_SECURE,
)
from auth.dependencies import get_current_active_user
from auth.schemas import Token, UserCreate, UserRead
from auth.security import create_access_token
from auth.service import authenticate_user, create_user, get_user_by_email
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
    """Issue a JWT for `user` and set it as an HttpOnly cookie. Returns the raw token."""
    token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,  # not readable by JS — mitigates XSS token theft
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
    )
    return token


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
    _set_access_cookie(response, user)  # log the new user straight in (web)
    return user


@router.post("/token")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
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
    access_token = _set_access_cookie(response, user)
    return Token(access_token=access_token, token_type="bearer")


@router.post("/auth/logout")
async def logout(response: Response) -> dict[str, str]:
    # SameSite/Secure must match how the cookie was set or the browser won't clear it.
    response.delete_cookie(
        ACCESS_COOKIE_NAME,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
    )
    return {"status": "ok"}


@router.get("/users/me")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserRead:
    return current_user
