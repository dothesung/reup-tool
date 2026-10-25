"""Reup Tool — Trang Admin cho NGƯỜI BÁN (không phải cho khách).

Chỉ hoạt động trên máy có file license_private.pem (máy người bán).
Máy khách không có file này -> API trả has_private_key=false, không tạo key được.
Sổ key (keys_issued.json) chỉ nằm local, gitignored, không push GitHub.
"""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services import license as lic

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/status")
def admin_status():
    return {"has_private_key": os.path.exists(lic.PRIVATE_KEY_PATH),
            "ledger_count": len(lic.list_issued())}


@router.get("/keys")
def admin_keys():
    if not os.path.exists(lic.PRIVATE_KEY_PATH):
        raise HTTPException(403, "Máy này không có license_private.pem (chỉ máy người bán mới tạo key được)")
    return {"items": lic.list_issued()}


class KeyCreate(BaseModel):
    plan: str = "personal"
    months: int = 0
    note: str = ""


@router.post("/keys")
def admin_create_key(body: KeyCreate):
    if body.plan not in lic.PLAN_MACHINES:
        raise HTTPException(400, "plan phải là personal | pro | team")
    if not os.path.exists(lic.PRIVATE_KEY_PATH):
        raise HTTPException(403, "Máy này không có license_private.pem (chỉ máy người bán mới tạo key được)")
    with open(lic.PRIVATE_KEY_PATH, "rb") as f:
        priv_pem = f.read()
    key = lic.create_key(body.plan, body.months, priv_pem)
    entry = lic.record_issued(key, body.plan, body.months, body.note)
    return entry
