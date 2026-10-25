#!/usr/bin/env python3
"""reup.py <url> — pipeline reup 1 lenh.

Chay lan 1:  tai -> STT -> resub, roi DUNG de agent viet sub Viet.
    python3 reup.py "<url>"
Chay lan 2 (sau khi co sub Viet): dub -> karaoke -> burn -> up Drive.
    python3 reup.py "<url>" --srt sub_vi.srt [--frost Y:H] [--share]

Toi uu: dub CapCut song song (--jobs), burn preset veryfast,
Kokoro local 1 giong Ngoc Huyen (mac dinh).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path("/home/hatch/workspace/capcut-tts")
JOBS = BASE / "jobs"
REUP = BASE / "reup_sub.py"
CAP_PY = "/home/hatch/workspace/.venvs/capcut/bin/python"
GWS = "/opt/hatch/bin/hatch_gws_cli"
MANIFEST = BASE / "drive_manifest.json"
NEXRAY = os.environ.get("NEXRAY_URL", "https://api.nexray.eu.cc/downloader/aio?url=")


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"FAIL {' '.join(cmd[:3])}...\n{r.stderr[-1200:]}")
    return r


def log(*a):
    print(*a, flush=True)


def slugify(url):
    m = re.search(r"(?:v=|youtu\.be/|reel/|share/v/|/v/|/p/|douyin\.com/video/|douyin\.com/)([A-Za-z0-9_-]{4,})", url)
    tag = m.group(1)[:16] if m else "job"
    return f"{time.strftime('%m%d')}_{tag}"


def fetch(url, wd):
    log("[1] Tai video qua nexray...")
    api = NEXRAY + urllib.parse.quote(url, safe="")
    req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0"})
    data = json.load(urllib.request.urlopen(req, timeout=90))
    r = data.get("result") or {}
    if r.get("error"):
        sys.exit(f"nexray error: {r.get('error')}")
    medias = r.get("medias") or []
    vids = [m for m in medias if m.get("type") == "video" and m.get("url")]
    auds = [m for m in medias if m.get("type") == "audio" and m.get("url")]

    def vscore(m):
        q = str(m.get("quality", "")).upper()
        return (("HD" in q or "1080" in q) * 2 + ("720" in q) * 1,
                int(m.get("height") or 0))

    vids.sort(key=vscore, reverse=True)
    if not vids:
        sys.exit("Khong tim duoc video URL tu nexray")
    meta = {"url": url, "title": r.get("title"), "author": r.get("author"),
            "duration_ms": r.get("duration"), "source": r.get("source")}
    (wd / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    vv, aa = vids[0]["url"], (auds[0]["url"] if auds else None)
    vp, ap = wd / "v.mp4", wd / "a.mp3"
    run(["curl", "-sL", "--retry", "3", "-o", str(vp), vv])
    src = wd / "src.mp4"
    if aa:
        run(["curl", "-sL", "--retry", "3", "-o", str(ap), aa])
        # mux; neu video da co audio thi giu nguyen
        has_a = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=index", "-of", "csv=p=0", str(vp)],
            capture_output=True, text=True).stdout.strip()
        if has_a:
            vp.rename(src)
        else:
            run(["ffmpeg", "-y", "-v", "error", "-i", str(vp), "-i", str(ap),
                 "-c:v", "copy", "-c:a", "aac", "-shortest", str(src)])
    else:
        vp.rename(src)
    log(f"  OK: {src} ({src.stat().st_size/1e6:.1f}MB)")
    return src, meta


def parse_frost(frost, vh):
    """'y:h' (pixel) hoac '0.84:0.14' (ti le). Mac dinh vung duoi."""
    if not frost:
        frost = "0.84:0.14"
    y, h = frost.split(":")
    y, h = float(y), float(h)
    if y < 2 and h < 2:  # ti le
        y, h = int(y * vh), int(h * vh)
    return f"{int(y)}:{int(h)}"


def parse_srt_simple(p):
    """Doc SRT -> [(t1, t2, text)]."""
    cues = []
    txt = Path(p).read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", txt.strip())
    for b in blocks:
        m = re.search(r"(\d+):(\d+):([\d.,]+)\s*-->\s*(\d+):(\d+):([\d.,]+)", b)
        if not m:
            continue
        g = m.groups()
        t1 = int(g[0])*3600 + int(g[1])*60 + float(g[2].replace(",", "."))
        t2 = int(g[3])*3600 + int(g[4])*60 + float(g[5].replace(",", "."))
        text = re.sub(r"(\d+):(\d+):[\d.,]+\s*-->\s*(\d+):(\d+):[\d.,]+", "", b)
        text = re.sub(r"^\d+\s*", "", text).strip()
        cues.append((t1, t2, " ".join(text.split())))
    return cues


def fmt_ts(s):
    s = int(s)
    return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"


def drive_folder(name="Reup"):
    q = (f"name='{name}' and mimeType='application/vnd.google-apps.folder' "
         f"and trashed=false")
    r = run([GWS, "drive", "files", "list", "--params",
             json.dumps({"q": q, "pageSize": 5, "fields": "files(id,name)"})])
    files = json.loads(r.stdout).get("files", [])
    if files:
        return files[0]["id"]
    r = run([GWS, "drive", "files", "create",
             "--params", json.dumps({"ignoreDefaultVisibility": True}),
             "--json", json.dumps({"name": name,
                                   "mimeType": "application/vnd.google-apps.folder"})])
    return json.loads(r.stdout)["id"]


def drive_upload(path, name, share=False):
    folder = drive_folder()
    log(f"  Up Drive (folder Reup): {name}")
    r = run([GWS, "drive", "files", "create", "--upload", str(path),
             "--json", json.dumps({"name": name, "parents": [folder]})])
    info = json.loads(r.stdout)
    fid = info["id"]
    if share:
        run([GWS, "drive", "permissions", "create",
             "--params", json.dumps({"fileId": fid}),
             "--json", json.dumps({"type": "anyone", "role": "reader"})])
    r = run([GWS, "drive", "files", "get",
             "--params", json.dumps({"fileId": fid,
                                     "fields": "id,name,webViewLink,webContentLink,size"})])
    return json.loads(r.stdout)


def save_manifest(entry):
    man = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else []
    man.append(entry)
    MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser(description="reup 1 lenh")
    ap.add_argument("url")
    ap.add_argument("--srt", default=None, help="sub Viet (lan 2)")
    ap.add_argument("--frost", default=None, help="'y:h' vung sub cu (tu dong doan neu bo trong)")
    ap.add_argument("--src-lang", default="en-US", help="ngon ngu goc cho STT")
    ap.add_argument("--engine", choices=["kokoro", "capcut"], default="kokoro")
    ap.add_argument("--capcut-voice", default=None,
                    help="ID giong CapCut khi --engine capcut (vd BV560_streaming)")
    ap.add_argument("--jobs", type=int, default=4,
                    help="so luong TTS song song")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--share", action="store_true", help="Drive link public")
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--v916", choices=["auto", "off", "black", "blur", "square"],
                    default="auto",
                    help="xuat 9:16 (auto: square neu video ngang)")
    ap.add_argument("--banner-top", default="REVIEW PHIM HAY")
    ap.add_argument("--banner-bottom", default="PHIM HAY MỖI NGÀY")
    ap.add_argument("--banner-color", default="FFCC00",
                    help="mau khung 9:16 (hex, khong #)")
    ap.add_argument("--title-template", default="{title}",
                    help="mau tieu de caption, {title} = tieu de goc")
    ap.add_argument("--hashtags", default="",
                    help="hashtag them vao cuoi caption, vd '#reviewphim #phimhay'")
    ap.add_argument("--frost-alpha", type=float, default=0.2,
                    help="do mo thanh che sub cu (0.05-0.9)")
    ap.add_argument("--draft", action="store_true",
                    help="ban nhap: 720x1280, ultrafast (nhanh)")
    ap.add_argument("--with-sub", action="store_true",
                    help="burn sub Viet vao video (mac dinh: khong burn, chi dub + che)")
    ap.add_argument("--frost-auto", action="store_true",
                    help="tu dong phat hien vung sub cu (thay cho --frost tay)")
    ap.add_argument("--cover", default=None,
                    help="che cung logo/text co dinh: 'x:y:w:h' (pixel)")
    a = ap.parse_args()

    wd = Path(a.workdir) if a.workdir else JOBS / slugify(a.url)
    wd.mkdir(parents=True, exist_ok=True)
    st_f = wd / "state.json"
    st = json.loads(st_f.read_text()) if st_f.exists() else {"done": []}

    def mark(s):
        st["done"].append(s)
        st_f.write_text(json.dumps(st, indent=1))

    src = wd / "src.mp4"
    if "fetch" not in st["done"]:
        src, meta = fetch(a.url, wd)
        st["meta"] = meta
        mark("fetch")
    else:
        meta = st.get("meta", {})

    if "stt" not in st["done"]:
        log("[2] STT audio goc...")
        run([CAP_PY, str(REUP), "stt", str(wd / "a.mp3" if (wd / "a.mp3").exists() else src),
             "--lang", a.src_lang, "-o", str(wd / "raw.srt")])
        mark("stt")
    if "resub" not in st["done"]:
        log("[3] Gom cue...")
        run([CAP_PY, str(REUP), "resub", str(wd / "raw.srt"),
             "-o", str(wd / "resub.srt")])
        mark("resub")

    if not a.srt:
        log("\n== DUNG: can sub Viet ==")
        log(f"  1. Viet lai: {wd/'resub.srt'} -> sub_vi.srt (giu nguyen timestamp)")
        log(f"  2. Chay tiep: python3 reup.py \"{a.url}\" --workdir {wd} --srt sub_vi.srt")
        return

    srt_vi = Path(a.srt)
    if not srt_vi.is_absolute():
        srt_vi = wd / srt_vi
    # frost zone + font: tinh tren video surface thuc te (loai letterbox)
    vh = int(run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                  "-show_entries", "stream=height", "-of", "csv=p=0",
                  str(src)]).stdout.strip())
    vw = int(run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                  "-show_entries", "stream=width", "-of", "csv=p=0",
                  str(src)]).stdout.strip())
    v916 = a.v916
    if v916 == "auto":
        v916 = "square" if vw > vh else "off"
    if a.frost_auto:
        # Tu dong phat hien: lay zone co confidence cao nhat
        log("  Auto-detect vung sub cu...")
        try:
            r = subprocess.run([CAP_PY, str(BASE / "autodetect_frost.py"),
                                str(src), str(srt_vi)],
                               capture_output=True, text=True, timeout=120)
            det = json.loads(r.stdout)
            if det.get("zones"):
                # Chon zone co frames_hit cao nhat
                best = max(det["zones"], key=lambda z: z["frames_hit"])
                log(f"  -> {best['frost']} (hit {best['frames_hit']}/{det['frames']})")
                a.frost = best["frost"]
            else:
                log("  -> khong tim thay, dung mac dinh 0.84:0.14")
                a.frost = "0.84:0.14"
        except Exception as e:
            log(f"  -> loi autodetect ({e}), dung mac dinh")
            a.frost = "0.84:0.14"
    frost_src = parse_frost(a.frost, vh)
    fy0, fh0 = map(int, frost_src.split(":"))
    if v916 == "off":
        frost, playres, pr_h = frost_src, ("1920x1080" if vw > vh else "1080x1920"), (1080 if vw > vh else 1920)
        bar_y = int(fy0 / vh * pr_h)
        bar_h = int(fh0 / vh * pr_h)
        font_size, wrap_chars = 76, 24
    elif vh > vw:
        # Video DOC: burn bo qua canvas 9:16 (chi ap canvas khi vw > vh) -> output = kich thuoc goc.
        # Toa do frost truyen vao da o dung khong gian output (= source) -> dung truc tiep, KHONG remap
        # theo kieu square (remap cu day frost ra ngoai khung, vd 880:100 -> 1310:170 tren video 1280).
        frost, playres, pr_h = frost_src, f"{vw}x{vh}", vh
        fy_map, fh_map = fy0, fh0
        surf_y, surf_h = 0, vh
        font_size = 56
        wrap_chars = 26
        if not a.with_sub:
            bar_h = int(fh_map + 20)
        else:
            bar_h = max(int(fh_map + 32), int(font_size * 2 * 1.3))
        bar_y = int(fy_map + fh_map / 2 - bar_h / 2)
        bar_y = max(int(surf_y), min(bar_y, int(surf_y + surf_h - bar_h)))
        frost = f"{bar_y}:{bar_h}"
    else:
        # output 9:16 (draft 720x1280, full 1080x1920)
        OW, OH = (720, 1280) if a.draft else (1080, 1920)
        BH = 280 if a.draft else 420
        playres, pr_h = f"{OW}x{OH}", OH
        if v916 == "square":
            crop = min(vw, vh)
            scale = OW / crop
            cx, cy = (vw - crop) / 2, (vh - crop) / 2
            surf_y, surf_h = BH, OW
            fy_map = surf_y + (fy0 - cy) * scale
            fh_map = fh0 * scale
        else:  # black / blur: fit-width
            scale = OW / vw
            surf_y, surf_h = (OH - vh * scale) / 2, vh * scale
            fy_map = surf_y + fy0 * scale
            fh_map = fh0 * scale
        # font theo surface (Netflix: vua doc tren dien thoai)
        # draft 720: font nho hon
        font_size = (46 if v916 == "square" else 38) if a.draft else (68 if v916 == "square" else 56)
        wrap_chars = 28 if v916 == "square" else 26
        # thanh che: om sat vung sub cu (it padding hon)
        # no-sub: khong can chua text Viet -> chi can che vua chu cu
        if not a.with_sub:
            bar_h = int(fh_map + 20)
        else:
            bar_h = max(int(fh_map + 32), int(font_size * 2 * 1.3))
        bar_y = int(fy_map + fh_map / 2 - bar_h / 2)
        # kep trong surface
        bar_y = max(int(surf_y), min(bar_y, int(surf_y + surf_h - bar_h)))
        frost = f"{bar_y}:{bar_h}"
    st["frost"] = frost
    st_f.write_text(json.dumps(st, indent=1))
    log(f"  Frost: src {frost_src} -> out {frost} (playres {playres}, font {font_size})")
    if "dub" not in st["done"]:
        log("[4] Dub 1 giong Ngoc Huyen...")
        cmd = [CAP_PY, str(REUP), "dub", str(srt_vi), "--engine", a.engine,
               "-o", str(wd / "dubbed.m4a"), "--workdir", str(wd / "work_dub")]
        cmd += ["--jobs", str(a.jobs)]
        if a.engine == "capcut" and a.capcut_voice:
            cmd += ["--voice", a.capcut_voice]
        run(cmd)
        mark("dub")
    if a.with_sub and not (wd / "dub_words.json").exists():
        log("  STT dub de lay word-timing...")
        run([CAP_PY, str(BASE / "stt_words.py"),
             str(wd / "dubbed.m4a"), str(wd / "dub_words.json")])
    if a.with_sub and "karaoke" not in st["done"]:
        log("[5] Karaoke...")
        run([CAP_PY, str(REUP), "karaoke", str(srt_vi),
             "--words", str(wd / "dub_words.json"),
             "-o", str(wd / "final.ass"),
             "--theme", "frost", "--font-size", str(font_size),
             "--bar-y", str(bar_y), "--bar-h", str(bar_h),
             "--wrap-chars", str(wrap_chars), "--playres", playres])
        mark("karaoke")

    if "burn" not in st["done"]:
        log(f"[6] Burn final (frost {frost}, v916={v916}, no_sub={not a.with_sub})...")
        bcmd = [CAP_PY, str(REUP), "burn", str(src),
                "--frost", frost, "--frost-srt", str(srt_vi),
                "--frost-alpha", str(a.frost_alpha),
                "--audio", str(wd / "dubbed.m4a"),
                "-o", str(wd / "final.mp4")]
        if a.cover:
            bcmd += ["--cover", a.cover]
        if a.with_sub:
            bcmd += ["--ass", str(wd / "final.ass")]
        if v916 != "off":
            bcmd += ["--v916", v916,
                     "--banner-top", a.banner_top,
                     "--banner-bottom", a.banner_bottom,
                     "--banner-color", a.banner_color]
            if a.draft:
                bcmd += ["--draft"]
        else:
            bcmd += ["--dodge"]
        run(bcmd)
        mark("burn")

    final = wd / "final.mp4"
    # Luu caption.txt (ten + noi dung sub Viet) thay cho SRT
    cap_txt = wd / "caption.txt"
    try:
        cues = parse_srt_simple(str(srt_vi))
        orig_title = (meta.get("title") or "").strip()
        title_out = (a.title_template or "{title}").replace("{title}", orig_title)
        lines = [f"TITLE: {title_out}",
                 f"URL: {a.url}", ""]
        for i, (t1, t2, txt) in enumerate(cues, 1):
            lines.append(f"[{fmt_ts(t1)} --> {fmt_ts(t2)}] {txt}")
        if (a.hashtags or "").strip():
            lines += ["", (a.hashtags or "").strip()]
        cap_txt.write_text("\n".join(lines), encoding="utf-8")
    except Exception as e:
        log(f"  (ghi caption.txt loi: {e})")
    if not a.no_upload and "upload" not in st["done"]:
        log("[7] Up Drive (video + caption)...")
        base = re.sub(r"[^\w\-. ]+", "", (meta.get("title") or "reup").strip()[:60]) or "reup"
        vname = base + "_vi.mp4"
        info = drive_upload(final, vname, share=a.share)
        save_manifest({"local": str(final), "drive_id": info["id"],
                       "link": info.get("webViewLink"),
                       "title": meta.get("title"), "time": time.strftime("%F %T")})
        st["drive"] = info
        # Upload caption.txt kem (ten + noi dung)
        if cap_txt.exists():
            try:
                cinfo = drive_upload(cap_txt, base + "_caption.txt", share=a.share)
                log(f"  Caption: {cinfo.get('webViewLink')}")
                st["drive_caption"] = cinfo.get("webViewLink")
            except Exception as e:
                log(f"  (up caption loi: {e})")
        mark("upload")
        log(f"  Link: {info.get('webViewLink')}")

    # title goc cho agent viet lai
    (wd / "title_src.txt").write_text(
        f"GOC: {meta.get('title')}\nURL: {a.url}\n", encoding="utf-8")
    log("\n== XONG ==")
    log(f"  Video: {final} ({final.stat().st_size/1e6:.0f}MB)")
    if st.get("drive"):
        log(f"  Drive: {st['drive'].get('webViewLink')}")
    log(f"  Viet title/hashtag tu: {wd/'title_src.txt'} -> luu {wd/'title_vi.txt'}")


if __name__ == "__main__":
    main()
