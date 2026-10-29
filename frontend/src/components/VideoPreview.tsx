import { useRef, useState } from "react";

interface Props {
  jobId: string;
  frost: string | null;
  cover: string | null;
  onFrost: (v: string | null) => void;
  onCover: (v: string | null) => void;
  cues: any[];
  videoName: string | null;
}

const EH = 1280; // không gian editor (720x1280)

const parseYH = (s: string | null) => {
  if (!s) return null;
  const [y, h] = s.split(":").map(Number);
  if (isNaN(y) || isNaN(h)) return null;
  return { y, h };
};

const parseTime = (t: string): number => {
  const m = t.match(/(?:(\d+):)?(\d+):(\d+)[,.](\d+)/);
  if (!m) return 0;
  return (+m[1] || 0) * 3600 + (+m[2]) * 60 + (+m[3]) + (+m[4]) / 1000;
};

type Drag = {
  kind: "move" | "resize" | "create";
  band: "frost" | "cover";
  startClientY: number;
  origY: number;
  origH: number;
  prev: string | null;
} | null;

/**
 * VideoPreview: xem trước video với frost/cover áp TRỰC TIẾP lên hình,
 * kéo-thả chỉnh live. Frost chỉ hiện khi đang trong cue sub (đúng bản final),
 * có nút "luôn hiện" để căn vùng.
 */
export default function VideoPreview({ jobId, frost, cover, onFrost, onCover, cues, videoName }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [mode, setMode] = useState<"frost" | "cover">("frost");
  const [alwaysShow, setAlwaysShow] = useState(true);
  const [drag, setDrag] = useState<Drag>(null);

  const setBand = (band: "frost" | "cover", v: string | null) =>
    band === "frost" ? onFrost(v) : onCover(v);
  const getBand = (band: "frost" | "cover") => (band === "frost" ? frost : cover);

  const activeCue = cues.find(c => { const s = parseTime(c.start), e = parseTime(c.end); return s <= t && t <= e; });
  const frostVisible = !!frost && (alwaysShow || !!activeCue);

  const yAt = (clientY: number) => {
    const rect = stageRef.current!.getBoundingClientRect();
    return Math.max(0, Math.min(EH, (clientY - rect.top) / rect.height * EH));
  };

  const captureOnStage = (e: React.PointerEvent) => {
    // Mọi drag đều capture về stage để onPointerMove/onPointerUp luôn chạy
    try { stageRef.current!.setPointerCapture(e.pointerId); } catch { /* ignore */ }
  };

  const onStageDown = (e: React.PointerEvent) => {
    const el = e.target as HTMLElement;
    if (el.closest(".band") || el.closest("video")) return; // band tự xử lý, video để bấm play
    const y0 = yAt(e.clientY);
    captureOnStage(e);
    setDrag({ kind: "create", band: mode, startClientY: e.clientY, origY: y0, origH: 0, prev: getBand(mode) });
  };

  const onBandDown = (e: React.PointerEvent, band: "frost" | "cover") => {
    e.stopPropagation();
    const b = parseYH(getBand(band))!;
    captureOnStage(e);
    setDrag({ kind: "move", band, startClientY: e.clientY, origY: b.y, origH: b.h, prev: getBand(band) });
  };

  const onHandleDown = (e: React.PointerEvent, band: "frost" | "cover") => {
    e.stopPropagation();
    const b = parseYH(getBand(band))!;
    captureOnStage(e);
    setDrag({ kind: "resize", band, startClientY: e.clientY, origY: b.y, origH: b.h, prev: getBand(band) });
  };

  const onMove = (e: React.PointerEvent) => {
    if (!drag) return;
    const rect = stageRef.current!.getBoundingClientRect();
    const dy = (e.clientY - drag.startClientY) / rect.height * EH;
    if (drag.kind === "move") {
      const y = Math.round(Math.max(0, Math.min(EH - drag.origH, drag.origY + dy)));
      setBand(drag.band, `${y}:${drag.origH}`);
    } else if (drag.kind === "resize") {
      const h = Math.round(Math.max(20, Math.min(EH - drag.origY, drag.origH + dy)));
      setBand(drag.band, `${drag.origY}:${h}`);
    } else {
      const y1 = yAt(e.clientY);
      const y = Math.round(Math.min(drag.origY, y1));
      const h = Math.round(Math.abs(y1 - drag.origY));
      setBand(drag.band, `${y}:${h}`);
    }
  };

  const onUp = () => {
    if (drag?.kind === "create") {
      const b = parseYH(getBand(drag.band));
      if (!b || b.h < 10) setBand(drag.band, drag.prev); // kéo quá ngắn = hủy
    }
    setDrag(null);
  };

  const togglePlay = () => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) v.play(); else v.pause();
  };

  const numInput = (band: "frost" | "cover", key: "y" | "h", label: string) => {
    const b = parseYH(getBand(band));
    return (
      <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
        {label}
        <input className="input" type="number" style={{ width: 76 }}
          value={b ? b[key] : ""} placeholder="—"
          onChange={e => {
            const v = Math.max(0, Number(e.target.value) || 0);
            const cur = parseYH(getBand(band)) || { y: 0, h: 100 };
            const ny = key === "y" ? Math.min(EH - cur.h, v) : cur.y;
            const nh = key === "h" ? Math.max(20, Math.min(EH - ny, v)) : cur.h;
            setBand(band, `${ny}:${nh}`);
          }} />
      </label>
    );
  };

  const renderBand = (band: "frost" | "cover") => {
    const val = getBand(band);
    const b = parseYH(val);
    if (!b) return null;
    const visible = band === "cover" ? true : frostVisible;
    if (!visible) return null;
    return (
      <div className={`band band-${band}`} style={{ top: `${b.y / EH * 100}%`, height: `${b.h / EH * 100}%` }}
        onPointerDown={e => onBandDown(e, band)}>
        <span className="band-label">{band === "frost" ? "FROST" : "COVER"} {val}</span>
        <div className="band-handle" onPointerDown={e => onHandleDown(e, band)} title="Kéo để đổi chiều cao" />
      </div>
    );
  };

  if (!videoName) return <div className="hint">Workdir chưa có video để preview.</div>;

  return (
    <div>
      <div className="row" style={{ marginBottom: 10, flexWrap: "wrap" }}>
        <button className={`btn btn-mode ${mode === "frost" ? "on" : ""}`} onClick={() => setMode("frost")}>▓ Frost (che sub cũ)</button>
        <button className={`btn btn-mode ${mode === "cover" ? "on" : ""}`} onClick={() => setMode("cover")}>▓ Cover (text cố định)</button>
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
          <input type="checkbox" checked={alwaysShow} onChange={e => setAlwaysShow(e.target.checked)} /> Luôn hiện frost
        </label>
        <button className="btn btn-ghost btn-sm" onClick={() => { onFrost(null); onCover(null); }}>Xóa hết</button>
      </div>

      <div ref={stageRef} className="video-stage"
        onPointerDown={onStageDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}>
        <video ref={videoRef} src={`http://localhost:8000/api/v1/jobs/${jobId}/video`}
          preload="metadata" playsInline
          onTimeUpdate={e => setT((e.target as HTMLVideoElement).currentTime)}
          onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)}
          onClick={togglePlay} />
        <div className="video-overlay">
          {renderBand("frost")}
          {renderBand("cover")}
          {activeCue && <div className="sub-overlay">{activeCue.text}</div>}
        </div>
      </div>

      <div className="row" style={{ marginTop: 10, alignItems: "center" }}>
        <button className="btn btn-dark btn-sm" onClick={togglePlay}>{playing ? "⏸ Tạm dừng" : "▶ Phát"}</button>
        <span className="mono" style={{ fontSize: 13 }}>{t.toFixed(1)}s</span>
        {videoName === "final.mp4" && <span className="hint">Đang xem bản final (src.mp4 đã bị dọn)</span>}
      </div>

      <div className="row" style={{ marginTop: 10 }}>
        <span style={{ fontSize: 13 }}><b>Frost:</b> {frost || "—"}</span>
        {numInput("frost", "y", "Y:")}{numInput("frost", "h", "Cao:")}
        <button className="btn btn-ghost btn-sm" onClick={() => onFrost(null)}>Xóa</button>
      </div>
      <div className="row" style={{ marginTop: 6 }}>
        <span style={{ fontSize: 13 }}><b>Cover:</b> {cover || "—"}</span>
        {numInput("cover", "y", "Y:")}{numInput("cover", "h", "Cao:")}
        <button className="btn btn-ghost btn-sm" onClick={() => onCover(null)}>Xóa</button>
      </div>

      <p className="hint" style={{ marginTop: 10 }}>
        Kéo trên video để vẽ vùng {mode === "frost" ? "frost" : "cover"} mới · kéo thân vùng để di chuyển ·
        kéo mép dưới để đổi chiều cao · frost xem trước đúng hiệu ứng mờ như bản final.
      </p>
    </div>
  );
}
