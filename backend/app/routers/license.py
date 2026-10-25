"""Reup Tool — License router: xem trạng thái + kích hoạt key."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import license as lic

router = APIRouter(prefix="/api/v1", tags=["license"])


@router.get("/license")
def license_status():
    return lic.get_status()


class ActivateBody(BaseModel):
    key: str


@router.post("/license/activate")
def license_activate(body: ActivateBody):
    try:
        return lic.activate(body.key)
    except ValueError as e:
        raise HTTPException(402, str(e))
