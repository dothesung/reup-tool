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

  const loadOne = async (name: string) => {
    const r = await fetch(`${API}/presets/${name}`);
    const p = await r.json();
    // Hiển thị lại dạng YAML đơn giản
    const { name: _, ...rest } = p;
    setContent(Object.entries(rest).map(([k, v]) => `${k}: ${v}`).join("\n"));
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
    <div style={{ maxWidth: 900, margin: "0 auto", padding: 20, fontFamily: "system-ui" }}>
      <h1>Preset Manager</h1>
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <select value={selected} onChange={e => loadOne(e.target.value)} style={{ padding: 8 }}>
          {presets.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
        </select>
        <button onClick={save} style={{ padding: "8px 16px", background: "#FFCC00", border: "none", fontWeight: "bold" }}>
          Lưu preset
        </button>
      </div>
      <textarea
        value={content} onChange={e => setContent(e.target.value)}
        style={{ width: "100%", height: 400, fontFamily: "monospace", padding: 12 }}
        spellCheck={false}
      />
      {msg && <p style={{ color: "green" }}>{msg}</p>}
      <p style={{ fontSize: 13, color: "#666" }}>
        Các key: v916 (square/black/blur), banner_top, banner_bottom, banner_color,
        frost_alpha, cover_alpha, voice, jobs, hwaccel (videotoolbox/nvenc).
      </p>
    </div>
  );
}
