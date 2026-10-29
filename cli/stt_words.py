"""STT 1 file audio -> dub_words.json (word timing) de lam karaoke."""
import sys, json, tempfile, subprocess
sys.path.insert(0, "/home/hatch/workspace/capcut-tts")
from reup_sub import get_client

src, out = sys.argv[1], sys.argv[2]
tmp = tempfile.mkdtemp()
wav = f"{tmp}/a.wav"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src,
                "-ar", "16000", "-ac", "1", wav], check=True)
client = get_client()
stt = client.transcribe_file(wav, language="vi-VN", timeout=300)
payload = json.loads(stt["data"]["tasks"][0]["payload"])
res = []
for u in payload["utterances"]:
    res.append({
        "start": u["start_time"], "end": u["end_time"],
        "text": u.get("text", ""),
        "words": [{"t": w.get("text", ""), "s": w.get("start_time", 0),
                   "e": w.get("end_time", 0)} for w in u.get("words", [])],
    })
json.dump(res, open(out, "w"), ensure_ascii=False)
print(f"OK: {out} ({len(res)} utterances)")
