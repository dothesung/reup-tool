#!/usr/bin/env python3
"""Launcher cho bản đóng gói Reup Tool: chạy backend + mở trình duyệt.

Dùng làm entry point cho PyInstaller (xem reup-tool.spec).
Khi chạy từ source: python3 launcher.py  (tương đương run.sh + mở browser)
"""
import os
import sys
import threading
import time
import webbrowser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

import uvicorn


def _open_browser():
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000/")


if __name__ == "__main__":
    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="warning")
