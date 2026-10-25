# Reup Tool — Localhost Video Reup Pipeline

Tool chạy trên localhost để reup video Douyin/YouTube → lồng tiếng Việt → 9:16 → up Drive.

## Tính năng
- Tải video trực tiếp (yt-dlp, không 403)
- STT → Dịch → Dub giọng Ngọc Huyền (Kokoro)
- Frost/cover tự động phân biệt text cố định vs subtitle
- Burn 9:16 (square/black/blur) + banner
- Hardware encode (VideoToolbox/NVENC)
- Giao diện web + API + CLI

## Cài đặt nhanh

```bash
git clone https://github.com/dothesung/reup-tool.git
cd reup-tool
./setup.sh
./run.sh
# Mở http://localhost:3000
```

## Cấu trúc
```
backend/   # FastAPI
frontend/  # React + Vite
cli/       # CLI (tương thích reup.py cũ)
presets/   # Preset cấu hình
docs/      # Tài liệu
```

## License
Private — chỉ dùng nội bộ.
