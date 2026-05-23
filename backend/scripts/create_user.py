"""Create (or update the password of) a user, so you can log in via /token.

Usage:
    poetry run python scripts/create_user.py --email you@example.com --password secret
"""

import argparse
import sys

# Allow running as a standalone script from the backend/ directory.
sys.path.append(".")

from auth.security import get_password_hash  # noqa: E402
from models import User  # noqa: E402
from models.database import SessionLocal  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update a user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == args.email).first()
        if user:
            user.hashed_password = get_password_hash(args.password)
            action = "Updated password for"
        else:
            user = User(
                email=args.email,
                hashed_password=get_password_hash(args.password),
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            action = "Created"
        db.commit()
        db.refresh(user)
        print(f"{action} user id={user.id} email={user.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
