#!/bin/bash
# Chay Reup Tool backend
cd "$(dirname "$0")/backend" || exit 1
../.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 2>/dev/null || python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
