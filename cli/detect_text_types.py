#!/usr/bin/env python3
"""Phan biet text CO DINH (logo/disclaimer) vs PHU DE (dong).
- Text co dinh: xuat hien >90% frame -> dung --cover (che cung, luon hien)
- Phu de: xuat hien 20-80% frame -> dung --frost (mo, chi khi co cue)
Usage: python3 detect_text_types.py <video> <srt>
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
    pr = subprocess.run(["ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=width,height,duration","-of","csv=p=0",video],
        capture_output=True, text=True)
    vw, vh, dur = pr.stdout.strip().split(",")
    vw, vh, dur = int(vw), int(vh), float(dur)
    SW = 480
    scale = vw / SW

    cues = parse_srt(srt)
    # Lay 30 frame deu khap video
    times = [dur * i / 30 for i in range(30)]

    # Dem text theo hang qua cac frame
    row_hits = None
    SH = None
    n_ok = 0
    with tempfile.TemporaryDirectory() as td:
        for i, t in enumerate(times):
            fp = os.path.join(td, f"f{i}.png")
            r = subprocess.run(["ffmpeg","-y","-v","error","-ss",str(t),
                "-i",video,"-frames:v","1","-vf",f"scale={SW}:-1",fp],
                capture_output=True)
            if r.returncode != 0: continue
            img = cv2.imread(fp)
            if img is None: continue
            if SH is None:
                SH = img.shape[0]
                row_hits = np.zeros(SH, dtype=np.int32)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, bw = cv2.threshold(gray, 210, 255, cv2.THRESH_BINARY)
            # Hang co text: >8% pixel trang
            has_text = ((bw > 0).sum(axis=1) > SW * 0.08)
            row_hits += has_text.astype(np.int32)
            n_ok += 1

    if n_ok == 0:
        print(json.dumps({"error": "khong doc duoc"})); return

    # Phan loai theo ty le xuat hien
    ratio = row_hits / n_ok
    # Tim dai lien tuc
    def find_bands(mask, min_h=6):
        bands = []
        s = None
        for y in range(SH):
            if mask[y] and s is None: s = y
            elif not mask[y] and s is not None:
                if y - s >= min_h: bands.append((s, y))
                s = None
        if s is not None and SH - s >= min_h: bands.append((s, SH))
        return bands

    fixed_mask = ratio > 0.9
    sub_mask = (ratio >= 0.2) & (ratio <= 0.8)

    fixed = []
    for s, e in find_bands(fixed_mask):
        # Bo qua vung qua nho
        fixed.append({"y": int(s*scale), "h": int((e-s)*scale),
                      "ratio": float(ratio[s:e].mean())})
    subs = []
    for s, e in find_bands(sub_mask):
        subs.append({"y": int(s*scale), "h": int((e-s)*scale),
                     "ratio": float(ratio[s:e].mean())})

    # Gop dai gan nhau
    def merge(bands, gap=12):
        if not bands: return []
        bands = sorted(bands, key=lambda b: b["y"])
        out = [bands[0]]
        for b in bands[1:]:
            if b["y"] - (out[-1]["y"] + out[-1]["h"]) < gap*scale:
                out[-1]["h"] = b["y"] + b["h"] - out[-1]["y"]
            else:
                out.append(b)
        return out

    print(json.dumps({
        "video_size": [vw, vh],
        "frames": n_ok,
        "fixed_text": merge(fixed),    # dung --cover
        "subtitles": merge(subs),      # dung --frost
    }, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
