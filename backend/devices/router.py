"""Device + notification-preferences endpoints. All require an authenticated user."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from auth.dependencies import get_current_active_user
from devices import service
from devices.schemas import (
    DeviceRead,
    DeviceRegister,
    NotificationPrefRead,
    NotificationPrefUpdate,
)
from models import User
from models.database import get_db

router = APIRouter(tags=["devices"])

UserDep = Annotated[User, Depends(get_current_active_user)]
DbDep = Annotated[Session, Depends(get_db)]


@router.post("/api/devices/register", status_code=status.HTTP_201_CREATED)
def register_device(payload: DeviceRegister, user: UserDep, db: DbDep) -> DeviceRead:
    return service.register_device(db, user, payload.push_token, payload.platform)


@router.delete("/api/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(device_id: int, user: UserDep, db: DbDep) -> None:
    service.revoke_device(db, user, device_id)


@router.get("/api/notification-prefs")
def read_prefs(user: UserDep, db: DbDep) -> NotificationPrefRead:
    return service.get_or_create_prefs(db, user)


@router.patch("/api/notification-prefs")
def patch_prefs(
    payload: NotificationPrefUpdate, user: UserDep, db: DbDep
) -> NotificationPrefRead:
    return service.update_prefs(
        db, user, payload.injury_alerts, payload.deadline_alerts
    )
