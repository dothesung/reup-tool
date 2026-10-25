"""Reup Tool — Đăng video lên Facebook Fanpage qua Graph API.

Dùng Page ID + Page Access Token trong Cài đặt (tab Key & Tích hợp).
Video đăng ở chế độ published, mô tả lấy từ caption.txt (tiêu đề + sub Việt).
Không giữ token trong code — token chỉ nằm trong settings.json local.
"""
import os

import httpx

GRAPH_VIDEO = "https://graph-video.facebook.com/v21.0"


def post_video(page_id: str, token: str, video_path: str, caption: str = "") -> dict:
    """Đăng video, trả về {'id': ...} của FB. Raise RuntimeError khi FB báo lỗi."""
    if not page_id or not token:
        raise RuntimeError("Chưa nhập Facebook Page ID / Access Token trong Cài đặt")
    if not os.path.exists(video_path):
        raise RuntimeError(f"Không tìm thấy video: {video_path}")
    with open(video_path, "rb") as f:
        files = {"source": (os.path.basename(video_path), f, "video/mp4")}
        data = {"access_token": token, "description": caption[:5000],
                "published": "true"}
        r = httpx.post(f"{GRAPH_VIDEO}/{page_id}/videos",
                       data=data, files=files, timeout=600)
    try:
        out = r.json()
    except Exception:
        raise RuntimeError(f"Facebook trả về không phải JSON (HTTP {r.status_code})")
    if "error" in out:
        e = out["error"]
        raise RuntimeError(f"Facebook lỗi {e.get('code')}: {e.get('message')}")
    if "id" not in out:
        raise RuntimeError(f"Facebook trả về lạ: {str(out)[:300]}")
    return out
