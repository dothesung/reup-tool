import { useEffect, useState } from "react";
import FrostEditor from "../components/FrostEditor";
import SubEditor from "../components/SubEditor";
import { getJobInfo, getSubs, saveSubs, getFrost, saveFrost, detectText } from "../api";

export default function JobDetail({ initialJobId = "" }: { initialJobId?: string }) {
  const [jobId, setJobId] = useState(initialJobId);
  const [info, setInfo] = useState<any>(null);
  const [cues, setCues] = useState<any[]>([]);
  const [frost, setFrost] = useState<string | null>(null);
  const [cover, setCover] = useState<string | null>(null);
  const [detect, setDetect] = useState<any>(null);
  const [msg, setMsg] = useState("");
  const [msgKind, setMsgKind] = useState("msg-info");

  // Phân giải ID: pipeline job id (12 ký tự hex) → workdir basename
  const resolveId = async (id: string): Promise<string> => {
    if (/^[0-9a-f]{12}$/.test(id)) {
      try {
        const r = await fetch(`http://localhost:8000/api/v1/pipeline/jobs/${id}`);
        if (r.ok) {
          const j = await r.json();
          if (j.workdir) return j.workdir.split("/").pop();
        }
      } catch { /* rơi xuống dùng id gốc */ }
    }
    return id;
  };

  const load = async (idOverride?: string) => {
    const raw = (idOverride ?? jobId).trim();
    if (!raw) { setMsg("Nhập Job ID (workdir hoặc pipeline id) rồi bấm Tải job."); setMsgKind("msg-info"); return; }
    setMsg("Đang tải..."); setMsgKind("msg-info");
    try {
      const id = await resolveId(raw);
      if (id !== raw) setJobId(id);
      const [i, s, f] = await Promise.all([getJobInfo(id), getSubs(id), getFrost(id)]);
      setInfo(i);
      setCues(s.cues);
      setFrost(f.frost);
      setCover(f.cover);
      setMsg("");
    } catch (e: any) {
      setMsg("Lỗi: " + e.message); setMsgKind("msg-err");
    }
  };

  useEffect(() => { if (initialJobId) load(initialJobId); }, []);

  const onDetect = async () => {
    setMsg("Đang phân tích text..."); setMsgKind("msg-info");
    try {
      const d = await detectText(jobId);
      setDetect(d);
      setMsg("");
    } catch (e: any) {
      setMsg("Lỗi detect: " + e.message); setMsgKind("msg-err");
    }
  };

  const onSave = async () => {
    setMsg("Đang lưu..."); setMsgKind("msg-info");
    try {
      await saveSubs(jobId, cues);
      await saveFrost(jobId, { frost, cover, frost_alpha: 0.2, cover_alpha: 0.3 });
      setMsg("Đã lưu sub + frost."); setMsgKind("msg-ok");
    } catch (e: any) {
      setMsg("Lỗi lưu: " + e.message); setMsgKind("msg-err");
    }
  };

  return (
    <div className="page">
      <h1>Editor</h1>
      <p className="page-subtitle">Chọn vùng frost/cover trên khung hình và sửa sub tiếng Việt trước khi chạy tiếp.</p>

      <div className="card">
        <div className="row">
          <input className="input input-flex" value={jobId} onChange={e => setJobId(e.target.value)} placeholder="Job ID — workdir (vd: 1025_u_f5Qv9Ods0) hoặc pipeline id" />
          <button className="btn btn-dark" onClick={() => load()}>Tải job</button>
        </div>
      </div>

      {msg && <div className={`msg ${msgKind}`}>{msg}</div>}
      {info && (
        <p className="hint">
          Video: {info.width}x{info.height} — {info.duration}s
        </p>
      )}

      {info && (
        <>
          <h2>1. Frost / Cover — kéo-thả trên khung hình</h2>
          <div className="card">
            <button className="btn btn-ghost" style={{ marginBottom: 14 }} onClick={onDetect}>
              🔍 Tự động phát hiện text cố định vs subtitle
            </button>
            {detect && <pre className="json">{JSON.stringify(detect, null, 2)}</pre>}
            <FrostEditor
              jobId={jobId}
              videoW={info.width}
              videoH={info.height}
              duration={info.duration}
              initialFrost={frost}
              initialCover={cover}
              onChange={(f, c) => { setFrost(f); setCover(c); }}
            />
          </div>

          <h2>2. Sub tiếng Việt</h2>
          <div className="card">
            <SubEditor cues={cues} onChange={setCues} />
          </div>

          <button className="btn btn-brand" style={{ padding: "14px 28px", fontSize: 16 }} onClick={onSave}>
            💾 Lưu sub + frost
          </button>
        </>
      )}
    </div>
  );
}
