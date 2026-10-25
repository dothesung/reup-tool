"""Reup Tool — API tuần 2: frame, frost detect, sub edit."""
import os
import subprocess
import json
import re
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/v1", tags=["editor"])

# Job workdir map (tuần 2: dùng thư mục jobs/ local)
JOBS_DIR = os.path.expanduser("~/workspace/capcut-tts/jobs")

def job_dir(jid: str) -> str:
    # Tìm workdir theo job id (tiền tố)
    for d in os.listdir(JOBS_DIR):
        if d.startswith(jid) or jid in d:
            return os.path.join(JOBS_DIR, d)
    raise HTTPException(404, f"Job {jid} không tìm thấy")

# ---------- Frame ----------

@router.get("/jobs/{jid}/frame")
def get_frame(jid: str, t: float = 10.0, w: int = 720):
    """Trích 1 frame tại thời điểm t (giây), trả về PNG."""
    wd = job_dir(jid)
    src = os.path.join(wd, "src.mp4")
    if not os.path.exists(src):
        raise HTTPException(404, "src.mp4 không tồn tại")
    out = os.path.join(wd, f"frame_{int(t)}s.png")
    if not os.path.exists(out):
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-ss", str(t),
            "-i", src, "-frames:v", "1", "-vf", f"scale={w}:-1", out,
        ], check=True)
    return FileResponse(out, media_type="image/png")

@router.get("/jobs/{jid}/info")
def job_info(jid: str):
    """Thông tin video: kích thước, thời lượng."""
    wd = job_dir(jid)
    src = os.path.join(wd, "src.mp4")
    r = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration",
        "-of", "json", src,
    ], capture_output=True, text=True)
    info = json.loads(r.stdout)["streams"][0]
    return {"job_id": jid, "width": info["width"], "height": info["height"],
            "duration": float(info["duration"]), "workdir": wd}

# ---------- Frost detect ----------

@router.post("/jobs/{jid}/detect")
def detect_text(jid: str):
    """Chạy detect_text_types.py → trả về vùng text cố định + subtitle."""
    wd = job_dir(jid)
    src = os.path.join(wd, "src.mp4")
    script = os.path.join(os.path.dirname(__file__), "services", "text_types.py")
    out_json = os.path.join(wd, "text_types.json")
    if not os.path.exists(out_json):
        r = subprocess.run(
            ["python3", script, src, "--output", out_json],
            capture_output=True, text=True, timeout=300,
        )
        if r.returncode != 0:
            raise HTTPException(500, f"Detect lỗi: {r.stderr[-500:]}")
    with open(out_json) as f:
        return json.load(f)

class FrostSet(BaseModel):
    frost: Optional[str] = None   # "Y:H" trên output 720x1280
    cover: Optional[str] = None   # "Y:H"
    frost_alpha: float = 0.2
    cover_alpha: float = 0.3

@router.post("/jobs/{jid}/frost")
def set_frost(jid: str, body: FrostSet):
    """Lưu cấu hình frost/cover vào job."""
    wd = job_dir(jid)
    cfg = os.path.join(wd, "frost_config.json")
    with open(cfg, "w") as f:
        json.dump(body.dict(), f, indent=2)
    return {"job_id": jid, "saved": cfg, **body.dict()}

@router.get("/jobs/{jid}/frost")
def get_frost(jid: str):
    wd = job_dir(jid)
    cfg = os.path.join(wd, "frost_config.json")
    if os.path.exists(cfg):
        with open(cfg) as f:
            return json.load(f)
    return {"frost": None, "cover": None, "frost_alpha": 0.2, "cover_alpha": 0.3}

# ---------- Sub edit ----------

def parse_srt(path: str) -> List[dict]:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    cues = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        try:
            idx = int(lines[0])
        except ValueError:
            continue
        m = re.match(r"(.+) --> (.+)", lines[1])
        if not m:
            continue
        cues.append({"id": idx, "start": m.group(1), "end": m.group(2),
                     "text": "\n".join(lines[2:])})
    return cues

def write_srt(path: str, cues: List[dict]):
    with open(path, "w", encoding="utf-8") as f:
        for i, c in enumerate(cues, 1):
            f.write(f"{i}\n{c['start']} --> {c['end']}\n{c['text']}\n\n")

@router.get("/jobs/{jid}/subs")
def get_subs(jid: str):
    wd = job_dir(jid)
    srt = os.path.join(wd, "sub_vi.srt")
    if not os.path.exists(srt):
        srt = os.path.join(wd, "resub.srt")
    if not os.path.exists(srt):
        raise HTTPException(404, "Chưa có file sub")
    return {"job_id": jid, "cues": parse_srt(srt)}

class SubUpdate(BaseModel):
    cues: List[dict]

@router.put("/jobs/{jid}/subs")
def put_subs(jid: str, body: SubUpdate):
    wd = job_dir(jid)
    srt = os.path.join(wd, "sub_vi.srt")
    write_srt(srt, body.cues)
    return {"job_id": jid, "saved": srt, "count": len(body.cues)}
