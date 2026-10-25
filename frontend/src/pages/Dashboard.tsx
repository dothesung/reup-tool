import { useEffect, useState } from "react";

const API = "http://localhost:8000/api/v1";

export default function Dashboard({ onOpenJob }: { onOpenJob: (id: string) => void }) {
  const [jobs, setJobs] = useState<any[]>([]);
  const [url, setUrl] = useState("");
  const [preset, setPreset] = useState("review_phim");
  const [presets, setPresets] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const [msgKind, setMsgKind] = useState("msg-info");

  const refresh = async () => {
    try {
      const r = await fetch(`${API}/pipeline/jobs`);
      setJobs(await r.json());
      const p = await fetch(`${API}/presets`);
      setPresets(await p.json());
    } catch { /* backend chưa chạy */ }
  };

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, []);

  const create = async () => {
    if (!url.trim()) return;
    setMsg("Đang tạo job..."); setMsgKind("msg-info");
    const r = await fetch(`${API}/pipeline/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, preset }),
    });
    const j = await r.json();
    setMsg(`Đã tạo job ${j.id} — đang tải video...`); setMsgKind("msg-ok");
    setUrl("");
    refresh();
  };

  const cont = async (id: string) => {
    await fetch(`${API}/pipeline/jobs/${id}/continue`, { method: "POST" });
    refresh();
  };

  const pill = (s: string) => {
    if (s === "done") return "pill pill-done";
    if (s === "failed") return "pill pill-failed";
    if (s === "waiting_sub") return "pill pill-waiting_sub";
    return "pill pill-default";
  };

  return (
    <div className="page">
      <h1>Dashboard</h1>
      <p className="page-subtitle">Tạo job reup mới, theo dõi tiến trình realtime (tự cập nhật mỗi 5 giây).</p>

      <div className="card">
        <div className="row">
          <input
            className="input input-flex" value={url} onChange={e => setUrl(e.target.value)}
            placeholder="Dán link Douyin / YouTube vào đây..."
            onKeyDown={e => e.key === "Enter" && create()}
          />
          <select className="select" value={preset} onChange={e => setPreset(e.target.value)}>
            {presets.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
            {presets.length === 0 && <option value="review_phim">review_phim</option>}
          </select>
          <button className="btn btn-brand" onClick={create}>＋ Tạo job</button>
        </div>
      </div>

      {msg && <div className={`msg ${msgKind}`}>{msg}</div>}

      <h2>Danh sách job ({jobs.length})</h2>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr><th>ID</th><th>Link video</th><th>Trạng thái</th><th>Bước hiện tại</th><th></th></tr>
          </thead>
          <tbody>
            {jobs.length === 0 && (
              <tr><td colSpan={5}><div className="empty">Chưa có job nào. Dán link ở trên để bắt đầu.</div></td></tr>
            )}
            {jobs.map(j => (
              <tr key={j.id}>
                <td className="mono">{j.id}</td>
                <td><div className="ellipsis" title={j.url}>{j.url}</div></td>
                <td><span className={pill(j.status)}>{j.status}</span></td>
                <td>{j.step || "—"}</td>
                <td style={{ whiteSpace: "nowrap" }}>
                  {j.status === "waiting_sub" && (
                    <button className="btn btn-ghost btn-sm" style={{ marginRight: 6 }} onClick={() => onOpenJob(j.id)}>Sửa sub/frost</button>
                  )}
                  {j.status === "waiting_sub" && (
                    <button className="btn btn-brand btn-sm" onClick={() => cont(j.id)}>Chạy tiếp →</button>
                  )}
                  {j.drive_link && (
                    <a href={j.drive_link} target="_blank" rel="noreferrer" style={{ marginLeft: 6 }}>Drive ↗</a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
