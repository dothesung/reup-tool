"""Reup Tool — kiểm tra + tải/cài phụ thuộc cho máy mới (trang Thiết lập).

Chạy cài đặt trong thread nền, log giữ trong bộ nhớ, frontend poll /setup/log.
Các bước:
  - deps: pip install backend/requirements.txt + cli/requirements.txt
  - sdk: git clone K07VN/capcut-tts-api -> <capcut_dir>/upstream + pip install
  - ffmpeg: tải bản static theo OS về <repo>/bin/ (Linux chỉ hướng dẫn apt)
Kokoro KHÔNG tự tải (nặng, cần torch + model riêng) — chỉ kiểm tra + hướng dẫn.
"""
import os
import platform
import shutil
import subprocess
import sys
import threading
import zipfile

from app.services import paths

LOG: list = []
INSTALLING = False


def _log(msg: str):
    LOG.append(msg)


def _run(cmd, **kw):
    _log("$ " + " ".join(str(c) for c in cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, **kw)
    tail = (r.stdout + r.stderr)[-800:]
    if tail.strip():
        _log(tail.strip())
    if r.returncode != 0:
        raise RuntimeError(f"Lệnh thất bại (exit {r.returncode}): {' '.join(str(c) for c in cmd)}")


def _ffmpeg_path():
    for p in (os.path.join(paths.repo_bin_dir(), "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"),
              shutil.which("ffmpeg") or ""):
        if p and os.path.isfile(p):
            return p
    return None


def status() -> dict:
    cap_dir, cands = paths.resolve_capcut_dir()
    files = {}
    if cap_dir:
        for f in ("reup.py", "reup_sub.py", "stt_words.py", "autodetect_frost.py"):
            files[f] = os.path.isfile(os.path.join(cap_dir, f))
    sdk_ok = False
    sdk_detail = "chưa kiểm tra được"
    try:
        r = subprocess.run([paths.capcut_py(), "-c", "import capcut_tts_api"],
                           capture_output=True, text=True, timeout=60)
        sdk_ok = r.returncode == 0
        sdk_detail = "đã cài" if sdk_ok else "chưa cài (STT CapCut sẽ lỗi)"
    except Exception as e:
        sdk_detail = f"lỗi kiểm tra: {e}"
    st = paths._load_settings_raw()
    kokoro_script = ""
    if st.get("kokoro_dir"):
        kokoro_script = os.path.join(os.path.expanduser(st["kokoro_dir"]), "batch_synth.py")
    checks = [
        {"id": "python", "label": "Python", "ok": True,
         "detail": sys.executable + f" (Python {sys.version.split()[0]})"},
        {"id": "ffmpeg", "label": "ffmpeg", "ok": bool(_ffmpeg_path()),
         "detail": _ffmpeg_path() or "chưa có — bấm Tải ffmpeg"},
        {"id": "capcut_dir", "label": "Thư mục pipeline capcut-tts", "ok": bool(cap_dir),
         "detail": cap_dir or ("không tìm thấy. Đã kiểm tra: " + "; ".join(cands))},
        {"id": "pipeline_files", "label": "File pipeline (reup.py, reup_sub.py, stt_words.py, autodetect_frost.py)",
         "ok": bool(cap_dir) and all(files.values()),
         "detail": ("đủ" if all(files.values()) else "thiếu: " + ", ".join(k for k, v in files.items() if not v)) if cap_dir else "chưa có thư mục pipeline"},
        {"id": "sdk", "label": "CapCut SDK (capcut_tts_api, cho STT)", "ok": sdk_ok, "detail": sdk_detail},
        {"id": "git", "label": "git (để tải SDK)", "ok": bool(shutil.which("git")),
         "detail": shutil.which("git") or "chưa có git"},
        {"id": "kokoro", "label": "Kokoro (tùy chọn, chỉ khi dùng giọng Ngọc Huyền)",
         "ok": bool(kokoro_script and os.path.isfile(kokoro_script)),
         "detail": (kokoro_script if kokoro_script and os.path.isfile(kokoro_script)
                    else "chưa cấu hình — vào Cài đặt -> Lồng tiếng -> Thư mục kokoro-vi")},
    ]
    return {"checks": checks, "capcut_dir": cap_dir, "installing": INSTALLING}


def _install_deps():
    root = paths.REPO_ROOT
    for req in ("backend/requirements.txt", "cli/requirements.txt"):
        p = os.path.join(root, req)
        if os.path.isfile(p):
            _run([sys.executable, "-m", "pip", "install", "-r", p])


def _install_sdk():
    cap_dir, _ = paths.resolve_capcut_dir()
    if not cap_dir:
        cap_dir = os.path.join(paths.REPO_ROOT, "cli")
    up = os.path.join(cap_dir, "upstream")
    if not os.path.isdir(up):
        if not shutil.which("git"):
            raise RuntimeError("Chưa có git — cài git trước rồi bấm lại")
        _run(["git", "clone", "https://github.com/K07VN/capcut-tts-api", up])
    else:
        _log(f"Đã có {up}, bỏ qua clone")
    _run([paths.capcut_py(), "-m", "pip", "install", up])


def _install_ffmpeg():
    system = platform.system()
    if system == "Linux":
        raise RuntimeError("Linux: chạy lệnh hệ thống: sudo apt install ffmpeg (hoặc brew trên Mac)")
    import urllib.request
    bindir = paths.repo_bin_dir()
    os.makedirs(bindir, exist_ok=True)
    if system == "Darwin":
        url, member = "https://evermeet.cx/ffmpeg/getrelease/zip", "ffmpeg"
    else:
        url, member = ("https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip", "ffmpeg.exe")
    zpath = os.path.join(bindir, "ffmpeg_dl.zip")
    _log(f"Tải {url} ...")
    urllib.request.urlretrieve(url, zpath)
    with zipfile.ZipFile(zpath) as z:
        names = [n for n in z.namelist() if n.endswith("/bin/" + member) or n == member]
        if not names:
            raise RuntimeError("Không tìm thấy ffmpeg trong file tải về")
        data = z.read(names[0])
    out = os.path.join(bindir, member)
    with open(out, "wb") as f:
        f.write(data)
    if system != "Windows":
        os.chmod(out, 0o755)
    os.remove(zpath)
    _log(f"Đã lưu {out}")


_STEPS = {"deps": _install_deps, "sdk": _install_sdk, "ffmpeg": _install_ffmpeg}


def install(step: str):
    """Chạy 1 bước cài đặt trong thread nền. Trả về True nếu bắt đầu chạy."""
    global INSTALLING
    if INSTALLING:
        return False
    if step not in _STEPS:
        raise ValueError(f"Bước không hợp lệ: {step}")
    INSTALLING = True
    LOG.clear()
    _log(f"Bắt đầu bước: {step}")

    def _worker():
        global INSTALLING
        try:
            _STEPS[step]()
            _log("HOÀN TẤT")
        except Exception as e:
            _log(f"LỖI: {e}")
        finally:
            INSTALLING = False

    threading.Thread(target=_worker, daemon=True).start()
    return True
