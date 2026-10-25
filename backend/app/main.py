"""Reup Tool — FastAPI backend (scaffold tuần 1)."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uuid

from app.routers import editor, jobs

app = FastAPI(title="Reup Tool", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(editor.router)
app.include_router(jobs.router)

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
    return {"status": "ok", "version": "1.0.0"}

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
