#!/bin/bash
# Chay Reup Tool
source .venv/bin/activate 2>/dev/null || true
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000 (tuan 2)"
python3 backend/app/main.py
