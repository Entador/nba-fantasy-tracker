import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from auth.router import router as auth_router
from players.router import router as players_router
from snapshot.router import router as snapshot_router
from core.cache import app_cache
from models.database import SessionLocal, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        app_cache.load_schedule(db)
        print("App ready!")
    except Exception as e:
        print(f"Warning: Could not pre-load cache: {e}")
        print("App will continue but without cached data")
    finally:
        db.close()
    yield


app = FastAPI(
    title="NBA Fantasy Tracker API",
    description="API for tracking Fantasy (NBA Fantasy) player picks",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: ALLOWED_ORIGINS controls which origins can send credentialed requests (cookies).
# In dev, default to "*" (no credentials). In prod, set ALLOWED_ORIGINS to the exact
# frontend URL (e.g. "https://ttfl.vercel.app") and ALLOW_CREDENTIALS=true.
# Mobile clients are native apps and are not subject to CORS.
_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",")]
ALLOW_CREDENTIALS = os.getenv("ALLOW_CREDENTIALS", "false").lower() == "true"

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds()
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Include routers
app.include_router(auth_router)
app.include_router(players_router, prefix="/api", tags=["players"])
app.include_router(snapshot_router, prefix="/api", tags=["snapshot"])


@app.get("/")
def read_root():
    return {"status": "ok", "message": "NBA Fantasy Tracker API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/admin/refresh-cache")
def refresh_cache(db: Session = Depends(get_db)):
    """Refresh the in-memory cache. Call after running daily_update.py."""
    try:
        app_cache.load_schedule(db)
        return {
            "status": "success",
            "message": "Application cache refreshed",
            "games_count": sum(len(games) for games in app_cache.games_by_date.values()),
            "dates_count": len(app_cache.games_by_date),
            "teams_count": len(app_cache.teams_by_id),
            "players_count": len(app_cache.players_by_id),
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to refresh cache: {str(e)}"}
