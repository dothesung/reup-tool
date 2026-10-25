#!/bin/bash
# Setup Reup Tool trên localhost (macOS/Linux)
set -e
echo "== Reup Tool setup =="
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -r backend/requirements.txt
echo "Cai ffmpeg (neu chua co)..."
which ffmpeg || brew install ffmpeg 2>/dev/null || sudo apt install -y ffmpeg 2>/dev/null || echo "Hay cai ffmpeg tay"
echo "Tai Kokoro model (1 lan)..."
python3 -c "from huggingface_hub import snapshot_download; snapshot_download('kokoro-vi')" 2>/dev/null || echo "Kokoro model: tai khi chay lan dau"
echo "Xong. Chay ./run.sh"
