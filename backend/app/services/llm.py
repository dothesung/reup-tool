"""Reup Tool — LLM client chuẩn OpenAI-compatible (chat completions).

Dùng cho: dịch phụ đề bằng AI, viết tiêu đề/hashtag.
Nhà cung cấp tùy chỉnh trong Cài đặt → tab AI: base_url + api_key + model.
Preset sẵn: OpenAI, DeepSeek, OpenRouter, Gemini (chế độ tương thích OpenAI),
hoặc base_url tùy chỉnh bất kỳ (LM Studio, Ollama, proxy riêng...).
"""
import httpx

PROVIDERS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "custom": "",
}


def chat(base_url: str, api_key: str, model: str, messages: list,
         temperature: float = 0.3, timeout: int = 120) -> str:
    """Gọi chat completions, trả về nội dung text. Raise RuntimeError khi lỗi."""
    if not base_url or not api_key or not model:
        raise RuntimeError("Chưa cấu hình LLM trong Cài đặt → tab AI (base_url, api_key, model)")
    url = base_url.rstrip("/") + "/chat/completions"
    # trust_env=False: không đi qua proxy của môi trường (tránh lộ API key
    # qua proxy, và tránh lỗi proxy env hỏng trên một số máy/VM)
    r = httpx.post(url, json={
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }, headers={"Authorization": f"Bearer {api_key}"}, timeout=timeout,
        trust_env=False)
    try:
        out = r.json()
    except Exception:
        raise RuntimeError(f"LLM trả về không phải JSON (HTTP {r.status_code})")
    if "error" in out:
        e = out["error"]
        raise RuntimeError(f"LLM lỗi: {e.get('message', e)}")
    try:
        return out["choices"][0]["message"]["content"].strip()
    except Exception:
        raise RuntimeError(f"LLM trả về lạ: {str(out)[:300]}")


TRANSLATE_SYSTEM = (
    "Bạn là dịch giả phụ đề phim Trung -> Việt. Dịch tự nhiên như người Việt nói, "
    "giữ đúng số dòng, mỗi dòng bắt đầu bằng số thứ tự và dấu chấm. "
    "Không thêm, không bớt, không giải thích, không gộp dòng. "
    "Tên riêng giữ nguyên hoặc phiên âm quen thuộc."
)


def translate_cues_ai(cues, llm: dict) -> tuple:
    """Dịch cues bằng LLM. Trả về (cues_mới, model). Raise khi số dòng lệch."""
    numbered = "\n".join(f"{i + 1}. {c.get('text', '')}" for i, c in enumerate(cues))
    content = chat(llm["base_url"], llm["api_key"], llm["model"], [
        {"role": "system", "content": TRANSLATE_SYSTEM},
        {"role": "user", "content": numbered},
    ])
    out = []
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Bỏ số thứ tự đầu dòng: "1. ..." hoặc "1: ..."
        for sep in (". ", ": ", ".", ":"):
            if line.split(sep, 1)[0].strip().isdigit() and len(line.split(sep, 1)) == 2:
                line = line.split(sep, 1)[1].strip()
                break
        out.append(line)
    if len(out) != len(cues):
        raise RuntimeError(
            f"LLM trả {len(out)} dòng nhưng cần {len(cues)} dòng — không ghi đè để tránh lệch sub")
    return [{**c, "text": t} for c, t in zip(cues, out)], llm["model"]


CAPTION_SYSTEM = (
    "Bạn là người viết tiêu đề video ngắn cho Fanpage Việt Nam. "
    "Trả về đúng 2 dòng, không giải thích:\n"
    "Dòng 1: TIÊU ĐỀ: <tiêu đề dưới 60 ký tự, gây tò mò, đúng nội dung>\n"
    "Dòng 2: HASHTAG: <#tag1 #tag2 ... tối đa 8 hashtag, không dấu, viết liền>"
)


def write_caption(orig_title: str, cue_texts: list, llm: dict) -> dict:
    """Viết tiêu đề + hashtag từ nội dung sub. Trả về {title, hashtags}."""
    sample = "\n".join(cue_texts[:30])
    content = chat(llm["base_url"], llm["api_key"], llm["model"], [
        {"role": "system", "content": CAPTION_SYSTEM},
        {"role": "user", "content": f"Tiêu đề gốc: {orig_title}\nNội dung:\n{sample}"},
    ])
    title, hashtags = orig_title, ""
    for line in content.split("\n"):
        line = line.strip()
        if line.upper().startswith("TIÊU ĐỀ:"):
            title = line.split(":", 1)[1].strip()
        elif line.upper().startswith("HASHTAG:"):
            hashtags = line.split(":", 1)[1].strip()
    return {"title": title, "hashtags": hashtags, "model": llm["model"]}
