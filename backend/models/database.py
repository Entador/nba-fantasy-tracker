from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")


def pin_psycopg2_driver(url: str) -> str:
    """Force any Postgres URL onto psycopg2, the driver we actually ship.

    Neon's SQLAlchemy snippet hands out "postgresql+psycopg://" (psycopg 3).
    SQLAlchemy honours that suffix, imports a driver that isn't in
    requirements.txt, and create_engine raises ModuleNotFoundError at import
    time — which takes down every route, not just the DB-backed ones. Pinning
    the driver here means the deploy runs the same one as local dev and the
    tests, whatever scheme the host's DATABASE_URL happens to use.

    Non-Postgres URLs (e.g. sqlite://) are returned untouched.
    """
    scheme, separator, rest = url.partition("://")
    if not separator or not scheme.startswith("postgres"):
        return url
    return f"postgresql+psycopg2://{rest}"


if DATABASE_URL:
    engine = create_engine(
        pin_psycopg2_driver(DATABASE_URL),
        pool_pre_ping=True,  # Test connections before use, reconnect if stale
        pool_recycle=300,    # Recycle connections after 5 minutes
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    # Allow server to start without database for testing API docs
    engine = None
    SessionLocal = None
    logger.warning("DATABASE_URL not set. Database operations will fail.")

Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get database session"""
    if SessionLocal is None:
        raise RuntimeError("Database not configured. Set DATABASE_URL environment variable.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
