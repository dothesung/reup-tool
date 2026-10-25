# Reup Tool — Hướng dẫn sử dụng v1.0

## Chạy tool

```bash
# Backend (cổng 8000)
cd reup-tool
./run.sh

# Frontend (cổng 5173) — terminal khác
cd reup-tool/frontend
npm install
npm run dev
```

Mở http://localhost:5173

## Quy trình 1 video

1. **Dashboard** → dán link Douyin/YouTube → chọn preset → **Tạo job**
2. Tool tự tải video + STT (1-3 phút) → trạng thái chuyển thành `waiting_sub`
3. Bấm **Sửa sub/frost** → sang trang Editor:
   - Xem frame video, kéo-thả chọn vùng frost (vàng) / cover (đỏ)
   - Hoặc bấm "Tự động phát hiện" để tool gợi ý vùng text
   - Sửa sub tiếng Việt trong bảng
   - Bấm **Lưu sub + frost**
4. Quay lại Dashboard → bấm **Chạy tiếp →** → tool dub + burn + up Drive
5. Khi xong, trạng thái `done`, bấm link **Drive ↗** để lấy video

## Preset

Vào tab **Preset** để sửa cấu hình:
- `v916`: square / black / blur
- `banner_top` / `banner_bottom`: chữ khung vàng
- `frost_alpha`: 0.2 (mặc định, mờ nhẹ)
- `cover_alpha`: 0.3
- `hwaccel`: videotoolbox (macOS) / nvenc (Windows NVIDIA) / để trống (CPU)

## Batch

Tạo nhiều job liên tiếp — mỗi job chạy độc lập, theo dõi trên Dashboard
(tự refresh mỗi 5 giây).

## API

- `GET /health`
- `POST /api/v1/pipeline/jobs` — tạo job
- `GET /api/v1/pipeline/jobs` — danh sách
- `POST /api/v1/pipeline/jobs/{id}/continue` — chạy tiếp sau khi sửa sub
- `GET /api/v1/jobs/{id}/frame?t=30` — frame video
- `GET/PUT /api/v1/jobs/{id}/subs` — sub Việt
- `GET/POST /api/v1/jobs/{id}/frost` — cấu hình frost
- `GET /api/v1/presets` — danh sách preset

## Lưu ý

- Audio không kiểm chứng được từ tool — nghe thử trước khi đăng.
- Frost tự động phát hiện đúng ~80% trường hợp; kiểm tra bằng mắt trước khi burn.
- Video dài >10 phút nên chia nhỏ hoặc chạy qua đêm.
