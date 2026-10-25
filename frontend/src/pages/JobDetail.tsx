import { useEffect, useState } from "react";
import FrostEditor from "../components/FrostEditor";
import SubEditor from "../components/SubEditor";
import { getJobInfo, getSubs, saveSubs, getFrost, saveFrost, detectText } from "../api";

export default function JobDetail() {
  const [jobId, setJobId] = useState("1023_YJkMwY9badg");
  const [info, setInfo] = useState<any>(null);
  const [cues, setCues] = useState<any[]>([]);
  const [frost, setFrost] = useState<string | null>(null);
  const [cover, setCover] = useState<string | null>(null);
  const [detect, setDetect] = useState<any>(null);
  const [msg, setMsg] = useState("");

  const load = async () => {
    setMsg("Đang tải...");
    try {
      const [i, s, f] = await Promise.all([getJobInfo(jobId), getSubs(jobId), getFrost(jobId)]);
      setInfo(i);
      setCues(s.cues);
      setFrost(f.frost);
      setCover(f.cover);
      setMsg("");
    } catch (e: any) {
      setMsg("Lỗi: " + e.message);
    }
  };

  useEffect(() => { load(); }, []);

  const onDetect = async () => {
    setMsg("Đang phân tích text...");
    try {
      const d = await detectText(jobId);
      setDetect(d);
      setMsg("");
    } catch (e: any) {
      setMsg("Lỗi detect: " + e.message);
    }
  };

  const onSave = async () => {
    setMsg("Đang lưu...");
    try {
      await saveSubs(jobId, cues);
      await saveFrost(jobId, { frost, cover, frost_alpha: 0.2, cover_alpha: 0.3 });
      setMsg("Đã lưu sub + frost.");
    } catch (e: any) {
      setMsg("Lỗi lưu: " + e.message);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: 20, fontFamily: "system-ui" }}>
      <h1>Reup Tool — Job Editor</h1>
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <input value={jobId} onChange={e => setJobId(e.target.value)} style={{ flex: 1, padding: 8 }} placeholder="Job ID (vd: 1023_YJkMwY9badg)" />
        <button onClick={load} style={{ padding: "8px 16px" }}>Tải job</button>
      </div>
      {msg && <p style={{ color: msg.startsWith("Lỗi") ? "red" : "green" }}>{msg}</p>}
      {info && (
        <p style={{ fontSize: 14, color: "#666" }}>
          Video: {info.width}x{info.height} — {info.duration}s — {info.workdir}
        </p>
      )}

      {info && (
        <>
          <h2>1. Frost / Cover (kéo-thả trên khung hình)</h2>
          <button onClick={onDetect} style={{ marginBottom: 12, padding: "6px 12px" }}>
            Tự động phát hiện text cố định vs subtitle
          </button>
          {detect && (
            <pre style={{ background: "#f5f5f5", padding: 12, fontSize: 12, overflowX: "auto" }}>
              {JSON.stringify(detect, null, 2)}
            </pre>
          )}
          <FrostEditor
            jobId={jobId}
            videoW={info.width}
            videoH={info.height}
            initialFrost={frost}
            initialCover={cover}
            onChange={(f, c) => { setFrost(f); setCover(c); }}
          />

          <h2 style={{ marginTop: 32 }}>2. Sub tiếng Việt</h2>
          <SubEditor cues={cues} onChange={setCues} />

          <button onClick={onSave} style={{ marginTop: 20, padding: "12px 24px", background: "#FFCC00", border: "none", fontWeight: "bold", fontSize: 16, cursor: "pointer" }}>
            Lưu sub + frost
          </button>
        </>
      )}
    </div>
  );
}
