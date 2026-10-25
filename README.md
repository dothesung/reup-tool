# Reup Tool v1.0 — Localhost Video Reup Pipeline

Tool chạy trên localhost để reup video Douyin/YouTube → lồng tiếng Việt → 9:16 → up Drive.

## Tính năng
- Tải video trực tiếp (yt-dlp, không 403)
- STT → Dịch → Dub giọng Ngọc Huyền (Kokoro)
- **Frost Editor kéo-thả** trên khung hình (không đo tay)
- Tự động phân biệt text cố định vs subtitle
- Burn 9:16 (square/black/blur) + banner
- Hardware encode (VideoToolbox/NVENC)
- Dashboard + batch queue + preset manager
- Giao diện web + API + CLI

## Chạy nhanh

```bash
git clone https://github.com/dothesung/reup-tool.git
cd reup-tool
./setup.sh
./run.sh            # Backend :8000

# Terminal khác:
cd frontend && npm install && npm run dev   # Frontend :5173
```

Mở http://localhost:5173 — xem chi tiết trong [docs/HUONG_DAN.md](docs/HUONG_DAN.md).

## Cấu trúc
```
backend/   # FastAPI (jobs, editor, pipeline worker)
frontend/  # React + Vite (Dashboard, Editor, Preset)
cli/       # CLI (tương thích reup.py cũ)
presets/   # Preset cấu hình
docs/      # Tài liệu
```
