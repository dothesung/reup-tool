import { useState } from "react";

interface Cue {
  id: number;
  start: string;
  end: string;
  text: string;
}

interface Props {
  cues: Cue[];
  onChange: (cues: Cue[]) => void;
}

export default function SubEditor({ cues, onChange }: Props) {
  const [filter, setFilter] = useState("");

  const update = (i: number, field: keyof Cue, val: string) => {
    const next = [...cues];
    next[i] = { ...next[i], [field]: val };
    onChange(next);
  };

  const remove = (i: number) => {
    onChange(cues.filter((_, j) => j !== i));
  };

  const shown = cues.filter(c =>
    filter === "" || c.text.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <input
          placeholder="Tìm trong sub..."
          value={filter}
          onChange={e => setFilter(e.target.value)}
          style={{ flex: 1, padding: 6 }}
        />
        <span style={{ fontSize: 13, color: "#666", alignSelf: "center" }}>
          {cues.length} cue
        </span>
      </div>
      <div style={{ maxHeight: 500, overflowY: "auto", border: "1px solid #ddd" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ background: "#f5f5f5", position: "sticky", top: 0 }}>
              <th style={{ padding: 6, textAlign: "left", width: 30 }}>#</th>
              <th style={{ padding: 6, textAlign: "left", width: 110 }}>Bắt đầu</th>
              <th style={{ padding: 6, textAlign: "left", width: 110 }}>Kết thúc</th>
              <th style={{ padding: 6, textAlign: "left" }}>Nội dung tiếng Việt</th>
              <th style={{ padding: 6, width: 30 }}></th>
            </tr>
          </thead>
          <tbody>
            {shown.map((c) => {
              const i = cues.indexOf(c);
              return (
                <tr key={c.id} style={{ borderTop: "1px solid #eee" }}>
                  <td style={{ padding: 6 }}>{i + 1}</td>
                  <td style={{ padding: 6 }}>
                    <input value={c.start} onChange={e => update(i, "start", e.target.value)} style={{ width: 100 }} />
                  </td>
                  <td style={{ padding: 6 }}>
                    <input value={c.end} onChange={e => update(i, "end", e.target.value)} style={{ width: 100 }} />
                  </td>
                  <td style={{ padding: 6 }}>
                    <input value={c.text} onChange={e => update(i, "text", e.target.value)} style={{ width: "100%" }} />
                  </td>
                  <td style={{ padding: 6 }}>
                    <button onClick={() => remove(i)} title="Xóa cue">✕</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
