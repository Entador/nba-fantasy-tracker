"""Auth settings, loaded from the environment.

Never hardcode the signing secret. Set AUTH_SECRET_KEY in your .env (and in the
host's env for prod). The dev fallback below is intentionally obvious so it
fails loudly if it ever reaches production. Generate a real one with:
    python -c "import secrets; print(secrets.token_hex(32))"
"""

import os

SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "dev-only-insecure-secret-change-me")
ALGORITHM = os.getenv("AUTH_ALGORITHM", "HS256")
# Short-lived access token: the refresh flow silently renews it, so it can be
# brief without logging the user out. Keep it small — it's a stateless JWT and
# can't be revoked before it expires.
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
# Long-lived refresh session ("remember me"): opaque, stored server-side, so it
# IS revocable. Rotated on every use.
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
MAGIC_LINK_EXPIRE_MINUTES = int(os.getenv("MAGIC_LINK_EXPIRE_MINUTES", "15"))

# Web clients carry the JWT in an HttpOnly cookie (not readable by JS, so XSS
# can't steal it); native clients keep using the Authorization: Bearer header.
# Same env-driven SameSite/Secure as the anon_id cookie so dev (http localhost)
# and cross-site prod both work.
ACCESS_COOKIE_NAME = "access_token"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

# Refresh token cookie. Scoped to /auth so it's only sent to the refresh/logout
# endpoints — not on every API call — shrinking its exposure.
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/auth"

# Base URL of the frontend, used to build the link emailed to the user. The link
# points at a frontend page that then calls GET /auth/magic/verify with the token.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
