"""Password hashing and JWT creation primitives."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from auth.config import ALGORITHM, SECRET_KEY

password_hash = PasswordHash.recommended()

# Pre-computed hash used to keep authentication timing constant when a username
# does not exist, mitigating user-enumeration via response-time differences.
DUMMY_HASH = password_hash.hash("dummypassword")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def generate_refresh_token() -> str:
    """A high-entropy opaque refresh token (the raw value handed to the client)."""
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for storage/lookup.

    Plain SHA-256 (not bcrypt) on purpose: the token is 256 bits of randomness,
    not a guessable password, so it isn't brute-forceable — a fast hash is enough
    and lets us index the column and look sessions up by hash.
    """
    return hashlib.sha256(token.encode()).hexdigest()
