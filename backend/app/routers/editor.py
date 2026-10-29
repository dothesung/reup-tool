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

# Job workdir map — lấy từ services.paths (portable, không hardcode VM)
from app.services import paths as _paths

def job_dir(jid: str) -> str:
    # Tìm workdir theo job id (tiền tố)
    # 1. Ưu tiên workdir đã lưu trong JOB_STATE (job id là hash, khác tên thư mục)
    try:
        from app.services import worker as _worker
        wd = (_worker.JOB_STATE.get(jid) or {}).get("workdir")
        if wd and os.path.isdir(wd):
            return wd
    except Exception:
        pass
    # 2. Fallback: khớp tên thư mục theo tiền tố (job mở bằng tên workdir)
    JOBS_DIR = _paths.jobs_dir()
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
        r = subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-ss", str(t),
            "-i", src, "-frames:v", "1", "-vf", f"scale={w}:-1", out,
        ])
        if r.returncode != 0 or not os.path.exists(out):
            # t vượt quá thời lượng → lấy frame giữa video
            subprocess.run([
                "ffmpeg", "-y", "-v", "error", "-ss", "5",
                "-i", src, "-frames:v", "1", "-vf", f"scale={w}:-1", out,
            ], check=True)
    return FileResponse(out, media_type="image/png")

@router.get("/jobs/{jid}/info")
def job_info(jid: str):
    """Thông tin video: kích thước, thời lượng."""
    wd = job_dir(jid)
    src = os.path.join(wd, "src.mp4")
    if not os.path.exists(src):
        raise HTTPException(404, "Workdir thiếu file video gốc src.mp4 (có thể đã bị dọn) — Editor cần job còn file gốc")
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

class TranslateBody(BaseModel):
    pass

def _resolve_llm(st: dict) -> dict:
    """Lấy cấu hình LLM thật (preset lấp base_url/model khi trống)."""
    from app.services.llm import resolve_llm
    return resolve_llm(st)

@router.post("/jobs/{jid}/translate-ai")
def translate_ai(jid: str):
    """Dịch resub.srt bằng LLM (chuẩn chat completions) -> sub_vi.srt nháp."""
    from app.services import llm as llmsvc
    from app.routers.settings import load_settings
    wd = job_dir(jid)
    src = os.path.join(wd, "resub.srt")
    if not os.path.exists(src):
        raise HTTPException(404, "Chưa có resub.srt — chạy stage 1 trước")
    st = load_settings()
    if not st.get("llm_enabled"):
        raise HTTPException(400, "Chưa bật AI trong Cài đặt → tab AI")
    try:
        cues, model = llmsvc.translate_cues_ai(parse_srt(src), _resolve_llm(st))
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    write_srt(os.path.join(wd, "sub_vi.srt"), cues)
    return {"job_id": jid, "model": model, "count": len(cues),
            "note": "Bản dịch AI — sửa tay trong bảng trước khi bấm Chạy tiếp"}

@router.post("/jobs/{jid}/caption-ai")
def caption_ai(jid: str):
    """Viết tiêu đề + hashtag bằng LLM từ sub gốc. Không ghi đè gì cả."""
    from app.services import llm as llmsvc
    from app.routers.settings import load_settings
    wd = job_dir(jid)
    src = os.path.join(wd, "resub.srt")
    if not os.path.exists(src):
        raise HTTPException(404, "Chưa có resub.srt — chạy stage 1 trước")
    st = load_settings()
    if not st.get("llm_enabled"):
        raise HTTPException(400, "Chưa bật AI trong Cài đặt → tab AI")
    meta = {}
    mp = os.path.join(wd, "meta.json")
    if os.path.exists(mp):
        try:
            meta = json.load(open(mp))
        except Exception:
            pass
    try:
        out = llmsvc.write_caption(meta.get("title", "") or "",
                                   [c["text"] for c in parse_srt(src)],
                                   _resolve_llm(st))
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    return {"job_id": jid, "orig_title": meta.get("title", ""), **out}

class CaptionOverride(BaseModel):
    title: str = ""
    hashtags: str = ""

@router.get("/jobs/{jid}/caption-override")
def get_caption_override(jid: str):
    wd = job_dir(jid)
    p = os.path.join(wd, "caption_override.json")
    if os.path.exists(p):
        return json.load(open(p))
    return {"title": "", "hashtags": ""}

@router.post("/jobs/{jid}/caption-override")
def set_caption_override(jid: str, body: CaptionOverride):
    """Áp tiêu đề/hashtag riêng cho job này (đè lên mẫu chung khi chạy tiếp)."""
    wd = job_dir(jid)
    p = os.path.join(wd, "caption_override.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"title": body.title, "hashtags": body.hashtags}, f, ensure_ascii=False)
    return {"job_id": jid, "saved": p}

@router.post("/jobs/{jid}/translate")
def translate_subs(jid: str):
    """Dịch máy resub.srt (chữ gốc) -> sub_vi.srt nháp để user sửa tay."""
    from app.services import translator
    from app.routers.settings import load_settings
    wd = job_dir(jid)
    src = os.path.join(wd, "resub.srt")
    if not os.path.exists(src):
        raise HTTPException(404, "Chưa có resub.srt — chạy stage 1 trước")
    st = load_settings()
    cues = parse_srt(src)
    out, engine, errors = translator.translate_cues(
        cues, src=st.get("default_src_lang", "zh-CN"),
        email=st.get("translate_email", ""))
    write_srt(os.path.join(wd, "sub_vi.srt"), out)
    return {"job_id": jid, "engine": engine, "count": len(out),
            "errors": errors,
            "note": "Bản dịch máy — sửa tay trong bảng trước khi bấm Chạy tiếp"}
