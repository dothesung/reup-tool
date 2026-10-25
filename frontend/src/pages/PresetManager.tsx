import { useEffect, useState } from "react";

const API = "http://localhost:8000/api/v1";

export default function PresetManager() {
  const [presets, setPresets] = useState<any[]>([]);
  const [selected, setSelected] = useState("");
  const [content, setContent] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    const r = await fetch(`${API}/presets`);
    const list = await r.json();
    setPresets(list);
    if (list.length > 0 && !selected) {
      setSelected(list[0].name);
      loadOne(list[0].name);
    }
  };

  const toYaml = (obj: any, indent = 0): string => {
    const pad = "  ".repeat(indent);
    return Object.entries(obj).map(([k, v]) => {
      if (v !== null && typeof v === "object" && !Array.isArray(v)) {
        return `${pad}${k}:\n${toYaml(v, indent + 1)}`;
      }
      return `${pad}${k}: ${v}`;
    }).join("\n");
  };

  const loadOne = async (name: string) => {
    const r = await fetch(`${API}/presets/${name}`);
    const p = await r.json();
    const { name: _, ...rest } = p;
    setContent(toYaml(rest));
    setSelected(name);
  };

  const save = async () => {
    await fetch(`${API}/presets/${selected}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    setMsg(`Đã lưu preset ${selected}`);
    load();
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="page">
      <h1>Preset</h1>
      <p className="page-subtitle">Cấu hình render mặc định cho từng loại video. Áp dụng khi tạo job mới.</p>

      <div className="card">
        <div className="row" style={{ marginBottom: 14 }}>
          <select className="select" value={selected} onChange={e => loadOne(e.target.value)}>
            {presets.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
          </select>
          <button className="btn btn-brand" onClick={save}>💾 Lưu preset</button>
        </div>
        <textarea
          className="textarea-code"
          value={content} onChange={e => setContent(e.target.value)}
          spellCheck={false}
        />
        {msg && <div className="msg msg-ok" style={{ marginTop: 12 }}>{msg}</div>}
        <p className="hint">
          Các key: v916 (square/black/blur), banner_top, banner_bottom, banner_color,
          frost_alpha, cover_alpha, voice, jobs, hwaccel (videotoolbox/nvenc).
        </p>
      </div>
    </div>
  );
}
