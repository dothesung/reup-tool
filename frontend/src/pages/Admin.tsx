import { useEffect, useState } from "react";

const API = "http://localhost:8000/api/v1";

export default function Admin() {
  const [status, setStatus] = useState<any>(null);
  const [items, setItems] = useState<any[]>([]);
  const [plan, setPlan] = useState("personal");
  const [months, setMonths] = useState(0);
  const [note, setNote] = useState("");
  const [newKey, setNewKey] = useState("");
  const [msg, setMsg] = useState("");
  const [copied, setCopied] = useState("");

  const load = async () => {
    const s = await fetch(`${API}/admin/status`).then(r => r.json()).catch(() => null);
    setStatus(s);
    if (s?.has_private_key) {
      const k = await fetch(`${API}/admin/keys`).then(r => r.json()).catch(() => ({ items: [] }));
      setItems(k.items || []);
    }
  };

  useEffect(() => { load(); }, []);

  const create = async () => {
    setMsg("Đang ký key...");
    const r = await fetch(`${API}/admin/keys`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan, months: plan === "personal" ? 0 : months, note }),
    });
    const d = await r.json();
    if (!r.ok) { setMsg("Lỗi: " + (d.detail || r.statusText)); return; }
    setNewKey(d.key);
    setMsg("Đã tạo key — gửi key này cho khách qua Zalo/email.");
    load();
  };

  const copy = (t: string, id: string) => {
    if (navigator.clipboard) navigator.clipboard.writeText(t).catch(() => {});
    setCopied(id);
    setTimeout(() => setCopied(""), 2000);
  };

  if (status && !status.has_private_key) {
    return (
      <div className="page">
        <h1>Admin — Quản lý key</h1>
        <div className="card">
          <p>⛔ Máy này không có file <span className="mono">license_private.pem</span> nên không tạo key được.</p>
          <p className="hint">Trang này chỉ chạy trên máy người bán (máy có private key). Máy khách mở trang này sẽ luôn thấy thông báo này — đó là thiết kế an toàn, không phải lỗi.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>Admin — Quản lý key</h1>
      <p className="page-subtitle">Tạo key bán cho khách và xem sổ key đã bán. Sổ chỉ nằm trên máy này (keys_issued.json, không push GitHub).</p>

      <div className="card">
        <div className="row" style={{ marginBottom: 12 }}>
          <select className="select" value={plan} onChange={e => setPlan(e.target.value)}>
            <option value="personal">Cá nhân — vĩnh viễn, 1 máy</option>
            <option value="pro">Pro — 3 máy</option>
            <option value="team">Team — 5 máy</option>
          </select>
          {plan !== "personal" && (
            <select className="select" value={months} onChange={e => setMonths(parseInt(e.target.value))}>
              <option value={1}>1 tháng</option>
              <option value={12}>12 tháng</option>
            </select>
          )}
          <input className="input input-flex" value={note} onChange={e => setNote(e.target.value)} placeholder="Ghi chú: tên khách / SĐT..." />
          <button className="btn btn-brand" onClick={create}>＋ Tạo key</button>
        </div>
        {msg && <div className="msg msg-info">{msg}</div>}
        {newKey && (
          <div className="row" style={{ marginTop: 12 }}>
            <input className="input input-flex mono" readOnly value={newKey} />
            <button className="btn btn-dark" onClick={() => copy(newKey, "new")}>{copied === "new" ? "✓ Đã sao chép" : "📋 Sao chép key"}</button>
          </div>
        )}
      </div>

      <h2>Sổ key đã bán ({items.length})</h2>
      <div className="table-wrap">
        <table className="data">
          <thead><tr><th>Ngày</th><th>Gói</th><th>Hạn</th><th>Ghi chú</th><th>Key</th><th></th></tr></thead>
          <tbody>
            {items.length === 0 && <tr><td colSpan={6}><div className="empty">Chưa bán key nào.</div></td></tr>}
            {items.map(it => (
              <tr key={it.id + it.issued}>
                <td>{it.issued}</td>
                <td>{it.plan}</td>
                <td>{it.months ? `${it.months} tháng` : "Vĩnh viễn"}</td>
                <td>{it.note || "—"}</td>
                <td className="mono">{it.key_preview}</td>
                <td><button className="btn btn-ghost btn-sm" onClick={() => copy(it.key, it.id)}>{copied === it.id ? "✓" : "📋 Sao chép"}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="hint">Lưu ý: key đã bán không thu hồi từ xa được (tool kiểm tra offline bằng chữ ký). Bán cho ai thì ghi chú rõ để đối soát.</p>
    </div>
  );
}
