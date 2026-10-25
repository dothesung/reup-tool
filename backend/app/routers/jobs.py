"""Reup Tool — API tuần 3: jobs pipeline + presets."""
import os
import glob
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services import worker
from app.routers.settings import load_settings

router = APIRouter(prefix="/api/v1", tags=["jobs"])

# Settings là cấu hình chung, ĐÈ LÊN preset cho các key trùng nhau
# (để đổi ở trang Cài đặt là có tác dụng ngay với mọi job).
# Preset vẫn giữ vai trò cho các key riêng (draft/final size, hwaccel, mô tả...).
SETTING_KEYS = ["engine", "jobs", "v916", "banner_top", "banner_bottom",
                "banner_color", "frost_alpha", "frost_auto", "with_sub",
                "output_mode", "auto_upload", "share_drive_link", "nexray_url"]

def merge_settings(preset: dict) -> dict:
    st = load_settings()
    merged = dict(preset or {})
    for k in SETTING_KEYS:
        if st.get(k) not in (None, ""):
            merged[k] = st[k]
    return merged

PRESETS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "presets"))

def load_preset(name: str) -> dict:
    path = os.path.join(PRESETS_DIR, f"{name}.yaml")
    if not os.path.exists(path):
        # Thử tìm preset mặc định
        path = os.path.join(PRESETS_DIR, "review_phim.yaml")
    try:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        # Fallback: parse tay nếu không có pyyaml
        d = {}
        with open(path) as f:
            for line in f:
                if ":" in line and not line.startswith(" ") and not line.startswith("#"):
                    k, v = line.split(":", 1)
                    d[k.strip()] = v.strip().strip('"')
        return d
    except Exception:
        return {}

# ---------- Jobs ----------

class JobCreate(BaseModel):
    url: str
    preset: str = "review_phim"
    src_lang: str = "zh-CN"

@router.post("/pipeline/jobs")
def pipeline_create(body: JobCreate):
    jid = uuid.uuid4().hex[:12]
    preset = load_preset(body.preset)
    preset["src_lang"] = body.src_lang
    preset = merge_settings(preset)
    worker.start_job_async(jid, body.url, preset)
    return {"id": jid, "url": body.url, "preset": body.preset, "status": "pending"}

@router.get("/pipeline/jobs")
def pipeline_list():
    return [
        {"id": k, **{kk: vv for kk, vv in v.items() if kk != "log"}}
        for k, v in worker.JOB_STATE.items()
    ]

@router.get("/pipeline/jobs/{jid}")
def pipeline_get(jid: str):
    if jid not in worker.JOB_STATE:
        raise HTTPException(404, "Job không tìm thấy")
    return {"id": jid, **worker.JOB_STATE[jid]}

@router.post("/pipeline/jobs/{jid}/continue")
def pipeline_continue(jid: str, preset_name: str = "review_phim"):
    if jid not in worker.JOB_STATE:
        raise HTTPException(404, "Job không tìm thấy")
    preset = merge_settings(load_preset(preset_name))
    worker.continue_job_async(jid, preset)
    return {"id": jid, "status": "dubbing"}

# ---------- Presets ----------

@router.get("/presets")
def list_presets():
    out = []
    for p in sorted(glob.glob(os.path.join(PRESETS_DIR, "*.yaml"))):
        name = os.path.basename(p)[:-5]
        try:
            out.append({"name": name, **load_preset(name)})
        except Exception:
            out.append({"name": name})
    return out

@router.get("/presets/{name}")
def get_preset(name: str):
    p = load_preset(name)
    if not p:
        raise HTTPException(404, "Preset không tìm thấy")
    return {"name": name, **p}

class PresetSave(BaseModel):
    content: str  # YAML text

@router.put("/presets/{name}")
def save_preset(name: str, body: PresetSave):
    path = os.path.join(PRESETS_DIR, f"{name}.yaml")
    with open(path, "w") as f:
        f.write(body.content)
    return {"name": name, "saved": path}
