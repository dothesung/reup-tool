# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — đóng gói Reup Tool thành app chạy được trên Win/Mac.

Chạy trên máy đích (KHÔNG build chéo từ Linux):
  Windows:  pip install -r backend/requirements.txt pyinstaller
            pyinstaller reup-tool.spec
  macOS:    tương tự (ra dist/ReupTool.app khi dùng windowed=True)

Lưu ý:
- Mode one-dir (không one-file): torch/Kokoro load model nhanh hơn, ít lỗi antivirus.
- ffmpeg KHÔNG đóng gói trong spec: CI tải bản static (gpl) riêng và copy vào dist/.
- Model Kokoro (~vài trăm MB) KHÔNG đóng gói: app tải lần đầu khi chạy (xem docs/PACKAGING.md).
- license_private.pem KHÔNG BAO GIỜ đóng gói (chỉ máy người bán có).
"""
import os

ROOT = os.path.dirname(os.path.abspath(SPEC))
DIST = os.path.join(ROOT, "frontend", "dist")

a = Analysis(
    [os.path.join(ROOT, "launcher.py")],
    pathex=[os.path.join(ROOT, "backend")],
    binaries=[],
    datas=[
        (os.path.join(ROOT, "backend", "app"), "app"),
        (DIST, "frontend/dist"),
        (os.path.join(ROOT, "presets"), "presets"),
    ],
    hiddenimports=["uvicorn.logging", "uvicorn.loops", "uvicorn.loops.auto",
                   "uvicorn.protocols", "uvicorn.protocols.http",
                   "uvicorn.protocols.http.auto", "uvicorn.protocols.websockets",
                   "uvicorn.protocols.websockets.auto", "uvicorn.lifespan",
                   "uvicorn.lifespan.on", "app.services.llm"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="ReupTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # backend in log ra console; bản Mac dùng windowed=False để thấy log khi lỗi
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=False, upx_exclude=[], name="ReupTool",
)
