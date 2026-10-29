#!/usr/bin/env python3
"""Tu dong phat hien vung phu de (text trang) de tinh toa do frost.
Phuong phap: quet hang pixel trang tai cac frame giua cue (tu SRT),
tim dai y co mat do text cao ON DINH qua nhieu frame.
Ho tro: nhieu vi tri sub khac nhau, nhieu vung (vd: sub duoi + chu thich tren).
Usage: python3 autodetect_frost.py <video> <srt> [--out-y-only]
Output JSON: {"zones": [{"frost": "Y:H", ...}]}
"""
import sys, json, subprocess, tempfile, os, re
import cv2
import numpy as np

def parse_srt(p):
    cues = []
    txt = open(p, encoding="utf-8").read()
    for m in re.finditer(r"(\d+):(\d+):([\d.,]+)\s*-->\s*(\d+):(\d+):([\d.,]+)", txt):
        g = m.groups()
        t1 = int(g[0])*3600 + int(g[1])*60 + float(g[2].replace(",", "."))
        t2 = int(g[3])*3600 + int(g[4])*60 + float(g[5].replace(",", "."))
        cues.append((t1, t2))
    return cues

def main():
    video, srt = sys.argv[1], sys.argv[2]
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0", video],
        capture_output=True, text=True)
    vw, vh = map(int, pr.stdout.strip().split(","))
    SW = 640
    scale = vw / SW
    SH = int(vh / scale)

    cues = parse_srt(srt)
    # Lay toi da 15 cue cach deu, frame o giua cue
    step = max(1, len(cues) // 15)
    times = [(c[0] + c[1]) / 2 for c in cues[::step][:15]]

    # Dem pixel trang theo hang, cong don qua cac frame
    row_counts = np.zeros(SH, dtype=np.float32)
    n_ok = 0
    with tempfile.TemporaryDirectory() as td:
        for i, t in enumerate(times):
            fp = os.path.join(td, f"f{i}.png")
            r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t),
                "-i", video, "-frames:v", "1",
                "-vf", f"scale={SW}:-1", fp], capture_output=True)
            if r.returncode != 0:
                continue
            img = cv2.imread(fp)
            if img is None:
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Text trang co vien den: lay pixel rat trang
            _, bw = cv2.threshold(gray, 215, 255, cv2.THRESH_BINARY)
            ah = bw.shape[0]
            # Chi xet vung 45%-92% (bo nua tren + 8% day nhat: disclaimer/watermark)
            y0 = int(ah * 0.45)
            y1 = int(ah * 0.92)
            counts = (bw[y0:y1, :] > 0).sum(axis=1).astype(np.float32)
            # Chuan hoa theo chieu rong (loai anh huong do dai text)
            # (dam bao kich thuoc khop)
            if len(row_counts) != ah:
                row_counts = np.zeros(ah, dtype=np.float32)
                SH = ah
            rc = np.zeros(ah, dtype=np.float32)
            rc[y0:y1] = (counts > SW * 0.08).astype(np.float32)
            row_counts += rc
            n_ok += 1

    if n_ok == 0:
        print(json.dumps({"error": "khong doc duoc frame"}))
        return

    # Nguong: hang co text xuat hien o >= 40% so frame mau
    thresh = n_ok * 0.4
    active = row_counts >= thresh

    # Tim cac dai y lien tuc
    zones = []
    in_run = False
    start = 0
    for y in range(SH):
        if active[y] and not in_run:
            in_run, start = True, y
        elif not active[y] and in_run:
            in_run = False
            if y - start >= 8:  # dai >= 8px (scaled) moi tinh
                zones.append((start, y))
    if in_run and SH - start >= 8:
        zones.append((start, SH))

    # Gop cac dai gan nhau (< 15px)
    merged = []
    for s, e in zones:
        if merged and s - merged[-1][1] < 15:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))

    out = []
    for s, e in merged:
        # Map ve toa do goc, mo rong 8px moi ben
        fy = int(s * scale) - 8
        fh = int((e - s) * scale) + 16
        fy = max(0, fy)
        out.append({"frost": f"{fy}:{fh}",
                    "y_src": [int(s*scale), int(e*scale)],
                    "frames_hit": int(row_counts[s:e].max())})

    print(json.dumps({"video_size": [vw, vh], "frames": n_ok,
                      "zones": out}, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
