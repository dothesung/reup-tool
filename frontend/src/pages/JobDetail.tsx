import { useEffect, useState } from "react";
import VideoPreview from "../components/VideoPreview";
import SubEditor from "../components/SubEditor";
import { getJobInfo, getSubs, saveSubs, getFrost, saveFrost, detectText, translateSubs } from "../api";

export default function JobDetail({ initialJobId = "" }: { initialJobId?: string }) {
  const [jobId, setJobId] = useState(initialJobId);
  const [info, setInfo] = useState<any>(null);
  const [cues, setCues] = useState<any[]>([]);
  const [frost, setFrost] = useState<string | null>(null);
  const [cover, setCover] = useState<string | null>(null);
  const [detect, setDetect] = useState<any>(null);
  const [msg, setMsg] = useState("");
  const [tab, setTab] = useState<"frost" | "subs" | "caption">("frost");
  const [capTitle, setCapTitle] = useState("");
  const [capTags, setCapTags] = useState("");
  const [capOrig, setCapOrig] = useState("");
  const [capModel, setCapModel] = useState("");
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

  const onTranslateAI = async () => {
    setMsg("Đang dịch bằng AI..."); setMsgKind("msg-info");
    try {
      const r = await fetch(`http://localhost:8000/api/v1/jobs/${jobId}/translate-ai`, { method: "POST" });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || r.statusText);
      const s2 = await getSubs(jobId);
      setCues(s2.cues);
      setMsg(`Đã dịch AI ${d.count} cue bằng ${d.model}. Sửa tay rồi bấm Lưu.`);
      setMsgKind("msg-ok");
    } catch (e: any) {
      setMsg("Dịch AI lỗi: " + e.message + " — bật AI và nhập API key trong Cài đặt → tab AI."); setMsgKind("msg-err");
    }
  };

  const onCaptionAI = async () => {
    setMsg("Đang viết tiêu đề + hashtag bằng AI..."); setMsgKind("msg-info");
    try {
      const r = await fetch(`http://localhost:8000/api/v1/jobs/${jobId}/caption-ai`, { method: "POST" });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || r.statusText);
      setCapTitle(d.title); setCapTags(d.hashtags); setCapOrig(d.orig_title); setCapModel(d.model);
      setMsg(`AI (${d.model}) đã viết xong — sửa lại nếu muốn rồi bấm "Áp dụng cho job này".`); setMsgKind("msg-ok");
    } catch (e: any) {
      setMsg("Caption AI lỗi: " + e.message + " — bật AI và nhập API key trong Cài đặt → tab AI."); setMsgKind("msg-err");
    }
  };

  const onApplyCaption = async () => {
    setMsg("Đang lưu caption riêng cho job..."); setMsgKind("msg-info");
    try {
      const r = await fetch(`http://localhost:8000/api/v1/jobs/${jobId}/caption-override`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: capTitle, hashtags: capTags }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || r.statusText);
      setMsg("Đã lưu — khi bấm Chạy tiếp, caption.txt sẽ dùng tiêu đề + hashtag này thay mẫu chung."); setMsgKind("msg-ok");
    } catch (e: any) {
      setMsg("Lưu caption lỗi: " + e.message); setMsgKind("msg-err");
    }
  };

  const onTranslate = async () => {
    setMsg("Đang dịch máy... (Google/MyMemory miễn phí, có thể mất vài chục giây)"); setMsgKind("msg-info");
    try {
      const r = await translateSubs(jobId);
      const s = await getSubs(jobId);
      setCues(s.cues);
      setMsg(`Đã dịch máy ${r.count} cue bằng ${r.engine}${r.errors ? ` — ${r.errors} cue lỗi, giữ chữ gốc` : ""}. Sửa tay rồi bấm Lưu.`);
      setMsgKind(r.errors ? "msg-info" : "msg-ok");
    } catch (e: any) {
      setMsg("Dịch lỗi: " + e.message + " — kiểm tra email MyMemory trong Cài đặt hoặc viết tay."); setMsgKind("msg-err");
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
          <div className="tabs">
            <button className={tab === "frost" ? "tabbtn active" : "tabbtn"} onClick={() => setTab("frost")}>Frost / Cover</button>
            <button className={tab === "subs" ? "tabbtn active" : "tabbtn"} onClick={() => setTab("subs")}>Sub tiếng Việt ({cues.length} cue)</button>
            <button className={tab === "caption" ? "tabbtn active" : "tabbtn"} onClick={() => setTab("caption")}>✨ AI Caption</button>
          </div>
          {tab === "frost" && <div className="editor-grid">
            <div className="card">
              <VideoPreview
                jobId={jobId}
                frost={frost} cover={cover}
                onFrost={setFrost} onCover={setCover}
                cues={cues} videoName={info.video || null}
              />
            </div>
            <div>
              <div className="card">
                <button className="btn btn-ghost" style={{ marginBottom: 14 }} onClick={onDetect}>
                  🔍 Tự động phát hiện text cố định vs subtitle
                </button>
                {detect && <pre className="json">{JSON.stringify(detect, null, 2)}</pre>}
                <p className="hint">
                  Frost/cover chỉnh trực tiếp trên video bên trái, số liệu đồng bộ vào đây.
                  Frost hiện tại: <b>{frost || "—"}</b> · Cover: <b>{cover || "—"}</b>
                </p>
                <p className="hint">Video gốc {info.width}x{info.height}, dài {Number(info.duration).toFixed(1)}s.</p>
              </div>
            </div>
          </div>}

          {tab === "subs" && <div className="card">
            <div className="row" style={{ marginBottom: 12 }}>
              <button className="btn btn-ghost" onClick={onTranslate}>🤖 Dịch máy từ sub gốc</button>
              <button className="btn btn-ghost" onClick={onTranslateAI}>✨ Dịch bằng AI</button>
              <span className="hint" style={{ alignSelf: "center" }}>Bản dịch máy để sửa tay — không thay người dịch. Cần email MyMemory trong Cài đặt nếu Google bị chặn.</span>
            </div>
            <SubEditor cues={cues} onChange={setCues} />
          </div>}

          {tab === "caption" && <div className="card">
            <div className="row" style={{ marginBottom: 12 }}>
              <button className="btn btn-brand" onClick={onCaptionAI}>✨ Viết tiêu đề + hashtag bằng AI</button>
              <span className="hint" style={{ alignSelf: "center" }}>Dựa trên sub gốc + tiêu đề gốc. Chưa cấu hình AI? Vào Cài đặt → tab AI.</span>
            </div>
            {capOrig && <div className="hint" style={{ marginBottom: 12 }}>Tiêu đề gốc: {capOrig}{capModel ? ` · AI: ${capModel}` : ""}</div>}
            <div className="field">
              <label>Tiêu đề</label>
              <input className="input" value={capTitle} onChange={e => setCapTitle(e.target.value)} placeholder="Bấm 'Viết bằng AI' hoặc nhập tay" />
            </div>
            <div className="field">
              <label>Hashtag</label>
              <input className="input" value={capTags} onChange={e => setCapTags(e.target.value)} placeholder="#tag1 #tag2 ..." />
            </div>
            <div className="row" style={{ marginTop: 12 }}>
              <button className="btn btn-brand" onClick={onApplyCaption}>Áp dụng cho job này</button>
              <span className="hint" style={{ alignSelf: "center" }}>Chỉ áp cho job này, không đổi mẫu chung trong Cài đặt.</span>
            </div>
          </div>}

          <button className="btn btn-brand" style={{ padding: "14px 28px", fontSize: 16 }} onClick={onSave}>
            💾 Lưu sub + frost
          </button>
        </>
      )}
    </div>
  );
}
