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
STATE_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "jobs_state.json"))

# Trạng thái job: {id: {status, step, progress, log, drive_link, error}}
JOB_STATE = {}

_GATE_LOCK = threading.Lock()
_GATE_ACTIVE = [0]  # số job pipeline đang chạy thật (đếm trong RAM, reset khi restart)

def _persist():
    """Lưu JOB_STATE xuống file để backend restart không mất danh sách job."""
    try:
        with open(STATE_PATH, "w") as f:
            json.dump(JOB_STATE, f, ensure_ascii=False)
    except Exception:
        pass

def _restore():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH) as f:
                JOB_STATE.update(json.load(f) or {})
        except Exception:
            pass
    for jid, st in JOB_STATE.items():
        if st.get("status") in ("downloading", "dubbing"):
            st["status"] = "interrupted"
            st["step"] = "Backend đã khởi động lại — bấm Chạy tiếp nếu đã có sub"

_restore()

def _max_parallel():
    try:
        from app.routers.settings import load_settings
        return max(1, min(5, int(load_settings().get("max_parallel_jobs") or 2)))
    except Exception:
        return 2

def _gated(job_id: str, fn, *args):
    """Chờ slot pipeline trống (giới hạn job chạy cùng lúc) rồi mới chạy fn."""
    while True:
        with _GATE_LOCK:
            if _GATE_ACTIVE[0] < _max_parallel():
                _GATE_ACTIVE[0] += 1
                break
        set_status(job_id, "queued", "Xếp hàng — chờ job khác xong")
        time.sleep(10)
    try:
        fn(*args)
    finally:
        with _GATE_LOCK:
            _GATE_ACTIVE[0] = max(0, _GATE_ACTIVE[0] - 1)
        _persist()

def log(job_id: str, msg: str):
    st = JOB_STATE.setdefault(job_id, {})
    st.setdefault("log", []).append(msg)
    print(f"[{job_id}] {msg}")
    _persist()

def set_status(job_id: str, status: str, step: str = ""):
    st = JOB_STATE.setdefault(job_id, {})
    st["status"] = status
    if step:
        st["step"] = step
    _persist()

def run_job(job_id: str, url: str, preset: dict):
    """Chạy pipeline đầy đủ cho 1 job."""
    try:
        set_status(job_id, "downloading", "Tải video")
        log(job_id, f"Bắt đầu: {url}")

        # B1: tải + STT (dùng reup.py stage 1)
        env = dict(os.environ)
        if preset.get("nexray_url"):
            env["NEXRAY_URL"] = preset["nexray_url"]
        r = subprocess.run(
            ["python3", "reup.py", url, "--src-lang", preset.get("src_lang", "zh-CN")],
            cwd=CAPCUT_DIR, capture_output=True, text=True, timeout=900, env=env,
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
        # FrostEditor làm việc trong không gian 720x1280 → scale về kích thước source thật
        frost_cfg = {}
        cfg_path = os.path.join(wd, "frost_config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path) as f:
                frost_cfg = json.load(f)
            src_mp4 = os.path.join(wd, "src.mp4")
            try:
                r = subprocess.run(
                    ["ffprobe", "-v", "error", "-select_streams", "v:0",
                     "-show_entries", "stream=height", "-of", "csv=p=0", src_mp4],
                    capture_output=True, text=True, timeout=30)
                vh = int(r.stdout.strip())
                if vh and vh != 1280:
                    s = vh / 1280
                    for key in ("frost", "cover"):
                        if frost_cfg.get(key):
                            y, h = frost_cfg[key].split(":")
                            frost_cfg[key] = f"{int(int(y) * s)}:{int(int(h) * s)}"
                    log(job_id, f"Scale frost/cover x{s:.2f} về source {vh}p")
            except Exception as e:
                log(job_id, f"Không scale được frost (giữ nguyên): {e}")

        set_status(job_id, "dubbing", "Dub giọng Ngọc Huyền")
        log(job_id, "Dub + burn...")

        # B3: dub + burn (dùng reup.py stage 2)
        # Flag lấy từ preset (đã merge settings làm mặc định ở jobs router).
        cmd = ["python3", "reup.py", "", "--workdir", wd, "--srt", "sub_vi.srt"]
        if frost_cfg.get("frost"):
            cmd += ["--frost", frost_cfg["frost"]]
        elif preset.get("frost_auto"):
            cmd += ["--frost-auto"]
        if frost_cfg.get("cover"):
            cmd += ["--cover", frost_cfg["cover"]]
        if preset.get("v916"):
            cmd += ["--v916", preset["v916"]]
        if preset.get("banner_top"):
            cmd += ["--banner-top", preset["banner_top"]]
        if preset.get("banner_bottom"):
            cmd += ["--banner-bottom", preset["banner_bottom"]]
        if preset.get("banner_color"):
            cmd += ["--banner-color", preset["banner_color"]]
        if preset.get("frost_alpha") is not None:
            cmd += ["--frost-alpha", str(preset["frost_alpha"])]
        if preset.get("engine"):
            cmd += ["--engine", preset["engine"]]
        if preset.get("engine") == "capcut" and preset.get("capcut_voice"):
            cmd += ["--capcut-voice", preset["capcut_voice"]]
        if preset.get("jobs"):
            cmd += ["--jobs", str(preset["jobs"])]
        if preset.get("output_mode") == "draft":
            cmd += ["--draft"]
        if preset.get("with_sub"):
            cmd += ["--with-sub"]
        if preset.get("auto_upload") is False:
            cmd += ["--no-upload"]
        if preset.get("share_drive_link"):
            cmd += ["--share"]

        env = dict(os.environ)
        if preset.get("nexray_url"):
            env["NEXRAY_URL"] = preset["nexray_url"]
        r = subprocess.run(cmd, cwd=CAPCUT_DIR, capture_output=True,
                           text=True, timeout=3600, env=env)
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
    JOB_STATE[job_id] = {"status": "pending", "url": url, "log": [],
                         "preset_used": {k: preset.get(k) for k in
                                         ("engine", "jobs", "capcut_voice", "v916", "output_mode",
                                          "auto_upload", "frost_alpha", "with_sub", "max_parallel_jobs")}}
    _persist()
    t = threading.Thread(target=_gated, args=(job_id, run_job, job_id, url, preset), daemon=True)
    t.start()

def continue_job_async(job_id: str, preset: dict):
    t = threading.Thread(target=_gated, args=(job_id, continue_job, job_id, preset), daemon=True)
    t.start()
