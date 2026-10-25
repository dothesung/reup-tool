import { useEffect, useState } from "react";

const API = "http://localhost:8000/api/v1";

export default function Dashboard({ onOpenJob }: { onOpenJob: (id: string) => void }) {
  const [jobs, setJobs] = useState<any[]>([]);
  const [url, setUrl] = useState("");
  const [preset, setPreset] = useState("review_phim");
  const [presets, setPresets] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const [msgKind, setMsgKind] = useState("msg-info");
  const [presetLoaded, setPresetLoaded] = useState(false);
  const [license, setLicense] = useState<any>(null);
  const [keyInput, setKeyInput] = useState("");
  const [adminContact, setAdminContact] = useState("0981228722");

  const refreshLicense = async () => {
    try {
      const r = await fetch(`${API}/license`);
      setLicense(await r.json());
      const s = await fetch(`${API}/settings`);
      const st = await s.json();
      if (st.admin_contact) setAdminContact(st.admin_contact);
    } catch { /* backend chưa chạy */ }
  };

  const activate = async () => {
    if (!keyInput.trim()) return;
    setMsg("Đang kích hoạt key..."); setMsgKind("msg-info");
    const r = await fetch(`${API}/license/activate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: keyInput.trim() }),
    });
    if (!r.ok) {
      const e = await r.json().catch(() => ({}));
      setMsg("Kích hoạt lỗi: " + (e.detail || r.statusText)); setMsgKind("msg-err");
      return;
    }
    setLicense(await r.json());
    setKeyInput("");
    setMsg("Kích hoạt thành công."); setMsgKind("msg-ok");
  };

  const refresh = async () => {
    try {
      const r = await fetch(`${API}/pipeline/jobs`);
      setJobs(await r.json());
      const p = await fetch(`${API}/presets`);
      setPresets(await p.json());
      if (!presetLoaded) {
        const s = await fetch(`${API}/settings`);
        const st = await s.json();
        if (st.default_preset) setPreset(st.default_preset);
        setPresetLoaded(true);
      }
    } catch { /* backend chưa chạy */ }
  };

  useEffect(() => {
    refresh();
    refreshLicense();
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

  const postFB = async (id: string) => {
    setMsg("Đang đăng lên Fanpage... (video 15s mất ~1 phút)"); setMsgKind("msg-info");
    const r = await fetch(`${API}/pipeline/jobs/${id}/post-facebook`, { method: "POST" });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      setMsg("Đăng FB lỗi: " + (d.detail || r.statusText)); setMsgKind("msg-err");
      return;
    }
    setMsg(`Đã đăng Fanpage: ${d.url}`); setMsgKind("msg-ok");
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

      {license && (
        <div className="card">
          <div className="row">
            <span>
              {license.mode === "licensed" && <>✅ Bản quyền: <b>{license.plan}</b>{license.exp ? ` — hết hạn ${license.exp}` : " — vĩnh viễn"}</>}
              {license.mode === "trial" && <>🆓 Dùng thử: còn <b>{license.days_left} ngày</b> / <b>{license.videos_left} video</b></>}
              {license.mode === "dev" && <>🛠 Chế độ dev (bypass license)</>}
              {(license.mode === "expired" || license.mode === "invalid") && <>⛔ {license.mode === "expired" ? "Hết dùng thử / key hết hạn" : "Key không hợp lệ"} — nhập key bên dưới để tiếp tục</>}
            </span>
          </div>
          {license.mode !== "licensed" && license.mode !== "dev" && (
            <>
              <div className="hint" style={{ marginTop: 10 }}>
                💳 <b>Mua key:</b> liên hệ admin qua Zalo/SĐT <b>{adminContact}</b> — nhắn kèm mã máy <span className="mono">{license.machine_id}</span> và gói muốn mua
                (Cá nhân 1.490.000đ vĩnh viễn / Pro 249.000đ/tháng / Team 599.000đ/tháng).
                Chuyển khoản xong admin gửi key, dán vào ô dưới để kích hoạt.
              </div>
              <div className="row" style={{ marginTop: 10 }}>
                <input className="input input-flex" value={keyInput} onChange={e => setKeyInput(e.target.value)} placeholder="Dán key bản quyền (RT-...) vào đây..." />
                <button className="btn btn-dark" onClick={activate}>🔑 Kích hoạt</button>
              </div>
            </>
          )}
        </div>
      )}

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
                  {j.status === "done" && (
                    <button className="btn btn-ghost btn-sm" style={{ marginLeft: 6 }} onClick={() => postFB(j.id)}>📘 Đăng Fanpage</button>
                  )}
                  {j.fb_post_id && (
                    <a href={`https://www.facebook.com/${j.fb_post_id}`} target="_blank" rel="noreferrer" style={{ marginLeft: 6 }}>Bài FB ↗</a>
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
