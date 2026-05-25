"""Pick endpoints. Open to guests and users alike via get_current_owner."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from models import Owner
from models.database import get_db
from picks import service
from picks.dependencies import get_current_owner
from picks.schemas import PickBatchCreate, PickCreate, PickImportResult, PickRead

router = APIRouter(prefix="/api/picks", tags=["picks"])

OwnerDep = Annotated[Owner, Depends(get_current_owner)]
DbDep = Annotated[Session, Depends(get_db)]


@router.get("")
def list_picks(owner: OwnerDep, db: DbDep) -> list[PickRead]:
    return service.list_picks(db, owner)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_pick(payload: PickCreate, owner: OwnerDep, db: DbDep) -> PickRead:
    return service.create_pick(db, owner, payload.player_id, payload.game_date)


@router.post("/batch", status_code=status.HTTP_201_CREATED)
def create_picks_batch(
    payload: PickBatchCreate, owner: OwnerDep, db: DbDep
) -> PickImportResult:
    imported, skipped = service.create_picks_batch(
        db, owner, [(p.player_id, p.game_date) for p in payload.picks]
    )
    return PickImportResult(imported=imported, skipped=skipped)


@router.delete("/{pick_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pick(pick_id: int, owner: OwnerDep, db: DbDep) -> None:
    service.delete_pick(db, owner, pick_id)
