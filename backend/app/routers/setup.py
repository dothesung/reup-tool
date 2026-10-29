"""Reup Tool — API trang Thiết lập (kiểm tra + tải phụ thuộc)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import setup as setupsvc

router = APIRouter(prefix="/api/v1/setup", tags=["setup"])


@router.get("/status")
def setup_status():
    return setupsvc.status()


@router.get("/log")
def setup_log():
    return {"installing": setupsvc.INSTALLING, "lines": setupsvc.LOG[-200:]}


class InstallBody(BaseModel):
    step: str = ""


@router.post("/install")
def setup_install(body: InstallBody):
    try:
        started = setupsvc.install(body.step)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not started:
        return {"started": False, "note": "Đang có bước khác chạy — chờ xong rồi bấm lại"}
    return {"started": True}
