"""Reup Tool — FastAPI backend (scaffold tuần 1)."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uuid

from app.routers import editor, jobs, settings, license, admin, setup

app = FastAPI(title="Reup Tool", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(editor.router)
app.include_router(jobs.router)
app.include_router(settings.router)
app.include_router(license.router)
app.include_router(admin.router)
app.include_router(setup.router)

# Store tạm (tuần 1 dùng dict, tuần sau chuyển SQLite)
jobs = {}

class JobCreate(BaseModel):
    url: str
    preset: str = "review_phim"
    src_lang: str = "zh-CN"

class JobUpdate(BaseModel):
    status: Optional[str] = None
    frost: Optional[str] = None
    cover: Optional[str] = None
    drive_link: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}

# --- Phục vụ frontend build sẵn (chế độ đóng gói / production) ---
# Khi có frontend/dist (sau `npm run build`), backend tự serve UI ở http://localhost:8000
# nên bản đóng gói chỉ cần 1 tiến trình, không cần chạy Vite riêng.
import os as _os
from fastapi.responses import FileResponse as _FileResponse
from fastapi.staticfiles import StaticFiles as _StaticFiles
_BASE = _os.path.dirname(__file__)
# Bản đóng gói: <bundle>/app/main.py -> <bundle>/frontend/dist
# Chạy từ source: backend/app/main.py -> frontend/dist
_DIST = next((p for p in (
    _os.path.join(_BASE, "..", "frontend", "dist"),
    _os.path.join(_BASE, "..", "..", "frontend", "dist"),
) if _os.path.isdir(p)), None)
if _DIST:
    app.mount("/assets", _StaticFiles(directory=_os.path.join(_DIST, "assets")), name="assets")

    @app.get("/")
    def _serve_ui():
        return _FileResponse(_os.path.join(_DIST, "index.html"))

@app.post("/jobs")
def create_job(body: JobCreate):
    jid = uuid.uuid4().hex[:12]
    jobs[jid] = {
        "id": jid, "url": body.url, "preset": body.preset,
        "src_lang": body.src_lang, "status": "pending",
    }
    return jobs[jid]

@app.get("/jobs")
def list_jobs():
    return list(jobs.values())

@app.get("/jobs/{jid}")
def get_job(jid: str):
    if jid not in jobs:
        raise HTTPException(404, "Job not found")
    return jobs[jid]

@app.patch("/jobs/{jid}")
def update_job(jid: str, body: JobUpdate):
    if jid not in jobs:
        raise HTTPException(404, "Job not found")
    for k, v in body.dict(exclude_none=True).items():
        jobs[jid][k] = v
    return jobs[jid]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
