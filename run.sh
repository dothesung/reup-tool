#!/bin/bash
# Chay Reup Tool: backend (:8000) + frontend dev (:5173).
# Lan dau tren may moi:
#   python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
#   cd frontend && npm install && cd ..
# Sau do mo trang Thiet lap (#/setup) trong app de tai/cai phu thuoc con thieu.
cd "$(dirname "$0")" || exit 1

PY="../.venv/bin/python"
[ -x "$PY" ] || PY="python3"

start_backend() {
  cd backend || exit 1
  $PY -m uvicorn app.main:app --host 0.0.0.0 --port 8000 2>/dev/null || python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
}

if [ -d "frontend/dist" ]; then
  # Da build production: backend tu serve UI o :8000, chi can 1 tien trinh
  start_backend
else
  # Dev: chay song song backend + vite
  (start_backend) &
  BPID=$!
  cd frontend || exit 1
  (npm run dev) &
  FPID=$!
  echo "Backend :8000 (pid $BPID) + Frontend :5173 (pid $FPID). Mo http://localhost:5173"
  echo "Nhan Ctrl+C de dung ca hai."
  trap "kill $BPID $FPID 2>/dev/null" INT TERM
  wait
fi
