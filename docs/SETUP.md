# Setup

## Yêu cầu
- Python 3.11+
- ffmpeg (có VideoToolbox trên macOS)
- Node 18+ (cho frontend, tuần 2)

## Chạy
```bash
./setup.sh
./run.sh
```

## API
- GET /health
- POST /jobs {url, preset, src_lang}
- GET /jobs
- GET /jobs/{id}
- PATCH /jobs/{id}
