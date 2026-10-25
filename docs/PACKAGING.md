# Đóng gói Reup Tool chạy trên Windows & macOS (kế hoạch v1.8)

## 1. Kiến trúc đóng gói (chọn phương án này)

App hiện tại = **2 tiến trình** (backend FastAPI :8000 + Vite dev :5173). Để đóng
gói, gộp thành **1 tiến trình duy nhất**:

```
ReupTool/                      <- thư mục app sau khi đóng gói
  ReupTool (exe / binary)      <- launcher.py: chạy uvicorn + mở trình duyệt
  ffmpeg / ffmpeg.exe          <- bản static, CI tải riêng (GPL)
  app/                         <- backend Python (PyInstaller đóng gói)
  frontend/dist/               <- UI đã build (backend tự serve ở :8000)
  presets/
  settings.json, license.json, jobs_state.json  <- dữ liệu người dùng
```

- **Công cụ:** PyInstaller, mode **one-dir** (không one-file — torch/Kokoro load
  model nhanh hơn, ít bị antivirus chặn).
- **Không build chéo:** PyInstaller chỉ build cho hệ điều hành đang chạy. VM Linux
  này KHÔNG build được bản Win/Mac → dùng **GitHub Actions**
  (`.github/workflows/build.yml`): push lên main là build cả 2, tải artifact về.
- **Bước đã làm xong trong v1.8:**
  - `backend/app/main.py` tự serve `frontend/dist` khi có (UI chạy ở :8000).
  - `launcher.py`: chạy uvicorn + tự mở trình duyệt.
  - `reup-tool.spec`: spec PyInstaller (datas: app/, frontend/dist, presets).
  - `.github/workflows/build.yml`: build Win + Mac, bundle ffmpeg static.

## 2. Những gì CHƯA đóng gói được / cần custom theo nền tảng

| Hạng mục | Trạng thái | Cần custom |
|---|---|---|
| ffmpeg | CI tải bản static riêng cho Win/Mac | Windows: `ffmpeg.exe`; Mac: `ffmpeg` (evermeet) |
| Giọng Kokoro (torch + model ~vài trăm MB) | **Không đóng gói** (quá nặng) | App tải model lần đầu khi chạy; cần code "first-run download" + hiển thị tiến trình |
| CapCut TTS SDK | Chạy trên cả Win/Mac (Python) | Kiểm tra lại trên máy thật |
| Tăng tốc phần cứng | Preset chỉ ghi chú (videotoolbox) | Win: d3d11va/dxva2/nvenc; Mac: videotoolbox; Linux: vaapi — cần map theo OS trong worker |
| Đường dẫn dữ liệu | Đang dùng `~/workspace/...` (VM) | Win: `%APPDATA%/ReupTool`; Mac: `~/Library/Application Support/ReupTool` — cần biến JOBS_DIR theo OS |
| Chữ ký / Gatekeeper | Chưa có | Mac: app chưa ký → user phải chuột phải → Open lần đầu; muốn hết cảnh báo cần Apple Developer ID ($99/năm) + notarize. Win: SmartScreen cảnh báo tương tự nếu chưa ký (EV cert đắt) — phát hành dạng zip portable trước |
| Auto-update | Chưa có | Giai đoạn sau: kiểm tra version trên GitHub Releases, tải bản mới |

## 3. Chức năng hiện có (v1.0 → v1.8) & điểm cần custom

| Nhóm | Chức năng | Custom được ở đâu |
|---|---|---|
| Pipeline | Nhập link Douyin/YouTube → STT → sub gốc → dịch → lồng tiếng → burn 9:16 → up Drive | Preset, Cài đặt → Pipeline |
| Editor | Sửa sub, đo frost/cover tự động, frame preview | Editor tab Frost / Sub |
| Lồng tiếng | Kokoro Ngọc Huyền (mặc định) hoặc CapCut BV560/BV074/BV421 | Cài đặt → Lồng tiếng |
| Khung & che | v916 (square/black/blur), banner top/bottom, frost alpha, cover alpha | Cài đặt → Khung & Che |
| Dịch | Dịch máy miễn phí (Google/MyMemory) — v1.4; **Dịch AI (v1.8)** | Cài đặt → tab AI |
| Caption | Mẫu tiêu đề/hashtag — v1.6; **Caption AI theo job (v1.8)** | Editor → tab AI Caption (per-job), Cài đặt → Pipeline (mẫu chung) |
| Đăng bài | Đăng Fanpage tự động (Graph API) | Cài đặt → Key & Tích hợp |
| License | Trial 7 ngày/10 video, key Ed25519, 3 gói | Trang Admin (người bán) |
| AI (v1.8) | Dịch phụ đề + viết caption qua API chuẩn OpenAI-compatible | Cài đặt → tab AI: provider, base_url, api_key, model |

## 4. AI provider — cách dùng (v1.8)

Cài đặt → tab AI → bật "Bật tính năng AI" → chọn nhà cung cấp:

| Provider | Base URL tự điền | Model ví dụ |
|---|---|---|
| DeepSeek | https://api.deepseek.com/v1 | deepseek-chat |
| OpenAI | https://api.openai.com/v1 | gpt-4o-mini |
| OpenRouter | https://openrouter.ai/api/v1 | (nhập tay, vd openai/gpt-4o-mini) |
| Gemini | https://generativelanguage.googleapis.com/v1beta/openai/ | gemini-2.0-flash |
| Tùy chỉnh | nhập tay | LM Studio (`http://localhost:1234/v1`), Ollama, proxy riêng |

- Nút **"Kiểm tra kết nối"** gọi 1 câu ngắn để xác nhận key/model chạy được.
- Key lưu local, API chỉ hiện •••• + 4 ký tự cuối; để trống = giữ key cũ.
- **Dịch AI:** Editor → Sub → "✨ Dịch bằng AI" (dịch có ngữ cảnh, giữ đúng số
  cue; nếu LLM trả lệch số dòng sẽ báo lỗi và KHÔNG ghi đè).
- **Caption AI:** Editor → tab AI Caption → "Viết bằng AI" → sửa lại → "Áp dụng
  cho job này" (lưu `caption_override.json` trong workdir, chỉ áp cho job đó,
  không đổi mẫu chung).
