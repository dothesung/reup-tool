import { useEffect, useState } from "react";

const API = "http://localhost:8000/api/v1";

export default function Setup() {
  const [checks, setChecks] = useState<any[]>([]);
  const [log, setLog] = useState<string[]>([]);
  const [installing, setInstalling] = useState(false);
  const [msg, setMsg] = useState("");

  const refresh = async () => {
    const d = await fetch(`${API}/setup/status`).then(r => r.json()).catch(() => null);
    if (d) setChecks(d.checks || []);
  };

  useEffect(() => {
    refresh();
    const t = setInterval(async () => {
      const d = await fetch(`${API}/setup/log`).then(r => r.json()).catch(() => null);
      if (d) { setLog(d.lines || []); setInstalling(d.installing); if (!d.installing) refresh(); }
    }, 2000);
    return () => clearInterval(t);
  }, []);

  const install = async (step: string) => {
    setMsg("Đang chạy...");
    const r = await fetch(`${API}/setup/install`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ step }),
    });
    const d = await r.json();
    setMsg(d.started ? "Đang cài — xem log bên dưới." : (d.note || "Không bắt đầu được"));
  };

  return (
    <div className="page">
      <h1>Thiết lập</h1>
      <p className="page-subtitle">Kiểm tra máy đã đủ phụ thuộc để chạy tool chưa, thiếu gì bấm cài nấy. Mở trang này đầu tiên khi chạy tool trên máy mới.</p>

      <div className="table-wrap">
        <table className="data">
          <thead><tr><th>Hạng mục</th><th>Trạng thái</th><th>Chi tiết</th><th></th></tr></thead>
          <tbody>
            {checks.map(c => (
              <tr key={c.id}>
                <td>{c.label}</td>
                <td>{c.ok ? "✅ Đạt" : "❌ Thiếu"}</td>
                <td style={{ maxWidth: 420, overflowWrap: "anywhere" }}>{c.detail}</td>
                <td>
                  {c.id === "sdk" && !c.ok && <button className="btn btn-brand btn-sm" onClick={() => install("sdk")}>Tải + cài SDK</button>}
                  {c.id === "ffmpeg" && !c.ok && <button className="btn btn-brand btn-sm" onClick={() => install("ffmpeg")}>Tải ffmpeg</button>}
                  {c.id === "pipeline_files" && !c.ok && <span className="hint">Kèm sẵn trong repo (thư mục cli/) — kiểm tra lại đường dẫn trong Cài đặt → Pipeline.</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="row" style={{ marginBottom: 10 }}>
          <button className="btn btn-dark" onClick={() => install("deps")}>📦 Cài thư viện Python (backend + pipeline)</button>
          <button className="btn btn-ghost" onClick={refresh}>🔄 Kiểm tra lại</button>
          <span className="hint" style={{ alignSelf: "center" }}>{msg}{installing ? " (đang chạy...)" : ""}</span>
        </div>
        <div className="hint" style={{ marginBottom: 8 }}>
          Kokoro (giọng Ngọc Huyền) không tự tải vì nặng (torch + model riêng). Muốn dùng: tải thư mục kokoro-vi về máy rồi chỉ đường dẫn trong Cài đặt → Lồng tiếng. Chưa có Kokoro vẫn chạy được bằng giọng CapCut.
        </div>
        {log.length > 0 && (
          <pre style={{ background: "#111", color: "#ddd", padding: 12, borderRadius: 8, maxHeight: 300, overflow: "auto", fontSize: 12, whiteSpace: "pre-wrap" }}>
            {log.join("\n")}
          </pre>
        )}
      </div>
    </div>
  );
}
