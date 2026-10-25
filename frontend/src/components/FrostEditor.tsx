import { useRef, useState, useEffect } from "react";
import { frameUrl } from "../api";

interface Props {
  jobId: string;
  videoW: number;
  videoH: number;
  initialFrost: string | null;
  initialCover: string | null;
  onChange: (frost: string | null, cover: string | null) => void;
}

/**
 * FrostEditor: kéo-thả chọn vùng frost/cover trên frame video.
 * Tọa độ hiển thị theo canvas 720x1280 (output square).
 * Chuyển đổi: frame gốc 1920x1080 → output square 720x1280
 * (scale = 720/1080, offset y = 280).
 */
export default function FrostEditor({ jobId, videoW, videoH, initialFrost, initialCover, onChange }: Props) {
  const [time, setTime] = useState(30);
  const [mode, setMode] = useState<"frost" | "cover">("frost");
  const [frost, setFrost] = useState<string | null>(initialFrost);
  const [cover, setCover] = useState<string | null>(initialCover);
  const [drag, setDrag] = useState<{ y0: number } | null>(null);
  const imgRef = useRef<HTMLDivElement>(null);

  // Tỉ lệ canvas hiển thị: rộng 360px, cao 640px (tỉ lệ 9:16)
  const CW = 360, CH = 640;
  // Output thật: 720x1280 → tỉ lệ hiển thị = 0.5
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
      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <label>
          Thời điểm (s):{" "}
          <input type="number" value={time} min={0} onChange={e => setTime(Number(e.target.value))} style={{ width: 70 }} />
        </label>
        <button onClick={() => setMode("frost")} style={{ background: mode === "frost" ? "#FFCC00" : "#eee" }}>
          Frost (phụ đề)
        </button>
        <button onClick={() => setMode("cover")} style={{ background: mode === "cover" ? "#FFCC00" : "#eee" }}>
          Cover (text cố định)
        </button>
        <button onClick={() => { setFrost(null); setCover(null); }}>Xóa hết</button>
      </div>

      <div
        ref={imgRef}
        onPointerDown={onPointerDown}
        onPointerUp={onPointerUp}
        style={{ position: "relative", width: CW, height: CH, border: "2px solid #333", cursor: "crosshair", overflow: "hidden", background: "#000" }}
      >
        <img src={frameUrl(jobId, time)} alt="frame" style={{ width: "100%", height: "100%", objectFit: "cover", pointerEvents: "none" }} draggable={false} />
        {/* Frost box */}
        {frostBox && (
          <div style={{
            position: "absolute", left: 0, right: 0,
            top: frostBox.y * SCALE, height: frostBox.h * SCALE,
            background: "rgba(255,255,255,0.35)", border: "2px dashed #FFCC00",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 12, fontWeight: "bold", color: "#333",
          }}>
            FROST {frost}
          </div>
        )}
        {/* Cover box */}
        {coverBox && (
          <div style={{
            position: "absolute", left: 0, right: 0,
            top: coverBox.y * SCALE, height: coverBox.h * SCALE,
            background: "rgba(255,0,0,0.25)", border: "2px dashed red",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 12, fontWeight: "bold", color: "#fff",
          }}>
            COVER {cover}
          </div>
        )}
      </div>

      <p style={{ fontSize: 13, color: "#666" }}>
        Kéo chuột trên khung hình để chọn vùng {mode === "frost" ? "frost (che phụ đề)" : "cover (che text cố định)"}.
        Tọa độ output 720x1280. Video gốc {videoW}x{videoH}.
      </p>
      <p style={{ fontSize: 13 }}>
        Frost hiện tại: <b>{frost || "—"}</b> | Cover: <b>{cover || "—"}</b>
      </p>
    </div>
  );
}
