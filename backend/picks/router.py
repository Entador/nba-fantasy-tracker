"""Pick endpoints. Open to guests and users alike via get_current_owner."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from core.rate_limit import limiter
from models import Owner
from models.database import get_db
from picks import service
from picks.dependencies import get_current_owner
from picks.schemas import PickBatchCreate, PickCreate, PickImportResult, PickRead

router = APIRouter(prefix="/api/picks", tags=["picks"])

OwnerDep = Annotated[Owner, Depends(get_current_owner)]
DbDep = Annotated[Session, Depends(get_db)]

# These endpoints are open to guests (no login), so they're rate-limited per IP to
# curb write-spam. slowapi needs `request: Request` (to read the limit key) and
# `response: Response` (to inject the X-RateLimit-* headers) in each signature.


@router.get("")
@limiter.limit("60/minute")
def list_picks(
    request: Request, response: Response, owner: OwnerDep, db: DbDep
) -> list[PickRead]:
    return service.list_picks(db, owner)


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_pick(
    request: Request, response: Response, payload: PickCreate, owner: OwnerDep, db: DbDep
) -> PickRead:
    return service.create_pick(db, owner, payload.player_id, payload.game_date)


@router.post("/batch", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")  # bulk write — the heaviest, so the tightest limit
def create_picks_batch(
    request: Request,
    response: Response,
    payload: PickBatchCreate,
    owner: OwnerDep,
    db: DbDep,
) -> PickImportResult:
    imported, skipped = service.create_picks_batch(
        db, owner, [(p.player_id, p.game_date) for p in payload.picks]
    )
    return PickImportResult(imported=imported, skipped=skipped)


@router.delete("/{pick_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
def delete_pick(
    request: Request, response: Response, pick_id: int, owner: OwnerDep, db: DbDep
) -> None:
    service.delete_pick(db, owner, pick_id)
