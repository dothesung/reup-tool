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

## Cài đặt (v1.2, trang ⚙ Cài đặt)

Cấu hình chung áp dụng cho mọi job mới — đè lên preset cho các mục trùng nhau.
Lưu tại `settings.json` ở root repo (đã gitignore, không push lên GitHub).
Mẫu: `settings.example.json`.

| Nhóm | Mục | Tác dụng thật |
|---|---|---|
| Thương hiệu & mặc định | Tên nav, preset mặc định, ngôn ngữ STT | Hiện ở nav; Dashboard preselect preset |
| Pipeline & xuất bản | Chế độ final/draft, auto up Drive, share link | `--draft`, `--no-upload`, `--share` |
| Lồng tiếng | Engine, số luồng TTS, burn sub | `--engine`, `--jobs`, `--with-sub` |
| Khung 9:16 & che | v916, chữ/màu khung, frost alpha, frost auto | `--v916`, `--banner-*`, `--frost-alpha`, `--frost-auto` |
| Tích hợp & Key | Nexray URL, Facebook Page ID/Token | Nexray qua env `NEXRAY_URL`; token FB lưu che (•••• + 4 ký tự cuối), để trống = giữ nguyên — dùng cho tính năng Đăng Fanpage sắp ra mắt. Drive dùng OAuth qua hatch CLI, không cần key. |

API: `GET /api/v1/settings` (che secret), `PUT /api/v1/settings` (field secret trống = giữ nguyên).

## Bản quyền & dùng thử (v1.4)

- Chưa có key: dùng thử 7 ngày / 10 video (tự bắt đầu khi mở app lần đầu).
- Hết trial: tạo job bị chặn (HTTP 402) — nhập key ở thanh license trên Dashboard.
- Key do người bán tạo bằng `cli/gen_key.py` + file `license_private.pem`
  (chỉ người bán giữ, KHÔNG commit): personal 1 máy vĩnh viễn, pro 3 máy,
  team 5 máy, thuê bao theo tháng (key chứa hạn, kích hoạt gắn máy).
- Tool chỉ chứa public key để verify — không tự ký key giả được.
- Người bán test: `REUP_LICENSE_DEV=1` để bypass.

## Dịch máy (v1.4)

- Nút "🤖 Dịch máy từ sub gốc" trong Editor: dịch resub.srt (chữ gốc) thành
  sub_vi.srt nháp qua Google gtx, fallback MyMemory miễn phí.
- Nhập email vào Cài đặt → Key & Tích hợp → "Email cho MyMemory" để tăng
  quota dịch lên 50.000 ký tự/ngày (Google hay bị chặn IP datacenter).
- Bản dịch máy luôn thô — sửa tay trong bảng trước khi bấm Chạy tiếp.
  Cue nào dịch lỗi sẽ giữ nguyên chữ gốc và báo số cue lỗi.

## Hoàn thiện v1.5

- **Editor dạng tab:** Frost / Cover | Sub tiếng Việt (số cue) — hết trang dài.
  Nút Lưu sub + frost luôn ở dưới cùng, không phụ thuộc tab.
- **Đăng Fanpage:** job done có nút "📘 Đăng Fanpage" trên Dashboard — đăng
  final.mp4 + caption.txt qua Graph API (cần Page ID + token trong Cài đặt).
  Chưa nhập token → báo rõ, không đăng lén.
- **Giọng CapCut:** Cài đặt → Lồng tiếng → chọn engine CapCut sẽ hiện ô ID giọng
  (gợi ý BV560 Alex Đại Đế, BV074 Cô Gái Hoạt Ngôn; trống = mặc định SDK).
- **Giới hạn job song song:** Cài đặt → Pipeline → số job chạy cùng lúc (1–5,
  mặc định 2); job vượt sẽ hiện "queued" chờ slot, tránh ngốn RAM.
- **Job sống qua restart:** JOB_STATE lưu xuống jobs_state.json (gitignored);
  job đang chạy dở khi backend restart sẽ về trạng thái "interrupted".
