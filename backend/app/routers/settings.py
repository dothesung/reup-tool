"""Reup Tool — Cài đặt hệ thống (v1.2).

Lưu tại settings.json ở root repo (gitignore — chứa key).
GET luôn che secret (chỉ hiện 4 ký tự cuối). PUT: field secret để trống = giữ nguyên.
Settings là cấu hình chung, đè lên preset cho các key trùng nhau (xem merge_settings
ở routers/jobs.py); worker truyền flag tương ứng sang reup.py.
"""
import json
import os
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1", tags=["settings"])

SETTINGS_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "settings.json"))
EXAMPLE_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "settings.example.json"))

# Secret: không bao giờ trả full qua API
SECRET_FIELDS = {"facebook_page_token"}

DEFAULTS = {
    # Thương hiệu (hiện ở nav, phục vụ thương mại hóa)
    "brand_name": "Reup Tool",
    # Chung
    "default_preset": "review_phim",
    "default_src_lang": "zh-CN",
    "auto_upload": True,        # False -> reup.py --no-upload
    "share_drive_link": False,  # True -> reup.py --share (link public)
    "output_mode": "final",    # final | draft (-> --draft: 720x1280, ultrafast)
    # Lồng tiếng
    "engine": "kokoro",        # kokoro | capcut
    "jobs": 4,                  # số TTS song song (1-8)
    "with_sub": False,          # True -> burn sub Việt lên video
    # Khung 9:16 & che
    "v916": "square",           # auto | square | black | blur | off
    "banner_top": "REVIEW PHIM HAY",
    "banner_bottom": "PHIM HAY MỖI NGÀY",
    "banner_color": "FFCC00",
    "frost_alpha": 0.2,         # độ mờ thanh che sub cũ
    "frost_auto": False,        # True -> tự phát hiện vùng sub (khi không set tay)
    # Tích hợp
    "nexray_url": "",           # để trống = dùng mặc định của reup.py
    "facebook_page_id": "",
    "facebook_page_token": "",
}


def load_settings() -> dict:
    """Đọc settings thật (kể cả secret) — chỉ dùng nội bộ (worker)."""
    merged = dict(DEFAULTS)
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH) as f:
                merged.update(json.load(f) or {})
        except Exception:
            pass
    return merged


def public_settings() -> dict:
    """Bản che secret để trả qua API."""
    out = load_settings()
    for k in SECRET_FIELDS:
        v = out.get(k) or ""
        out[k] = ("••••" + v[-4:]) if len(v) > 4 else ("••••" if v else "")
    out["_secrets_saved"] = {k: bool(load_settings().get(k)) for k in SECRET_FIELDS}
    return out


@router.get("/settings")
def get_settings():
    return public_settings()


class SettingsSave(BaseModel):
    brand_name: Optional[str] = None
    default_preset: Optional[str] = None
    default_src_lang: Optional[str] = None
    auto_upload: Optional[bool] = None
    share_drive_link: Optional[bool] = None
    output_mode: Optional[str] = None
    engine: Optional[str] = None
    jobs: Optional[int] = None
    with_sub: Optional[bool] = None
    v916: Optional[str] = None
    banner_top: Optional[str] = None
    banner_bottom: Optional[str] = None
    banner_color: Optional[str] = None
    frost_alpha: Optional[float] = None
    frost_auto: Optional[bool] = None
    nexray_url: Optional[str] = None
    facebook_page_id: Optional[str] = None
    facebook_page_token: Optional[str] = None


@router.put("/settings")
def save_settings(body: SettingsSave):
    cur = load_settings()
    data = body.dict(exclude_none=True)
    # Secret để trống (hoặc giá trị đã che) = giữ nguyên
    for k in SECRET_FIELDS:
        v = data.get(k)
        if not v or v.startswith("••"):
            data.pop(k, None)
    # Validate nhẹ
    if data.get("output_mode") not in (None, "final", "draft"):
        data["output_mode"] = "final"
    if data.get("engine") not in (None, "kokoro", "capcut"):
        data["engine"] = "kokoro"
    if data.get("v916") not in (None, "auto", "square", "black", "blur", "off"):
        data["v916"] = "square"
    if data.get("jobs") is not None:
        data["jobs"] = max(1, min(8, int(data["jobs"])))
    if data.get("frost_alpha") is not None:
        data["frost_alpha"] = max(0.05, min(0.9, float(data["frost_alpha"])))
    cur.update(data)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(cur, f, ensure_ascii=False, indent=1)
    return public_settings()
