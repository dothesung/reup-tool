"""Reup Tool — Pipeline worker: download → STT → dub → burn → upload.

Chạy nền bằng thread, state lưu trong jobs dict (tuần 4 chuyển SQLite).
Tái dùng code từ cli/reup.py + services/burner.py.
"""
import os
import subprocess
import threading
import time
import json
import glob

JOBS_DIR = os.path.expanduser("~/workspace/capcut-tts/jobs")
CAPCUT_DIR = os.path.expanduser("~/workspace/capcut-tts")

# Trạng thái job: {id: {status, step, progress, log, drive_link, error}}
JOB_STATE = {}

def log(job_id: str, msg: str):
    st = JOB_STATE.setdefault(job_id, {})
    st.setdefault("log", []).append(msg)
    print(f"[{job_id}] {msg}")

def set_status(job_id: str, status: str, step: str = ""):
    st = JOB_STATE.setdefault(job_id, {})
    st["status"] = status
    if step:
        st["step"] = step

def run_job(job_id: str, url: str, preset: dict):
    """Chạy pipeline đầy đủ cho 1 job."""
    try:
        set_status(job_id, "downloading", "Tải video")
        log(job_id, f"Bắt đầu: {url}")

        # B1: tải + STT (dùng reup.py stage 1)
        r = subprocess.run(
            ["python3", "reup.py", url, "--src-lang", preset.get("src_lang", "zh-CN")],
            cwd=CAPCUT_DIR, capture_output=True, text=True, timeout=900,
        )
        if r.returncode != 0:
            raise RuntimeError(f"Stage 1 lỗi: {r.stderr[-500:]}")

        # Tìm workdir mới nhất
        workdirs = sorted(glob.glob(os.path.join(JOBS_DIR, "102*")),
                          key=os.path.getmtime, reverse=True)
        wd = workdirs[0] if workdirs else None
        if not wd:
            raise RuntimeError("Không tìm thấy workdir sau stage 1")
        log(job_id, f"Workdir: {wd}")

        # B2: chờ sub Việt (user sửa qua SubEditor rồi bấm "Chạy tiếp")
        set_status(job_id, "waiting_sub", "Chờ sub Việt")
        JOB_STATE[job_id]["workdir"] = wd
        log(job_id, "Chờ user viết/sửa sub Việt rồi bấm Chạy tiếp")
    except Exception as e:
        set_status(job_id, "failed", str(e))
        log(job_id, f"LỖI: {e}")

def continue_job(job_id: str, preset: dict):
    """Chạy tiếp từ sau khi có sub Việt: dub → burn → upload."""
    try:
        wd = JOB_STATE.get(job_id, {}).get("workdir")
        if not wd:
            raise RuntimeError("Chưa có workdir — chạy stage 1 trước")
        srt = os.path.join(wd, "sub_vi.srt")
        if not os.path.exists(srt):
            raise RuntimeError("Chưa có sub_vi.srt")

        # Frost config (nếu user đã set qua FrostEditor)
        frost_cfg = {}
        cfg_path = os.path.join(wd, "frost_config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path) as f:
                frost_cfg = json.load(f)

        set_status(job_id, "dubbing", "Dub giọng Ngọc Huyền")
        log(job_id, "Dub + burn...")

        # B3: dub + burn (dùng reup.py stage 2)
        cmd = ["python3", "reup.py", "", "--workdir", wd, "--srt", "sub_vi.srt"]
        if frost_cfg.get("frost"):
            cmd += ["--frost", frost_cfg["frost"]]
        if frost_cfg.get("cover"):
            cmd += ["--cover", frost_cfg["cover"]]
        cmd += ["--frost-alpha", str(frost_cfg.get("frost_alpha", 0.2))]
        if preset.get("v916"):
            cmd += ["--v916", preset["v916"]]
        if preset.get("banner_top"):
            cmd += ["--banner-top", preset["banner_top"]]
        if preset.get("banner_bottom"):
            cmd += ["--banner-bottom", preset["banner_bottom"]]
        # Hardware encode trên macOS (VideoToolbox) hoặc NVENC
        hw = preset.get("hwaccel", "")
        if hw == "videotoolbox":
            cmd += ["--hwaccel", "videotoolbox"]
        elif hw == "nvenc":
            cmd += ["--hwaccel", "nvenc"]

        r = subprocess.run(cmd, cwd=CAPCUT_DIR, capture_output=True,
                           text=True, timeout=3600)
        if r.returncode != 0:
            raise RuntimeError(f"Stage 2 lỗi: {r.stderr[-500:]}")

        # Lấy link Drive từ output
        for line in r.stdout.split("\n"):
            if "drive.google.com" in line and "Link:" in line:
                JOB_STATE[job_id]["drive_link"] = line.split("Link:")[-1].strip()

        set_status(job_id, "done", "Hoàn thành")
        log(job_id, "XONG")
    except Exception as e:
        set_status(job_id, "failed", str(e))
        log(job_id, f"LỖI: {e}")

def start_job_async(job_id: str, url: str, preset: dict):
    JOB_STATE[job_id] = {"status": "pending", "url": url, "log": []}
    t = threading.Thread(target=run_job, args=(job_id, url, preset), daemon=True)
    t.start()

def continue_job_async(job_id: str, preset: dict):
    t = threading.Thread(target=continue_job, args=(job_id, preset), daemon=True)
    t.start()
