"""Reup Tool — API tuần 3: jobs pipeline + presets."""
import os
import glob
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services import worker
from app.routers.settings import load_settings
from app.services import license as lic

router = APIRouter(prefix="/api/v1", tags=["jobs"])

# Settings là cấu hình chung, ĐÈ LÊN preset cho các key trùng nhau
# (để đổi ở trang Cài đặt là có tác dụng ngay với mọi job).
# Preset vẫn giữ vai trò cho các key riêng (draft/final size, hwaccel, mô tả...).
SETTING_KEYS = ["engine", "jobs", "capcut_voice", "max_parallel_jobs",
                "v916", "banner_top", "banner_bottom",
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
    try:
        lic.check_or_raise()
    except RuntimeError as e:
        raise HTTPException(402, str(e))
    jid = uuid.uuid4().hex[:12]
    preset = load_preset(body.preset)
    preset["src_lang"] = body.src_lang
    preset = merge_settings(preset)
    worker.start_job_async(jid, body.url, preset)
    lic.count_trial_video()
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

class PostFBBody(BaseModel):
    workdir: Optional[str] = None  # khi backend mới khởi động, JOB_STATE trống

@router.post("/pipeline/jobs/{jid}/post-facebook")
def pipeline_post_facebook(jid: str, body: Optional[PostFBBody] = None):
    """Đăng final.mp4 của job lên Fanpage (cần Page ID + token trong Cài đặt)."""
    from app.services import facebook as fb
    st = load_settings()
    wd = worker.JOB_STATE.get(jid, {}).get("workdir") or (body.workdir if body else None)
    if not wd:
        raise HTTPException(404, "Không tìm thấy workdir — backend mới khởi động? Nhập workdir")
    if not os.path.isdir(wd):
        # workdir có thể là basename
        cand = os.path.join(worker.JOBS_DIR, wd)
        wd = cand if os.path.isdir(cand) else wd
    final = os.path.join(wd, "final.mp4")
    cap = os.path.join(wd, "caption.txt")
    caption = ""
    if os.path.exists(cap):
        with open(cap, encoding="utf-8") as f:
            caption = f.read()
    try:
        out = fb.post_video(st.get("facebook_page_id", ""), st.get("facebook_page_token", ""),
                            final, caption)
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    if jid in worker.JOB_STATE:
        worker.JOB_STATE[jid]["fb_post_id"] = out["id"]
    return {"id": jid, "fb_post_id": out["id"],
            "url": f"https://www.facebook.com/{out['id']}"}

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
