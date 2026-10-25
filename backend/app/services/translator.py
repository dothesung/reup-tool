"""Reup Tool — Dịch máy phụ đề (bản nháp để sửa tay, không thay người dịch).

Engine miễn phí, thử theo thứ tự:
1. Google gtx (không key) — hay bị chặn IP datacenter (302/captcha).
2. MyMemory (không key, quota ẩn danh thấp; kèm email trong Cài đặt
   -> translate_email để tăng quota lên 50.000 ký tự/ngày).
Engine nào dịch được cue nào thì lấy cue đó; cuối cùng trả về engine đã dùng
nhiều nhất + cảnh báo rõ ràng nếu có cue lỗi (giữ nguyên chữ gốc).
Về sau có thể thêm engine AI có key (OpenAI/Gemini) cho chất lượng cao hơn.
"""
import json
import urllib.parse
import urllib.request

TIMEOUT = 20


def _google(text: str, src: str) -> str:
    q = urllib.parse.quote(text)
    url = ("https://translate.googleapis.com/translate_a/single"
           f"?client=gtx&sl={src}&tl=vi&dt=t&q={q}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = json.load(r)
    parts = [seg[0] for seg in (data[0] or []) if seg and seg[0]]
    out = "".join(parts).strip()
    if not out or out == text:
        raise RuntimeError("Google không trả bản dịch")
    return out


def _mymemory(text: str, src: str, email: str = "") -> str:
    q = urllib.parse.quote(text)
    url = ("https://api.mymemory.translated.net/get"
           f"?q={q}&langpair={src}|vi-VN")
    if email:
        url += f"&de={urllib.parse.quote(email)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = json.load(r)
    if data.get("responseStatus") != 200:
        raise RuntimeError(f"MyMemory lỗi: {data.get('responseDetails', '')[:120]}")
    out = (data.get("responseData", {}).get("translatedText") or "").strip()
    if not out or out == text or "MYMEMORY WARNING" in out:
        raise RuntimeError("MyMemory không trả bản dịch (có thể hết quota)")
    return out


def translate_cues(cues, src: str = "zh-CN", email: str = ""):
    """Dịch từng cue. Trả về (cues_mới, engine_chính, số_cue_lỗi)."""
    out = []
    used = {"google": 0, "mymemory": 0}
    errors = 0
    for c in cues:
        txt = (c.get("text") or "").strip()
        if not txt:
            out.append(c)
            continue
        done = None
        for name, fn in (("google", lambda: _google(txt, src)),
                         ("mymemory", lambda: _mymemory(txt, src, email))):
            try:
                done = fn()
                used[name] += 1
                break
            except Exception:
                continue
        if done is None:
            errors += 1
            out.append(c)  # giữ chữ gốc, user sửa tay
        else:
            out.append({**c, "text": done})
    engine = "google" if used["google"] >= used["mymemory"] else "mymemory"
    return out, engine, errors
