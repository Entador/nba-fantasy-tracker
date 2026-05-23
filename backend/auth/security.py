"""Password hashing and JWT creation primitives."""

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
