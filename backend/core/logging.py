"""Structured logging setup — stdlib only, no extra dependencies.

What this gives us:
- Log levels by environment via LOG_LEVEL (dev: DEBUG, prod: INFO/ERROR).
- Per-request context (request_id, user_id) injected into every record through
  contextvars + a logging.Filter, so call sites stay plain `logger.info(...)`.
- Optional JSON output (LOG_JSON=true) so a log aggregator (Filebeat → Elasticsearch,
  Datadog, etc.) can search/filter on the fields instead of grepping text.

Sensitive data (passwords, tokens, API keys, DB credentials) must never be passed
to the logger — we only ever log IDs and messages, never secrets or raw payloads.

If we outgrow this, structlog/python-json-logger are drop-in replacements; the
contextvars and call sites wouldn't change.
"""

import json
import logging
import os
import sys
from contextvars import ContextVar

# ANSI colors per level, applied to the level name in TTY (text) output only.
_LEVEL_COLORS = {
    "DEBUG": "\033[36m",     # cyan
    "INFO": "\033[32m",      # green
    "WARNING": "\033[33m",   # yellow
    "ERROR": "\033[31m",     # red
    "CRITICAL": "\033[1;31m",  # bold red
}
_RESET = "\033[0m"

# Set by configure_logging() so helpers (e.g. color_status) match the formatter's
# decision — colored on a TTY, plain when piped/redirected or in JSON mode.
_use_color = False


def color_status(status_code: int) -> str:
    """Color an HTTP status code by class (2xx green … 5xx red) for log messages."""
    if not _use_color:
        return str(status_code)
    color = _LEVEL_COLORS["INFO"]      # 2xx green
    if status_code >= 500:
        color = _LEVEL_COLORS["ERROR"]
    elif status_code >= 400:
        color = _LEVEL_COLORS["WARNING"]
    elif status_code >= 300:
        color = _LEVEL_COLORS["DEBUG"]  # 3xx cyan
    return f"{color}{status_code}{_RESET}"

# Request-scoped context. Defaults ("-") keep logging working outside a request
# (startup, scripts, background jobs), where no middleware has set them.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
user_id_var: ContextVar[str] = ContextVar("user_id", default="-")


class ContextFilter(logging.Filter):
    """Copy the request-scoped contextvars onto each record so formatters see them."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """Minimal JSON lines formatter — one object per record, easy to ship + index."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "user_id": getattr(record, "user_id", "-"),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


class ColorFormatter(logging.Formatter):
    """Text formatter that colors the level name. Used only on a TTY."""

    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname}{_RESET}" if color else record.levelname
        return super().format(record)


def configure_logging() -> None:
    """Install a single root handler. Call once at startup, before anything logs."""
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    json_logs = os.getenv("LOG_JSON", "false").lower() == "true"

    handler = logging.StreamHandler()
    handler.addFilter(ContextFilter())
    if json_logs:
        handler.setFormatter(JsonFormatter())
    else:
        # Colorize only on an interactive terminal; piped/redirected output stays
        # clean (no escape codes polluting log files). LOG_COLOR overrides either way.
        fmt = (
            "%(asctime)s %(levelname)s %(name)s "
            "[req=%(request_id)s user=%(user_id)s] %(message)s"
        )
        color_env = os.getenv("LOG_COLOR")
        use_color = (
            color_env.lower() == "true" if color_env is not None
            else sys.stderr.isatty()
        )
        global _use_color
        _use_color = use_color
        handler.setFormatter(ColorFormatter(fmt) if use_color else logging.Formatter(fmt))

    root = logging.getLogger()
    root.handlers.clear()  # replace uvicorn/basicConfig defaults so context is applied
    root.addHandler(handler)
    root.setLevel(level)

    # Make uvicorn's own loggers emit through our handler instead of their default
    # one, so startup/error/access lines share this format (and the req/user context
    # when they fire inside a request). They keep their own levels; we only redirect
    # where they write. uvicorn.access stays as the canonical always-on access log;
    # our DEBUG →/← lines are extra dev detail that also carry the request id.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv = logging.getLogger(name)
        uv.handlers.clear()
        uv.propagate = True
