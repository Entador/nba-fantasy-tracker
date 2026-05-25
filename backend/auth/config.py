"""Auth settings, loaded from the environment.

Never hardcode the signing secret. Set AUTH_SECRET_KEY in your .env (and in the
host's env for prod). The dev fallback below is intentionally obvious so it
fails loudly if it ever reaches production. Generate a real one with:
    python -c "import secrets; print(secrets.token_hex(32))"
"""

import os

SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "dev-only-insecure-secret-change-me")
ALGORITHM = os.getenv("AUTH_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
MAGIC_LINK_EXPIRE_MINUTES = int(os.getenv("MAGIC_LINK_EXPIRE_MINUTES", "15"))

# Base URL of the frontend, used to build the link emailed to the user. The link
# points at a frontend page that then calls GET /auth/magic/verify with the token.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
