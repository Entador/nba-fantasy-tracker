"""Resolve the current pick Owner from either a logged-in user or an anon cookie.

A signed-in user always wins. Otherwise we fall back to the `anon_id` cookie,
minting a new anonymous identity (and setting the cookie) for first-time guests.
"""

import os
from typing import Annotated

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from auth.dependencies import get_optional_user
from models import Owner, User
from models.database import get_db
from picks import service

ANON_COOKIE_NAME = "anon_id"
# ~400 days is the max a browser will honor (Chrome clamps longer values).
ANON_COOKIE_MAX_AGE = 400 * 24 * 60 * 60

# Cross-site prod needs SameSite=None; Secure. Dev over http://localhost needs
# Lax + non-secure (browsers drop Secure cookies on http). Hence env-driven.
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"


def get_current_owner(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_optional_user)],
) -> Owner:
    if user is not None:
        return service.get_or_create_owner_for_user(db, user)

    token = request.cookies.get(ANON_COOKIE_NAME)
    owner, token = service.get_or_create_owner_for_anon(db, token)
    response.set_cookie(
        key=ANON_COOKIE_NAME,
        value=token,
        max_age=ANON_COOKIE_MAX_AGE,
        httponly=True,  # not readable by JS — mitigates XSS token theft
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
    )
    return owner
