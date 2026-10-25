import { useRef, useState, useEffect } from "react";
import { frameUrl } from "../api";

interface Props {
  jobId: string;
  videoW: number;
  videoH: number;
  duration: number;
  initialFrost: string | null;
  initialCover: string | null;
  onChange: (frost: string | null, cover: string | null) => void;
}

/**
 * FrostEditor: kéo-thả chọn vùng frost/cover trên frame video.
 * Tọa độ theo canvas output 720x1280 (square).
 */
export default function FrostEditor({ jobId, videoW, videoH, duration, initialFrost, initialCover, onChange }: Props) {
  const [time, setTime] = useState(Math.min(10, Math.max(1, Math.floor(duration / 2) || 5)));
  const [mode, setMode] = useState<"frost" | "cover">("frost");
  const [frost, setFrost] = useState<string | null>(initialFrost);
  const [cover, setCover] = useState<string | null>(initialCover);
  const [drag, setDrag] = useState<{ y0: number } | null>(null);
  const imgRef = useRef<HTMLDivElement>(null);

  const CW = 360;
  const SCALE = CW / 720;

  useEffect(() => { onChange(frost, cover); }, [frost, cover]);

  const parseYH = (s: string | null) => {
    if (!s) return null;
    const [y, h] = s.split(":").map(Number);
    return { y, h };
  };

  const frostBox = parseYH(frost);
  const coverBox = parseYH(cover);

  const onPointerDown = (e: React.PointerEvent) => {
    const rect = imgRef.current!.getBoundingClientRect();
    const y = (e.clientY - rect.top) / rect.height * 1280;
    setDrag({ y0: y });
  };

  const onPointerUp = (e: React.PointerEvent) => {
    if (!drag) return;
    const rect = imgRef.current!.getBoundingClientRect();
    const y1 = (e.clientY - rect.top) / rect.height * 1280;
    const y = Math.round(Math.min(drag.y0, y1));
    const h = Math.round(Math.abs(y1 - drag.y0));
    if (h < 10) { setDrag(null); return; }
    const val = `${y}:${h}`;
    if (mode === "frost") setFrost(val); else setCover(val);
    setDrag(null);
  };

  return (
    <div>
      <div className="row" style={{ marginBottom: 14 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
          Thời điểm (s):
          <input className="input" type="number" value={time} min={0} max={Math.floor(duration)} onChange={e => setTime(Math.min(Number(e.target.value), Math.floor(duration)))} style={{ width: 80 }} />
        </label>
        <button className={`btn btn-mode ${mode === "frost" ? "on" : ""}`} onClick={() => setMode("frost")}>
          ▓ Frost (phụ đề)
        </button>
        <button className={`btn btn-mode ${mode === "cover" ? "on" : ""}`} onClick={() => setMode("cover")}>
          ▓ Cover (text cố định)
        </button>
        <button className="btn btn-ghost" onClick={() => { setFrost(null); setCover(null); }}>Xóa hết</button>
      </div>

      <div ref={imgRef} onPointerDown={onPointerDown} onPointerUp={onPointerUp} className="frame-box">
        <img src={frameUrl(jobId, time)} alt="frame" style={{ width: "100%", height: "100%", objectFit: "cover", pointerEvents: "none" }} draggable={false} />
        {frostBox && (
          <div className="frost-box" style={{ top: frostBox.y * SCALE, height: frostBox.h * SCALE }}>
            FROST {frost}
          </div>
        )}
        {coverBox && (
          <div className="cover-box" style={{ top: coverBox.y * SCALE, height: coverBox.h * SCALE }}>
            COVER {cover}
          </div>
        )}
      </div>

      <p className="hint">
        Kéo chuột trên khung hình để chọn vùng {mode === "frost" ? "frost (che phụ đề)" : "cover (che text cố định)"}.
        Tọa độ output 720x1280. Video gốc {videoW}x{videoH}.
      </p>
      <p style={{ fontSize: 14 }}>
        Frost hiện tại: <b>{frost || "—"}</b> &nbsp;|&nbsp; Cover: <b>{cover || "—"}</b>
      </p>
    </div>
  );
}
