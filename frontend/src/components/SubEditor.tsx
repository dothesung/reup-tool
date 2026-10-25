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
      <div className="row" style={{ marginBottom: 12 }}>
        <input
          className="input input-flex"
          placeholder="🔍 Tìm trong sub..."
          value={filter}
          onChange={e => setFilter(e.target.value)}
        />
        <span className="hint" style={{ alignSelf: "center" }}>{cues.length} cue</span>
      </div>
      <div className="sub-scroll">
        <table className="data">
          <thead>
            <tr>
              <th style={{ width: 36 }}>#</th>
              <th style={{ width: 118 }}>Bắt đầu</th>
              <th style={{ width: 118 }}>Kết thúc</th>
              <th>Nội dung tiếng Việt</th>
              <th style={{ width: 40 }}></th>
            </tr>
          </thead>
          <tbody>
            {shown.map((c) => {
              const i = cues.indexOf(c);
              return (
                <tr key={c.id}>
                  <td>{i + 1}</td>
                  <td><input className="sub-time" value={c.start} onChange={e => update(i, "start", e.target.value)} /></td>
                  <td><input className="sub-time" value={c.end} onChange={e => update(i, "end", e.target.value)} /></td>
                  <td><input className="sub-input" value={c.text} onChange={e => update(i, "text", e.target.value)} /></td>
                  <td><button className="btn-del" onClick={() => remove(i)} title="Xóa cue">✕</button></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
