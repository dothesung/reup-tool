#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reup_sub.py — Pipeline reup video: STT (v2t) -> resub -> TTS dub -> burn sub.
Single-file. Chay tren VM nay voi venv ~/workspace/.venvs/capcut.

Yeu cau: ffmpeg, package capcut_tts_api (pip install -e <repo K07VN/capcut-tts-api>).

Cach dung:
  # 1. Tach audio + STT ra SRT tho (word-level)
  python reup_sub.py stt video.mp4 --lang vi-VN -o raw.srt

  # 1b. STT kem dich may (vd: video tieng Anh -> sub Viet tho)
  python reup_sub.py stt video.mp4 --lang en-US --translate vi-VN -o raw.srt

  # 2. Gom cue tu-level thanh cue doc duoc (xuống dòng, ngắt câu)
  python reup_sub.py resub raw.srt -o sub.srt

  # 3. (Tuy chon) Long tieng Viet tung cue, giu dung timestamp
  python reup_sub.py dub sub.srt --voice BV421_vivn_streaming -o dubbed.m4a

  # 4. Burn sub (+ audio long tieng) ra video moi
  python reup_sub.py burn video.mp4 --srt sub.srt -o final.mp4
  python reup_sub.py burn video.mp4 --srt sub.srt --audio dubbed.m4a -o final.mp4

  # Xem giọng Viet:
  python reup_sub.py voices --lang vi-VN

Luu y:
  - API CapCut la hang reverse-engineered, co the die/rate-limit bat cu luc nao.
    Fallback local: faster-whisper (STT) + VieNeu-TTS (giong Ngoc Linh/Thien Minh).
  - Buoc "AI viet lai phu de tu nhien" (bien dich tho -> van Viet muot) nen lam
    bang LLM rieng truoc khi burn; script nay chi gom cue cho de doc.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------- SRT helpers

TS_RE = re.compile(
    r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d+):(\d{2}):(\d{2})[,.](\d{1,3})"
)


def ts_to_ms(ts) -> int:
    """Parse 'HH:MM:SS,mmm' | 'HH:MM:SS.mmm' | ms (int/float/numeric str) -> ms.

    LUU Y: SDK capcut_tts_api tra start_time/end_time la MILLISECOND (int),
    khong phai giay.
    """
    if isinstance(ts, (int, float)):
        return int(ts)
    s = str(ts).strip()
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return int(float(s))
    m = re.match(r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})", s)
    if not m:
        raise ValueError(f"Bad timestamp: {ts!r}")
    h, mi, sec, ms = m.groups()
    return (int(h) * 3600 + int(mi) * 60 + int(sec)) * 1000 + int(ms.ljust(3, "0")[:3])


def ms_to_ts(ms: int) -> str:
    ms = max(0, int(ms))
    h, ms = divmod(ms, 3600000)
    mi, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{mi:02d}:{s:02d},{ms:03d}"


def parse_srt(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    cues = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue
        m = TS_RE.search(lines[1] if "-->" in lines[1] else (lines[0] if "-->" in lines[0] else ""))
        body_start = 2 if "-->" in lines[1] else 1
        if not m:
            continue
        start = (int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))) * 1000 + int(m.group(4).ljust(3, "0")[:3])
        end = (int(m.group(5)) * 3600 + int(m.group(6)) * 60 + int(m.group(7))) * 1000 + int(m.group(8).ljust(3, "0")[:3])
        body = " ".join(l.strip() for l in lines[body_start:] if l.strip())
        if body:
            cues.append({"start": start, "end": end, "text": body})
    return cues


def write_srt(cues, path):
    out = []
    for i, c in enumerate(cues, 1):
        out.append(f"{i}\n{ms_to_ts(c['start'])} --> {ms_to_ts(c['end'])}\n{c['text']}\n")
    Path(path).write_text("\n".join(out), encoding="utf-8")
    return path


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"CMD failed: {' '.join(cmd)}\n{r.stderr[-2000:]}")
    return r


def check_ffmpeg():
    if not shutil.which("ffmpeg"):
        sys.exit("Khong tim thay ffmpeg. Cai: sudo apt install ffmpeg")

# ---------------------------------------------------------------- resub

SENT_END = set(".!?…:;—-")


def wrap_lines(text, max_chars, max_lines=2):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len((cur + " " + w).strip()) <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
            if len(lines) >= max_lines - 1 and len(" ".join(words[words.index(w):])) > max_chars:
                # gom het phan con lai vao dong cuoi (cat bot neu qua dai)
                rest = " ".join(words[words.index(w):])
                lines.append(rest[: max_chars * 2])
                return lines[:max_lines]
    if cur:
        lines.append(cur)
    return lines[:max_lines]


def resub_cues(cues, max_chars=42, max_dur_ms=6000, min_chars=12, gap_ms=1200):
    """Gom cue word-level thanh cue doc duoc."""
    out, acc_text, acc_start, acc_end = [], "", 0, 0

    def flush():
        nonlocal acc_text, acc_start, acc_end
        if acc_text.strip():
            lines = wrap_lines(acc_text.strip(), max_chars)
            out.append({"start": acc_start, "end": acc_end, "text": "\n".join(lines)})
        acc_text, acc_start, acc_end = "", 0, 0

    for c in cues:
        w = c["text"].strip()
        if not w:
            continue
        if not acc_text:
            acc_text, acc_start, acc_end = w, c["start"], c["end"]
            continue
        gap = c["start"] - acc_end
        too_long = len(acc_text) + 1 + len(w) > max_chars * 2
        too_dur = c["end"] - acc_start > max_dur_ms
        if too_long or too_dur or (gap > gap_ms and len(acc_text) >= min_chars):
            flush()
            acc_text, acc_start, acc_end = w, c["start"], c["end"]
        else:
            acc_text += " " + w
            acc_end = c["end"]
            if acc_text[-1] in SENT_END and len(acc_text) >= min_chars:
                nxt_is_pause = gap > 400
                if nxt_is_pause or len(acc_text) > max_chars:
                    flush()
    flush()
    return out

# ---------------------------------------------------------------- commands

def get_client():
    try:
        from capcut_tts_api import CapCutClient
    except ImportError:
        sys.exit("Chua cai capcut_tts_api. Chay: pip install -e <repo K07VN/capcut-tts-api>")
    return CapCutClient(timeout=90)


def cmd_stt(a):
    check_ffmpeg()
    client = get_client()
    tmp = Path(tempfile.mkdtemp(prefix="reup_stt_"))
    wav = tmp / "audio.wav"
    print(f"[1/3] Tach audio -> {wav}")
    run(["ffmpeg", "-y", "-v", "error", "-i", a.input, "-vn",
         "-ar", "16000", "-ac", "1", str(wav)])
    print("[2/3] STT via CapCut...")
    kw = dict(language=a.lang, timeout=300)
    if a.translate:
        kw.update(use_translation=True, translation_language=a.translate)
    stt = client.transcribe_file(str(wav), **kw)
    subs = client.extract_subtitles(stt)
    subs.write_srt(a.out, use_translation=bool(a.translate))
    n = len(parse_srt(a.out))
    print(f"[3/3] OK: {a.out} ({n} cue tho). Chay 'resub' de gom cue.")
    shutil.rmtree(tmp, ignore_errors=True)


def cmd_resub(a):
    cues = parse_srt(a.input)
    if not cues:
        sys.exit(f"Khong doc duoc cue nao tu {a.input}")
    out = resub_cues(cues, max_chars=a.max_chars, max_dur_ms=int(a.max_dur * 1000))
    write_srt(out, a.out)
    print(f"OK: {a.input} ({len(cues)} cue tho) -> {a.out} ({len(out)} cue)")


def kokoro_synth_parts(cues, workdir, jobs=4):
    """Dung Kokoro local (giong Ngoc Huyen) synth tung cue -> wav parts.
    Chay qua venv kokoro rieng. Chia N chunk chay song song (moi chunk load model rieng).
    Tra ve [(start_ms, end_ms, path)]."""
    import json
    import subprocess
    from concurrent.futures import ThreadPoolExecutor
    kokoro_py = os.environ.get("KOKORO_PY") or sys.executable
    parts_dir = Path(workdir) / "parts_kokoro"
    parts_dir.mkdir(parents=True, exist_ok=True)

    # Chia cue thanh N chunk
    n = min(jobs, len(cues))
    chunks = [cues[i::n] for i in range(n)]
    # Map global index cho tung chunk
    chunk_jobs = []
    for ci, ch in enumerate(chunks):
        js = []
        for c in ch:
            gi = cues.index(c)  # index global (0-based)
            js.append({"id": gi + 1, "text": c["text"]})
        jf = Path(workdir) / f"kokoro_jobs_{ci}.json"
        jf.write_text(json.dumps(js, ensure_ascii=False), encoding="utf-8")
        chunk_jobs.append((jf, ci))

    print(f"  Kokoro: synth {len(cues)} cue, {n} luong song song...")
    def run_chunk(args):
        jf, ci = args
        kokoro_script = os.environ.get("KOKORO_SCRIPT") or "/home/hatch/workspace/kokoro-vi/batch_synth.py"
        r = subprocess.run([kokoro_py, kokoro_script,
                            str(jf), str(parts_dir)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"Kokoro chunk {ci} failed:\n{r.stderr[-1000:]}")
        return ci
    with ThreadPoolExecutor(max_workers=n) as ex:
        list(ex.map(run_chunk, chunk_jobs))

    parts = []
    for i, c in enumerate(cues, 1):
        p = parts_dir / f"cue_{i:03d}.wav"
        if not p.exists():
            print(f"  ! thieu audio cue {i}")
            continue
        parts.append((c["start"], c["end"], str(p)))
    return parts


def cmd_dub(a):
    check_ffmpeg()
    cues = parse_srt(a.srt)
    if not cues:
        sys.exit(f"Khong doc duoc cue nao tu {a.srt}")
    workdir = Path(a.workdir or tempfile.mkdtemp(prefix="reup_dub_"))
    if a.engine == "kokoro":
        print(f"[1/2] TTS Kokoro local (Ngoc Huyen) {len(cues)} cue...")
        parts = kokoro_synth_parts(cues, workdir, jobs=a.jobs)
        print(f"[2/2] Mix {len(parts)} cue theo timestamp -> {a.out}")
        mix_wav = _mix_parts_at_offsets(parts, workdir, fit=not a.no_fit)
        run(["ffmpeg", "-y", "-v", "error", "-i", str(mix_wav),
             "-c:a", "aac", "-b:a", "128k", a.out])
        print(f"OK: {a.out}")
        return
    client = get_client()
    # cast: "1,2:VOICE_A;3:VOICE_B" — cue nao khong co trong cast dung voice mac dinh
    cast = {}
    if a.cast:
        for grp in a.cast.split(";"):
            nums, v = grp.split(":")
            for n in nums.split(","):
                cast[int(n.strip())] = v.strip()
    # nhom cue theo voice de goi TTS tung dot
    by_voice = {}
    for i, c in enumerate(cues, start=1):
        by_voice.setdefault(cast.get(i, a.voice), []).append(i)
    print(f"[1/2] TTS {len(cues)} cue, {len(by_voice)} voice: "
          + ", ".join(f"{v}({len(ix)})" for v, ix in by_voice.items()))
    # song song: chia moi nhom voice thanh chunk, goi API dong thoi
    import concurrent.futures as cf

    def synth_chunk(v, chunk_idxs, j):
        cli = get_client()
        tmp_srt = workdir / f"cast_{v}_{j}.srt"
        write_srt([dict(cues[k - 1], index=k) for k in chunk_idxs], str(tmp_srt))
        outd = workdir / f"parts_{v}_{j}"
        res = cli.generate_speech_from_srt(
            str(tmp_srt), voice=v, output_dir=str(outd),
            timeout=300, part=True)
        return res["cues"]

    jobs = max(1, getattr(a, "jobs", 3))
    tasks = []
    for v, idxs in by_voice.items():
        n = min(jobs, len(idxs))
        for j in range(n):
            tasks.append((v, idxs[j::n], j))
    print(f"  -> {len(tasks)} chunk song song (jobs={jobs})")
    chunk_cues = []
    with cf.ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        futs = [ex.submit(synth_chunk, v, ix, j) for v, ix, j in tasks]
        for f in cf.as_completed(futs):
            try:
                chunk_cues.extend(f.result())
            except Exception as e:
                print(f"  ! chunk loi: {e}")
    parts = []
    cue_end = {c["start"]: c["end"] for c in cues}
    for c in chunk_cues:
        p = Path(c["audio_path"])
        if not p.exists():
            print(f"  ! thieu audio cue @{c['start_time']}, bo qua")
            continue
        st = ts_to_ms(c["start_time"])
        parts.append((st, cue_end.get(st, st + 60000), str(p)))
    if not parts:
        sys.exit("Khong co audio cue nao duoc sinh.")
    print(f"[2/2] Mix {len(parts)} cue theo timestamp -> {a.out}")
    mix_wav = _mix_parts_at_offsets(parts, workdir, fit=not a.no_fit)
    run(["ffmpeg", "-y", "-v", "error", "-i", str(mix_wav),
         "-c:a", "aac", "-b:a", "128k", a.out])
    print(f"OK: {a.out}")


def _mix_parts_at_offsets(parts, workdir, fit=True):
    """Mix cac part mp3 theo offset ms (code Python, khong dung amix).
    parts = (start_ms, end_ms, path). fit=True: co audio (atempo<=1.3x)
    neu dai hon cue de khong tran sang cue sau."""
    import array
    import wave
    sr = 44100
    tmp = Path(workdir) / "wavparts"
    tmp.mkdir(parents=True, exist_ok=True)
    decoded = []
    for start_ms, end_ms, p in parts:
        window = (end_ms - start_ms) / 1000
        af = []
        if fit and window > 0:
            dur = float(run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of", "csv=p=0", p]
                            ).stdout.strip() or 0)
            if dur > window * 1.05:
                rate = min(dur / window, 1.3)
                af = ["-af", f"atempo={rate:.3f}"]
                print(f"  ! fit cue @{start_ms}ms: {dur:.1f}s->{window:.1f}s (x{rate:.2f})")
        w = tmp / (Path(p).stem + ".wav")
        run(["ffmpeg", "-y", "-v", "error", "-i", p,
             "-ar", str(sr), "-ac", "1"] + af + ["-f", "wav", str(w)])
        with wave.open(str(w), "rb") as wf:
            frames = wf.readframes(wf.getnframes())
        samples = array.array("h", frames)
        offset = int(start_ms * sr / 1000)
        decoded.append((offset, samples))
    total = max(off + len(s) for off, s in decoded)
    mixed = array.array("h", bytes(total * 2))
    for off, s in decoded:
        for i, v in enumerate(s):
            nv = mixed[off + i] + v
            mixed[off + i] = 32767 if nv > 32767 else (-32768 if nv < -32768 else nv)
    out_wav = Path(workdir) / "dubbed_mix.wav"
    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(mixed.tobytes())
    return out_wav


def make_banner(text, color_hex, out_path, W=1080, H=420):
    """Render khung mau + chu (PIL) cho mode v916 square."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (W, H), "#" + color_hex)
    d = ImageDraw.Draw(img)
    fp = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
    size = 100
    while size > 24:
        f = ImageFont.truetype(fp, size)
        bb = d.textbbox((0, 0), text, font=f)
        if bb[2] - bb[0] <= W - 70:
            break
        size -= 6
    f = ImageFont.truetype(fp, size)
    d.text((W / 2, H / 2), text, font=f, fill="black", anchor="mm")
    img.save(out_path)
    return out_path


def cmd_burn(a):
    check_ffmpeg()
    style = ("FontName=Noto Sans,FontSize={fs},PrimaryColour=&HFFFFFF,"
             "OutlineColour=&H80000000,BorderStyle=1,Outline=2,"
             "Shadow=0,MarginV={mv},Alignment=2").format(
                 fs=a.font_size, mv=a.margin_v)
    # Do dai chuan = do dai video (audio long tieng ngan hon -> pad im lang)
    vd = float(run(["ffprobe", "-v", "error", "-show_entries",
                    "format=duration", "-of", "csv=p=0", a.video],
                   ).stdout.strip())
    vw, vh = map(int, run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", a.video],
    ).stdout.strip().split(","))
    # --- v916: dung canvas 9:16 ---
    v916 = getattr(a, "v916", "off")
    draft = getattr(a, "draft", False)
    OW, OH = (720, 1280) if draft else (1080, 1920)  # output size
    BH = 280 if draft else 420  # banner height
    inputs = ["-i", a.video]
    fc_pre = []
    vsrc = "[0:v]"
    out_w = vw
    audio_idx = 1
    workdir = Path(a.out).parent
    if v916 != "off" and vw > vh:
        if v916 == "square":
            top_png = str(workdir / "banner_top.png")
            bot_png = str(workdir / "banner_bot.png")
            make_banner(a.banner_top, a.banner_color, top_png, W=OW, H=BH)
            make_banner(a.banner_bottom, a.banner_color, bot_png, W=OW, H=BH)
            inputs += ["-i", top_png, "-i", bot_png]
            audio_idx = 3
            sq = OW  # square video size
            fc_pre = [
                f"color=c=0x{a.banner_color}:s={OW}x{OH}:r=30:d={vd:.3f}[canvas]",
                f"[1:v]scale={OW}:{BH}[bt]",
                f"[2:v]scale={OW}:{BH}[bb]",
                "[canvas][bt]overlay=0:0[t1]",
                f"[t1][bb]overlay=0:{OH-BH}[t2]",
                r"[0:v]crop=min(iw\,ih):min(iw\,ih):(iw-min(iw\,ih))/2:(ih-min(ih\,ih))/2,"
                f"scale={sq}:{sq}[fg]",
                f"[t2][fg]overlay=(W-w)/2:(H-h)/2[vbase]",
            ]
        elif v916 == "black":
            fc_pre = [
                f"color=c=black:s={OW}x{OH}:r=30:d={vd:.3f}[canvas]",
                f"[0:v]scale={OW}:-2[fg]",
                "[canvas][fg]overlay=(W-w)/2:(H-h)/2[vbase]",
            ]
        elif v916 == "blur":
            fc_pre = [
                "[0:v]split=2[bg0][fg0]",
                f"[bg0]scale={OW}:{OH}:force_original_aspect_ratio=increase,"
                f"crop={OW}:{OH},boxblur=20:4,"
                "eq=brightness=-0.12:saturation=0.85[canvas]",
                f"[fg0]scale={OW}:-2[fg]",
                "[canvas][fg]overlay=(W-w)/2:(H-h)/2[vbase]",
            ]
        vsrc = "[vbase]"
        out_w = OW
    filters = []
    use_frost = bool(a.frost)
    # Cover: che mo text co dinh (trong suot nhe nhu frost, luon hien)
    cover_filter = None
    cover_yh = None
    if a.cover:
        y, h = a.cover.split(":")
        cover_yh = (int(y), int(h))
        # Dung blur + veil trang mo nhe (giong frost) thay vi den dac
        cover_filter = True  # danh dau, xu ly ben duoi
    sub_filter = None
    if a.ass:
        ass_esc = str(Path(a.ass).resolve()).replace(":", r"\:")
        sub_filter = f"ass={ass_esc}"
    elif a.srt:
        srt_esc = str(Path(a.srt).resolve()).replace(":", r"\:")
        sub_filter = f"subtitles={srt_esc}:force_style='{style}'"
    if not sub_filter and not use_frost:
        sys.exit("burn can --srt hoac --ass (va tuy chon --cover/--frost)")
    if use_frost:
        # Nen trang mo: crop vung -> boxblur -> phu veil trang -> dap len video
        # (chi hien trong cac cue neu co --frost-srt)
        # --dodge: crop nhe 3% + scale lai + eq (lách ban quyen), toa do frost giu nguyen
        fy, fh = (int(x) for x in a.frost.split(":"))
        pre = list(fc_pre)
        if a.delogo:
            dx, dy, dw, dh = a.delogo.split(":")
            pre.append(f"{vsrc}delogo=x={dx}:y={dy}:w={dw}:h={dh}[dl0]")
            vsrc = "[dl0]"
        # v916 square/black/blur da bien doi manh -> bo qua dodge rieng
        if a.dodge and v916 == "off":
            # dodge = zoom nhe 3%: scale len truoc roi crop ve kich thuoc goc
            # (crop-then-scale bi mat kich thuoc vi iw/ih doi sau crop)
            pre.append(f"{vsrc}scale=ceil(iw/0.97/2)*2:ceil(ih/0.97/2)*2,"
                       f"crop={vw}:{vh},"
                       f"eq=brightness=0.02:saturation=1.06[d0]")
            vsrc = "[d0]"
        enable = ""
        if a.frost_srt:
            ts = []
            for c in parse_srt(a.frost_srt):
                ts.append(f"between(t,{c['start']/1000:.2f},{c['end']/1000:.2f})")
            if ts:
                enable = ":enable='" + "+".join(ts) + "'"
        # split tuong minh: tranh bug auto-split cua ffmpeg khi dung vsrc 2 lan
        # draft: bo boxblur (chi veil trang) cho nhanh
        # blur radius khong vuot qua 1/4 chieu cao frost (tranh loi ffmpeg)
        blur_r = min(10 if draft else 14, max(2, fh // 4))
        if draft:
            # draft: blur nhe + veil (nhanh hon full blur, van an duoc chu)
            # split tuong minh de tranh bug auto-split
            pre.append(f"{vsrc}split=2[vs1][vs2]")
            fc = pre + [
                f"[vs1]crop=iw:{fh}:0:{fy},boxblur={blur_r}:2[bg]",
                f"color=white@{a.frost_alpha}:s={out_w}x{fh}:r=30:d={vd:.3f},format=rgba[veil]",
                "[bg][veil]overlay=0:0:format=auto[bar]",
                f"[vs2][bar]overlay=0:{fy}:format=yuv420{enable}[base]",
            ]
        else:
            pre.append(f"{vsrc}split=2[vs1][vs2]")
            fc = pre + [
                f"[vs1]crop=iw:{fh}:0:{fy},boxblur={blur_r}:2[bg]",
                f"color=white@{a.frost_alpha}:s={out_w}x{fh}:r=30:d={vd:.3f},format=rgba[veil]",
                "[bg][veil]overlay=0:0:format=auto[bar]",
                f"[vs2][bar]overlay=0:{fy}:format=yuv420{enable}[base]",
            ]
        vmap = "[base]"
        if sub_filter:
            fc.append(f"[base]{sub_filter}[vout]")
            vmap = "[vout]"
        # Cover text co dinh: blur mo nhe (giong frost nhung luon hien)
        if cover_filter and cover_yh:
            cy, ch = cover_yh
            blur_c = min(8, max(2, ch // 4))
            # Tao bar mo cho cover: crop -> blur -> veil -> overlay (luon hien)
            fc.append(f"{vmap}split=2[cv1][cv2]")
            fc.append(f"[cv1]crop=iw:{ch}:0:{cy},boxblur={blur_c}:2[cbg]")
            fc.append(f"color=white@0.3:s={out_w}x{ch}:r=30:d={vd:.3f},format=rgba[cveil]")
            fc.append("[cbg][cveil]overlay=0:0:format=auto[cbar]")
            fc.append(f"[cv2][cbar]overlay=0:{cy}:format=yuv420[vcover]")
            vmap = "[vcover]"
        cmd = ["ffmpeg", "-y", "-v", "error"] + inputs
        if a.audio:
            cmd += ["-i", a.audio]
            audio_idx = len(inputs) // 2
        cmd += ["-filter_complex", ";".join(fc), "-map", vmap]
        if a.audio:
            cmd += ["-map", f"{audio_idx}:a", "-af", f"apad=whole_dur={vd:.3f}",
                    "-c:a", "aac", "-b:a", "128k"]
        cmd += ["-c:v", "libx264", "-preset",
                "ultrafast" if draft else "veryfast", "-crf", "20",
                "-t", f"{vd:.3f}", a.out]
        print(f"Burn frost ({a.frost}) + sub -> {a.out} ...")
        run(cmd)
        print(f"OK: {a.out}")
        return
    if sub_filter:
        filters.append(sub_filter)
    if a.dodge and not use_frost:
        filters.insert(0, f"scale=ceil(iw/0.97/2)*2:ceil(ih/0.97/2)*2,"
                          f"crop={vw}:{vh},"
                          "eq=brightness=0.02:saturation=1.06")
    if a.delogo and not use_frost:
        dx, dy, dw, dh = a.delogo.split(":")
        filters.insert(0, f"delogo=x={dx}:y={dy}:w={dw}:h={dh}")
    vf = ",".join(filters)
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", a.video]
    if a.audio:
        cmd += ["-i", a.audio, "-map", "0:v", "-map", "1:a",
                "-af", f"apad=whole_dur={vd:.3f}"]
    cmd += ["-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-t", f"{vd:.3f}"]
    if a.audio:
        cmd += ["-c:a", "aac", "-b:a", "128k"]
    else:
        cmd += ["-c:a", "copy"]
    cmd.append(a.out)
    print(f"Burn sub -> {a.out} ...")
    run(cmd)
    print(f"OK: {a.out}")


def cmd_voices(a):
    client = get_client()
    for v in client.list_voices(lang=a.lang):
        print(f"{v.voice_type:35s} {v.display_name}")


def ass_ts(ms: int) -> str:
    ms = max(0, int(ms))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h}:{m:02d}:{s:02d}.{ms//10:02d}"


def cmd_karaoke(a):
    """SRT + word-timing STT -> ASS karaoke pill (tu chuyen mau theo nhip doc)."""
    import json
    cues = parse_srt(a.srt)
    if not cues:
        sys.exit(f"Khong doc duoc cue nao tu {a.srt}")
    stt = json.load(open(a.words, encoding="utf-8"))
    # gan utterance STT vao cue theo do chong lap thoi gian lon nhat
    # (loc token rong cua SDK)
    groups = [[] for _ in cues]
    for u in stt:
        words = [w for w in u["words"] if w.get("t", "").strip()]
        if not words:
            continue
        best, best_ov = -1, 0
        for i, c in enumerate(cues):
            ov = min(u["end"], c["end"]) - max(u["start"], c["start"])
            if ov > best_ov:
                best, best_ov = i, ov
        if best >= 0:
            groups[best].extend(words)
    events = []
    for i, c in enumerate(cues):
        my_words = c["text"].replace("\n", " ").split()
        sw = groups[i]
        durs = []
        if len(sw) == len(my_words) and sw:
            for j, w in enumerate(sw):
                if j < len(sw) - 1:
                    d = (sw[j + 1]["s"] - w["s"]) / 10
                else:
                    d = (c["end"] - w["s"]) / 10
                durs.append(max(5, int(round(d))))
        else:
            span = c["end"] - c["start"]
            tot = sum(len(w) for w in my_words) or 1
            durs = [max(5, int(round(span / 10 * len(w) / tot))) for w in my_words]
            print(f"  ! cue {i+1}: STT {len(sw)}w != text {len(my_words)}w -> chia ti le")
        # frost: xuong dong chu dong de can giua chinh xac tren thanh
        disp_lines = []
        fs_override = None
        if a.theme == "frost":
            cur, cur_len = [], 0
            for w in my_words:
                if cur and cur_len + 1 + len(w) > a.wrap_chars:
                    disp_lines.append(cur)
                    cur, cur_len = [], 0
                cur.append(w)
                cur_len += len(w) + (1 if cur_len else 0)
            if cur:
                disp_lines.append(cur)
            # Netflix: toi da 2 dong — gop lai + thu nho font vua thanh
            if len(disp_lines) > 2:
                words = [w for ln in disp_lines for w in ln]
                tot = sum(len(w) + 1 for w in words)
                acc, cut = 0, len(words)
                for k, w in enumerate(words):
                    acc += len(w) + 1
                    if acc >= tot / 2:
                        cut = k + 1
                        break
                disp_lines = [words[:cut], words[cut:]]
                fs_override = max(30, int(a.font_size * 2 / 3))
                print(f"  ! cue {i+1}: -> 2 dong, font {fs_override}")
        else:
            disp_lines = [ln.split() for ln in c["text"].split("\n")]
        wi = 0
        out_lines = []
        for li, words_in_line in enumerate(disp_lines):
            parts = []
            for wj, w in enumerate(words_in_line):
                tag = f"{{\\k{durs[wi]}}}"
                if fs_override and li == 0 and wj == 0:
                    tag = f"{{\\fs{fs_override}\\k{durs[wi]}}}"
                parts.append(f"{tag}{w}")
                wi += 1
            out_lines.append(" ".join(parts))
        events.append((c["start"], c["end"], "\\N".join(out_lines),
                       len(out_lines)))
    if a.theme == "frost":
        # Chu dam tren nen trang mo: bo pill den, can giua theo thanh
        style_line = ("Style: Frost,Noto Sans,{fs},&H001A1A1A,&H000045FF,"
                      "&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,2,0,2,"
                      "40,40,0,1").format(fs=a.font_size)
        style_name = "Frost"
        line_h = int(a.font_size * 1.15)
        bar_c = a.bar_y + a.bar_h // 2
    else:
        style_line = ("Style: Pill,Noto Sans,{fs},&H00FFFFFF,&H0000FFFF,"
                      "&H96000000,&HAA000000,-1,0,0,0,100,100,0,0,3,3,0,2,"
                      "40,40,{mv},1").format(fs=a.font_size, mv=a.margin_v)
        style_name = "Pill"
        line_h, bar_c = 0, 0
    prx, pry = a.playres.split("x")
    head = """[Script Info]
Title: Karaoke
ScriptType: v4.00+
PlayResX: {prx}
PlayResY: {pry}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""".format(style=style_line, prx=prx, pry=pry)
    body = ""
    for s, e, t, nlines in events:
        if a.theme == "frost":
            mv = int(pry) - (bar_c + (nlines * line_h) // 2)
            body += (f"Dialogue: 0,{ass_ts(s)},{ass_ts(e)},{style_name},,"
                     f"0,0,{mv},,{t}\n")
        else:
            body += f"Dialogue: 0,{ass_ts(s)},{ass_ts(e)},{style_name},,0,0,0,,{t}\n"
    Path(a.out).write_text(head + body, encoding="utf-8")
    print(f"OK: {a.out} ({len(events)} cue karaoke, theme={a.theme})")

# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(
        prog="reup_sub.py",
        description="Pipeline reup video: STT (v2t) -> resub -> TTS dub -> burn sub.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("stt", help="Video/audio -> SRT tho (word-level)")
    p.add_argument("input"); p.add_argument("-o", "--out", default="raw.srt")
    p.add_argument("--lang", default="vi-VN")
    p.add_argument("--translate", default=None, help="vd: vi-VN (dich may trong luc STT)")
    p.set_defaults(fn=cmd_stt)

    p = sub.add_parser("resub", help="Gom cue tho thanh cue doc duoc")
    p.add_argument("input"); p.add_argument("-o", "--out", default="sub.srt")
    p.add_argument("--max-chars", type=int, default=42)
    p.add_argument("--max-dur", type=float, default=6.0)
    p.set_defaults(fn=cmd_resub)

    p = sub.add_parser("dub", help="TTS tung cue, mix theo timestamp")
    p.add_argument("srt"); p.add_argument("-o", "--out", default="dubbed.m4a")
    p.add_argument("--voice", default="BV421_vivn_streaming")
    p.add_argument("--cast", default=None,
                   help='phan vai: "1,2:VOICE_A;3:VOICE_B" (cue theo so thu tu)')
    p.add_argument("--no-fit", action="store_true",
                   help="tat tu co audio vua khit cue")
    p.add_argument("--engine", choices=["capcut", "kokoro"], default="capcut",
                   help="capcut: API cloud (nhieu giong); kokoro: local Ngoc Huyen")
    p.add_argument("--jobs", type=int, default=4,
                   help="so luong TTS song song (capcut chunk / kokoro process)")
    p.add_argument("--workdir", default=None)
    p.set_defaults(fn=cmd_dub)

    p = sub.add_parser("burn", help="Burn sub (+audio) ra video moi")
    p.add_argument("video"); p.add_argument("--srt", default=None)
    p.add_argument("--ass", default=None, help="file ASS karaoke (uu tien hon --srt)")
    p.add_argument("--cover", default=None, help="che vung den: 'y:h' vd '1430:150'")
    p.add_argument("--frost", default=None, help="nen trang mo: 'y:h' vd '1430:150'")
    p.add_argument("--frost-srt", default=None,
                   help="SRT de thanh mo chi hien trong cac cue")
    p.add_argument("--frost-alpha", type=float, default=0.35,
                   help="do duc lop trang (0-1, mac dinh 0.35)")
    p.add_argument("--dodge", action="store_true",
                   help="lách ban quyen: crop 3%% + eq nhe")
    p.add_argument("--delogo", default=None,
                   help="lam mo logo: 'x:y:w:h' vd '500:20:180:60'")
    p.add_argument("--v916", choices=["off", "black", "blur", "square"],
                   default="off",
                   help="xuat 9:16: black=nen den, blur=nen mo, square=cat vuong + khung mau")
    p.add_argument("--banner-top", default="REVIEW PHIM HAY")
    p.add_argument("--banner-bottom", default="PHIM HAY MỖI NGÀY")
    p.add_argument("--banner-color", default="FFCC00",
                   help="mau khung (hex, mac dinh vang)")
    p.add_argument("--draft", action="store_true",
                   help="ban nhap: 720x1280, ultrafast, frost don gian (nhanh)")
    p.add_argument("--audio", default=None); p.add_argument("-o", "--out", default="final.mp4")
    p.add_argument("--font-size", type=int, default=22)
    p.add_argument("--margin-v", type=int, default=90)
    p.set_defaults(fn=cmd_burn)

    p = sub.add_parser("karaoke", help="SRT + word-timing STT -> ASS karaoke")
    p.add_argument("srt"); p.add_argument("--words", required=True,
                                         help="dub_words.json tu STT audio long tieng")
    p.add_argument("-o", "--out", default="karaoke.ass")
    p.add_argument("--font-size", type=int, default=64)
    p.add_argument("--margin-v", type=int, default=170)
    p.add_argument("--theme", choices=["pill", "frost"], default="pill",
                   help="pill: chu trang/nen den; frost: chu dam tren nen trang mo")
    p.add_argument("--bar-y", type=int, default=1430, help="frost: y thanh mo")
    p.add_argument("--bar-h", type=int, default=150, help="frost: cao thanh mo")
    p.add_argument("--wrap-chars", type=int, default=26,                   help="frost: so ky tu toi da moi dong")
    p.add_argument("--playres", default="1080x1920",
                   help="ASS PlayRes, vd 1920x1080 cho video ngang")
    p.set_defaults(fn=cmd_karaoke)

    p = sub.add_parser("voices", help="Liet ke giọng doc")
    p.add_argument("--lang", default="vi-VN")
    p.set_defaults(fn=cmd_voices)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
