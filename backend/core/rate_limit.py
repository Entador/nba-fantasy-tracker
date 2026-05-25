"""Application rate limiting (slowapi).

Scoped to the abuse-prone auth endpoints (login / register) — not the read-heavy
snapshot/picks paths. Limits are keyed per client IP.

Storage:
- prod: set RATELIMIT_STORAGE_URI to a shared store (Upstash Redis, e.g.
  `rediss://default:<password>@<host>:6379`) so one counter is shared across
  Vercel's serverless instances.
- dev / unset: in-memory (`memory://`) — per-process and resets on restart.
  Fine locally, but NOT a real limit on serverless (each instance counts alone).

Set RATELIMIT_ENABLED=false to turn limiting off (used by the test suite, which
hammers /token and /auth/register from a single host).
"""

import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
ENABLED = os.getenv("RATELIMIT_ENABLED", "true").lower() == "true"


def client_ip(request: Request) -> str:
    """Real client IP for keying limits.

    Behind Vercel's proxy the socket peer is the proxy, so `request.client.host`
    is the same for everyone. Prefer the first hop of X-Forwarded-For; fall back
    to the socket address only when there's no proxy header (local dev).
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# swallow_errors: if Redis is unreachable, allow the request rather than 500.
# Being able to log in matters more than strict limiting during a storage outage.
limiter = Limiter(
    key_func=client_ip,
    storage_uri=STORAGE_URI,
    enabled=ENABLED,
    swallow_errors=True,
    headers_enabled=True,  # send Retry-After + X-RateLimit-* so clients can back off
)
