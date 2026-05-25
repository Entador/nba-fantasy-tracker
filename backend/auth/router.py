"""Auth endpoints: login and current-user info."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from auth.config import ACCESS_TOKEN_EXPIRE_MINUTES
from auth.dependencies import get_current_active_user
from auth.schemas import Token, UserCreate, UserRead
from auth.security import create_access_token
from auth.service import authenticate_user, create_user, get_user_by_email
from models import User
from models.database import get_db

router = APIRouter(tags=["auth"])


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    db: Annotated[Session, Depends(get_db)],
) -> UserRead:
    # payload.email is already normalized (stripped + lowercased) by the schema.
    if get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )
    return create_user(db, email=payload.email, password=payload.password)


@router.post("/token")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
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
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/users/me")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserRead:
    return current_user
