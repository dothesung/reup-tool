"""Reup Tool — phân giải đường dẫn pipeline, portable giữa các máy.

Vấn đề gốc: worker/editor hardcode ~/workspace/capcut-tts (chỉ có trên VM dev),
sang máy khác là lỗi [Errno 2] No such file or directory.

Thứ tự tìm thư mục capcut-tts:
  1. settings capcut_dir (user chỉ tay trong Cài đặt / Thiết lập)
  2. ~/workspace/capcut-tts (máy dev cũ, giữ tương thích job cũ)
  3. <repo>/cli (thư mục pipeline kèm theo repo — máy mới dùng cái này)
  4. ~/capcut-tts
Không tìm thấy -> trả None + danh sách đã kiểm tra, để API báo lỗi rõ ràng
thay vì Errno 2 khó hiểu.
"""
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
SETTINGS_PATH = os.path.join(REPO_ROOT, "settings.json")


def _load_settings_raw() -> dict:
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def resolve_capcut_dir() -> tuple:
    """Trả về (dir | None, candidates_đã_kiểm_tra).

    Nếu user đã chỉ capcut_dir trong Cài đặt nhưng đường dẫn đó không chứa
    reup.py thì KHÔNG fallback im lặng sang chỗ khác — trả None để báo lỗi
    rõ ràng (người chỉ sai cần biết mình chỉ sai).
    """
    st = _load_settings_raw()
    explicit = st.get("capcut_dir")
    if explicit:
        d = os.path.expanduser(explicit)
        if os.path.isfile(os.path.join(d, "reup.py")):
            return d, [d]
        return None, [d]
    cands = [
        os.path.expanduser("~/workspace/capcut-tts"),
        os.path.join(REPO_ROOT, "cli"),
        os.path.expanduser("~/capcut-tts"),
    ]
    for d in cands:
        if d and os.path.isfile(os.path.join(d, "reup.py")):
            return d, cands
    return None, cands


def jobs_dir() -> str:
    d, _ = resolve_capcut_dir()
    if d is None:
        raise RuntimeError(
            "Không tìm thấy thư mục pipeline capcut-tts (cần file reup.py). "
            "Vào trang Thiết lập để tải/cài phụ thuộc, hoặc vào Cài đặt -> "
            "Pipeline để chỉ đường dẫn thư mục capcut-tts.")
    return os.path.join(d, "jobs")


def capcut_py() -> str:
    """Python chạy các bước con của pipeline (STT...)."""
    st = _load_settings_raw()
    if st.get("capcut_py"):
        return os.path.expanduser(st["capcut_py"])
    vm_venv = "/home/hatch/workspace/.venvs/capcut/bin/python"
    if os.path.isfile(vm_venv):
        return vm_venv
    return sys.executable


def kokoro_env() -> dict:
    """Env cho engine kokoro (chỉ set khi user đã cấu hình)."""
    st = _load_settings_raw()
    env = {}
    if st.get("kokoro_py"):
        env["KOKORO_PY"] = os.path.expanduser(st["kokoro_py"])
    if st.get("kokoro_dir"):
        script = os.path.join(os.path.expanduser(st["kokoro_dir"]), "batch_synth.py")
        env["KOKORO_SCRIPT"] = script
    return env


def repo_bin_dir() -> str:
    return os.path.join(REPO_ROOT, "bin")
