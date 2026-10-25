import { useEffect, useState } from "react";

const API = "http://localhost:8000/api/v1";

export default function Dashboard({ onOpenJob }: { onOpenJob: (id: string) => void }) {
  const [jobs, setJobs] = useState<any[]>([]);
  const [url, setUrl] = useState("");
  const [preset, setPreset] = useState("review_phim");
  const [presets, setPresets] = useState<any[]>([]);
  const [msg, setMsg] = useState("");

  const refresh = async () => {
    const r = await fetch(`${API}/pipeline/jobs`);
    setJobs(await r.json());
    const p = await fetch(`${API}/presets`);
    setPresets(await p.json());
  };

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, []);

  const create = async () => {
    if (!url.trim()) return;
    setMsg("Đang tạo job...");
    const r = await fetch(`${API}/pipeline/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, preset }),
    });
    const j = await r.json();
    setMsg(`Đã tạo job ${j.id} — đang tải video...`);
    setUrl("");
    refresh();
  };

  const cont = async (id: string) => {
    await fetch(`${API}/pipeline/jobs/${id}/continue`, { method: "POST" });
    refresh();
  };

  const statusColor = (s: string) => {
    if (s === "done") return "green";
    if (s === "failed") return "red";
    if (s === "waiting_sub") return "orange";
    return "#333";
  };

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: 20, fontFamily: "system-ui" }}>
      <h1>Reup Tool — Dashboard</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <input
          value={url} onChange={e => setUrl(e.target.value)}
          placeholder="Dán link Douyin / YouTube..."
          style={{ flex: 1, padding: 10 }}
        />
        <select value={preset} onChange={e => setPreset(e.target.value)} style={{ padding: 10 }}>
          {presets.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
          {presets.length === 0 && <option value="review_phim">review_phim</option>}
        </select>
        <button onClick={create} style={{ padding: "10px 20px", background: "#FFCC00", border: "none", fontWeight: "bold", cursor: "pointer" }}>
          Tạo job
        </button>
      </div>
      {msg && <p style={{ color: "#666" }}>{msg}</p>}

      <h2>Danh sách job</h2>
      {jobs.length === 0 && <p style={{ color: "#999" }}>Chưa có job nào.</p>}
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead>
          <tr style={{ background: "#f5f5f5" }}>
            <th style={{ padding: 8, textAlign: "left" }}>ID</th>
            <th style={{ padding: 8, textAlign: "left" }}>URL</th>
            <th style={{ padding: 8, textAlign: "left" }}>Trạng thái</th>
            <th style={{ padding: 8, textAlign: "left" }}>Bước</th>
            <th style={{ padding: 8 }}></th>
          </tr>
        </thead>
        <tbody>
          {jobs.map(j => (
            <tr key={j.id} style={{ borderTop: "1px solid #eee" }}>
              <td style={{ padding: 8 }}>{j.id}</td>
              <td style={{ padding: 8, maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{j.url}</td>
              <td style={{ padding: 8, color: statusColor(j.status), fontWeight: "bold" }}>{j.status}</td>
              <td style={{ padding: 8 }}>{j.step || "—"}</td>
              <td style={{ padding: 8 }}>
                {j.status === "waiting_sub" && (
                  <button onClick={() => onOpenJob(j.id)} style={{ marginRight: 6 }}>Sửa sub/frost</button>
                )}
                {j.status === "waiting_sub" && (
                  <button onClick={() => cont(j.id)}>Chạy tiếp →</button>
                )}
                {j.drive_link && (
                  <a href={j.drive_link} target="_blank" rel="noreferrer">Drive ↗</a>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
