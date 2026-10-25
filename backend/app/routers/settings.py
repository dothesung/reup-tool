"""Reup Tool — Cài đặt hệ thống (v1.2).

Lưu tại settings.json ở root repo (gitignore — chứa key).
GET luôn che secret (chỉ hiện 4 ký tự cuối). PUT: field secret để trống = giữ nguyên.
Settings là cấu hình chung, đè lên preset cho các key trùng nhau (xem merge_settings
ở routers/jobs.py); worker truyền flag tương ứng sang reup.py.
"""
import json
import os
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1", tags=["settings"])

SETTINGS_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "settings.json"))
EXAMPLE_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "settings.example.json"))

# Secret: không bao giờ trả full qua API
SECRET_FIELDS = {"facebook_page_token", "llm_api_key"}

DEFAULTS = {
    # Thương hiệu (hiện ở nav, phục vụ thương mại hóa)
    "brand_name": "Reup Tool",
    "admin_contact": "0981228722",  # Zalo/SĐT liên hệ mua key (hiện ở Dashboard + footer)
    # Chung
    "default_preset": "review_phim",
    "default_src_lang": "zh-CN",
    "auto_upload": True,        # False -> reup.py --no-upload
    "share_drive_link": False,  # True -> reup.py --share (link public)
    "output_mode": "final",    # final | draft (-> --draft: 720x1280, ultrafast)
    # Tiêu đề & hashtag (caption.txt + mô tả khi đăng Fanpage)
    "title_template": "{title}",  # {title} = tiêu đề gốc
    "hashtags": "",
    # Lồng tiếng
    "engine": "kokoro",        # kokoro | capcut
    "jobs": 4,                  # số TTS song song (1-8)
    "capcut_voice": "",         # ID giọng CapCut khi engine=capcut (trống = mặc định SDK)
    "max_parallel_jobs": 2,     # số job pipeline chạy cùng lúc (vượt thì xếp hàng)
    "with_sub": False,          # True -> burn sub Việt lên video
    # Khung 9:16 & che
    "v916": "square",           # auto | square | black | blur | off
    "banner_top": "REVIEW PHIM HAY",
    "banner_bottom": "PHIM HAY MỖI NGÀY",
    "banner_color": "FFCC00",
    "frost_alpha": 0.2,         # độ mờ thanh che sub cũ
    "frost_auto": False,        # True -> tự phát hiện vùng sub (khi không set tay)
    # Tích hợp
    "nexray_url": "",           # để trống = dùng mặc định của reup.py
    "translate_email": "",      # email cho MyMemory (tăng quota dịch miễn phí)
    "facebook_page_id": "",
    "facebook_page_token": "",
    # AI (chuẩn OpenAI-compatible chat completions)
    "llm_enabled": False,
    "llm_provider": "deepseek",   # openai | deepseek | openrouter | gemini | custom
    "llm_base_url": "",
    "llm_api_key": "",
    "llm_model": "",
}


def load_settings() -> dict:
    """Đọc settings thật (kể cả secret) — chỉ dùng nội bộ (worker)."""
    merged = dict(DEFAULTS)
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH) as f:
                merged.update(json.load(f) or {})
        except Exception:
            pass
    return merged


def public_settings() -> dict:
    """Bản che secret để trả qua API."""
    out = load_settings()
    for k in SECRET_FIELDS:
        v = out.get(k) or ""
        out[k] = ("••••" + v[-4:]) if len(v) > 4 else ("••••" if v else "")
    out["_secrets_saved"] = {k: bool(load_settings().get(k)) for k in SECRET_FIELDS}
    return out


@router.get("/settings")
def get_settings():
    return public_settings()


class SettingsSave(BaseModel):
    brand_name: Optional[str] = None
    admin_contact: Optional[str] = None
    default_preset: Optional[str] = None
    default_src_lang: Optional[str] = None
    auto_upload: Optional[bool] = None
    share_drive_link: Optional[bool] = None
    output_mode: Optional[str] = None
    title_template: Optional[str] = None
    hashtags: Optional[str] = None
    engine: Optional[str] = None
    jobs: Optional[int] = None
    capcut_voice: Optional[str] = None
    max_parallel_jobs: Optional[int] = None
    with_sub: Optional[bool] = None
    v916: Optional[str] = None
    banner_top: Optional[str] = None
    banner_bottom: Optional[str] = None
    banner_color: Optional[str] = None
    frost_alpha: Optional[float] = None
    frost_auto: Optional[bool] = None
    nexray_url: Optional[str] = None
    translate_email: Optional[str] = None
    facebook_page_id: Optional[str] = None
    facebook_page_token: Optional[str] = None
    llm_enabled: Optional[bool] = None
    llm_provider: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None


@router.put("/settings")
def save_settings(body: SettingsSave):
    cur = load_settings()
    data = body.dict(exclude_none=True)
    # Secret để trống (hoặc giá trị đã che) = giữ nguyên
    for k in SECRET_FIELDS:
        v = data.get(k)
        if not v or v.startswith("••"):
            data.pop(k, None)
    # Validate nhẹ
    if data.get("output_mode") not in (None, "final", "draft"):
        data["output_mode"] = "final"
    if data.get("engine") not in (None, "kokoro", "capcut"):
        data["engine"] = "kokoro"
    if data.get("v916") not in (None, "auto", "square", "black", "blur", "off"):
        data["v916"] = "square"
    if data.get("jobs") is not None:
        data["jobs"] = max(1, min(8, int(data["jobs"])))
    if data.get("max_parallel_jobs") is not None:
        data["max_parallel_jobs"] = max(1, min(5, int(data["max_parallel_jobs"])))
    if data.get("frost_alpha") is not None:
        data["frost_alpha"] = max(0.05, min(0.9, float(data["frost_alpha"])))
    cur.update(data)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(cur, f, ensure_ascii=False, indent=1)
    return public_settings()


@router.post("/settings/llm-test")
def llm_test():
    """Kiểm tra kết nối LLM: gọi 1 câu ngắn, trả về đúng 'OK' nếu chạy."""
    from app.services import llm as llmsvc
    from app.services.llm import PROVIDERS
    import time
    st = load_settings()
    base = st.get("llm_base_url") or PROVIDERS.get(st.get("llm_provider", ""), "")
    t0 = time.time()
    try:
        reply = llmsvc.chat(base, st.get("llm_api_key", ""), st.get("llm_model", ""), [
            {"role": "user", "content": "Trả lời đúng 1 từ: OK"},
        ], timeout=60)
    except RuntimeError as e:
        from fastapi import HTTPException
        raise HTTPException(400, str(e))
    return {"ok": True, "model": st.get("llm_model", ""),
            "reply": reply[:100], "ms": int((time.time() - t0) * 1000)}
