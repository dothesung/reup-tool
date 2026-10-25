import { useState } from "react";

interface Props {
  license: any;
  contact: string;
  onClose: () => void;
  onActivated: () => void;
}

const API = "http://localhost:8000/api/v1";

export function copyText(t: string, done: () => void) {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(t).then(done).catch(() => done());
  } else {
    const ta = document.createElement("textarea");
    ta.value = t; document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); } catch { /* ignore */ }
    document.body.removeChild(ta); done();
  }
}

export default function LicenseModal({ license, contact, onClose, onActivated }: Props) {
  const [key, setKey] = useState("");
  const [msg, setMsg] = useState("");
  const [copied, setCopied] = useState(false);

  const activate = async () => {
    if (!key.trim()) return;
    setMsg("Đang kích hoạt...");
    const r = await fetch(`${API}/license/activate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: key.trim() }),
    });
    if (!r.ok) {
      const e = await r.json().catch(() => ({}));
      setMsg("Lỗi: " + (e.detail || r.statusText));
      return;
    }
    onActivated();
    onClose();
  };

  const statusText = () => {
    if (!license) return "Đang tải...";
    if (license.mode === "licensed") return `Bản quyền: ${license.plan}${license.exp ? ` — hết hạn ${license.exp}` : " — vĩnh viễn"}`;
    if (license.mode === "trial") return `Dùng thử: còn ${license.days_left} ngày / ${license.videos_left} video`;
    if (license.mode === "dev") return "Chế độ dev (bypass license)";
    if (license.mode === "expired") return "Hết dùng thử / key hết hạn";
    return "Key không hợp lệ";
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-head">
          <b>🔑 Bản quyền</b>
          <button className="btn-del" onClick={onClose}>✕</button>
        </div>

        <p>{statusText()}</p>

        <div className="field">
          <label>Mã máy của bạn (gửi mã này cho admin khi mua key / xin reset)</label>
          <div className="row">
            <input className="input input-flex mono" readOnly value={license?.machine_id || ""} />
            <button className="btn btn-dark" onClick={() => copyText(license?.machine_id || "", () => { setCopied(true); setTimeout(() => setCopied(false), 2000); })}>
              {copied ? "✓ Đã sao chép" : "📋 Sao chép"}
            </button>
          </div>
        </div>

        {license?.mode !== "licensed" && license?.mode !== "dev" && (
          <div className="hint" style={{ marginBottom: 14 }}>
            💳 <b>Mua key:</b> liên hệ admin qua Zalo/SĐT <b>{contact}</b> — nhắn kèm mã máy ở trên
            và gói muốn mua (Cá nhân 1.490.000đ vĩnh viễn / Pro 249.000đ/tháng / Team 599.000đ/tháng).
            Chuyển khoản xong admin gửi key, dán vào ô dưới để kích hoạt.
          </div>
        )}

        <div className="field">
          <label>Nhập key bản quyền</label>
          <div className="row">
            <input className="input input-flex" value={key} onChange={e => setKey(e.target.value)} placeholder="RT-..." onKeyDown={e => e.key === "Enter" && activate()} />
            <button className="btn btn-brand" onClick={activate}>Kích hoạt</button>
          </div>
          {msg && <div className="hint" style={{ marginTop: 6 }}>{msg}</div>}
        </div>
      </div>
    </div>
  );
}
