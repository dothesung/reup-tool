import { useEffect, useState } from "react";
import { getSettings, saveSettings, getPresets } from "../api";

const DEFAULTS: any = {
  brand_name: "Reup Tool", admin_contact: "0981228722",
  default_preset: "review_phim", default_src_lang: "zh-CN",
  auto_upload: true, share_drive_link: false, output_mode: "final",
  title_template: "{title}", hashtags: "",
  engine: "kokoro", jobs: 4, capcut_voice: "", max_parallel_jobs: 2, with_sub: false, v916: "square",
  banner_top: "REVIEW PHIM HAY", banner_bottom: "PHIM HAY MỖI NGÀY",
  banner_color: "FFCC00", frost_alpha: 0.2, frost_auto: false,
  nexray_url: "", facebook_page_id: "", facebook_page_token: "", translate_email: "",
  capcut_dir: "", capcut_py: "", kokoro_dir: "", kokoro_py: "",
  llm_enabled: false, llm_provider: "deepseek", llm_base_url: "", llm_api_key: "", llm_model: "",
};

export default function Settings() {
  const [form, setForm] = useState<any>({ ...DEFAULTS });
  const [presets, setPresets] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const [msgKind, setMsgKind] = useState("msg-info");
  const [fbSaved, setFbSaved] = useState(false);
  const [llmSaved, setLlmSaved] = useState(false);
  const [llmTest, setLlmTest] = useState("");
  const LLM_PRESETS: Record<string, string> = {
    openai: "https://api.openai.com/v1",
    deepseek: "https://api.deepseek.com/v1",
    openrouter: "https://openrouter.ai/api/v1",
    gemini: "https://generativelanguage.googleapis.com/v1beta/openai/",
    "gemini-free": "https://api-gemini.zinghay-com.workers.dev/v1",
    custom: "",
  };
  const LLM_MODELS: Record<string, string> = {
    openai: "gpt-4o-mini",
    deepseek: "deepseek-chat",
    gemini: "gemini-2.0-flash",
    "gemini-free": "gemini-free",
    openrouter: "",
    custom: "",
  };
  const onProvider = (pv: string) => {
    setForm((f: any) => {
      const cur = f.llm_base_url || "";
      const isPreset = Object.values(LLM_PRESETS).includes(cur);
      return {
        ...f,
        llm_provider: pv,
        llm_base_url: pv === "custom" ? cur : (cur === "" || isPreset ? LLM_PRESETS[pv] : cur),
        llm_model: f.llm_model === "" ? LLM_MODELS[pv] : f.llm_model,
      };
    });
  };
  const testLlm = async () => {
    setLlmTest("Đang kiểm tra kết nối...");
    try {
      const r = await fetch("http://localhost:8000/api/v1/settings/llm-test", { method: "POST" });
      const d = await r.json();
      if (!r.ok) { setLlmTest("Lỗi: " + (d.detail || r.statusText)); return; }
      setLlmTest(`OK — model ${d.model}, trả lời: ${d.reply} (${d.ms}ms)`);
    } catch (e: any) { setLlmTest("Lỗi: " + e.message); }
  };
  const [tab, setTab] = useState("general");
  const TABS = [
    { id: "general", label: "Chung" },
    { id: "pipeline", label: "Pipeline" },
    { id: "dub", label: "Lồng tiếng" },
    { id: "frame", label: "Khung & Che" },
    { id: "keys", label: "Key & Tích hợp" },
    { id: "ai", label: "AI" },
  ];

  useEffect(() => {
    (async () => {
      try {
        const s = await getSettings();
        const { _secrets_saved, ...rest } = s;
        setForm({ ...DEFAULTS, ...rest, facebook_page_token: "" });
        setFbSaved(!!_secrets_saved?.facebook_page_token);
        setLlmSaved(!!_secrets_saved?.llm_api_key);
        setPresets(await getPresets());
      } catch { setMsg("Không kết nối được backend."); setMsgKind("msg-err"); }
    })();
  }, []);

  const set = (k: string, v: any) => setForm((f: any) => ({ ...f, [k]: v }));

  const save = async (data?: any) => {
    const body = data || form;
    setMsg("Đang lưu..."); setMsgKind("msg-info");
    try {
      const s = await saveSettings(body);
      const { _secrets_saved, ...rest } = s;
      setForm({ ...rest, facebook_page_token: "" });
      setFbSaved(!!_secrets_saved?.facebook_page_token);
      setMsg("Đã lưu cài đặt. Job mới sẽ dùng các giá trị này làm mặc định.");
      setMsgKind("msg-ok");
    } catch (e: any) {
      setMsg("Lưu lỗi: " + e.message); setMsgKind("msg-err");
    }
  };

  const reset = () => {
    if (!confirm("Về toàn bộ cài đặt mặc định?")) return;
    setForm({ ...DEFAULTS });
    save({ ...DEFAULTS });
  };

  const field = (label: string, node: React.ReactNode, hint?: string) => (
    <div className="field">
      <label>{label}</label>
      {node}
      {hint && <div className="hint">{hint}</div>}
    </div>
  );

  const check = (label: string, k: string, hint?: string) => (
    <div className="field">
      <label className="check">
        <input type="checkbox" checked={!!form[k]} onChange={e => set(k, e.target.checked)} />
        {label}
      </label>
      {hint && <div className="hint">{hint}</div>}
    </div>
  );

  return (
    <div className="page">
      <h1>Cài đặt</h1>
      <p className="page-subtitle">
        Cấu hình chung áp dụng cho mọi job mới — các giá trị ở đây đè lên preset
        cho các mục trùng nhau. Key chỉ lưu trên máy này (file settings.json, không push lên GitHub).
      </p>
      <div className="tabs">
        {TABS.map(t => (
          <button key={t.id} className={tab === t.id ? "tabbtn active" : "tabbtn"} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>
      {msg && <div className={`msg ${msgKind}`}>{msg}</div>}

      {tab === "general" && <div className="card">
        <h2 className="section-title">Thương hiệu &amp; mặc định</h2>
        <div className="grid2">
          {field("Tên hiển thị trên thanh nav", <input className="input" value={form.brand_name} onChange={e => set("brand_name", e.target.value)} />, "Đổi tên khi bàn giao cho khách hàng khác.")}
          {field("Zalo / SĐT liên hệ mua key", <input className="input" value={form.admin_contact} onChange={e => set("admin_contact", e.target.value)} />, "Hiện ở Dashboard (khối Mua key) và chân trang.")}
          {field("Preset mặc định", <select className="select" value={form.default_preset} onChange={e => set("default_preset", e.target.value)}>
            {presets.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
            {presets.length === 0 && <option value="review_phim">review_phim</option>}
          </select>)}
          {field("Ngôn ngữ gốc (STT)", <select className="select" value={form.default_src_lang} onChange={e => set("default_src_lang", e.target.value)}>
            <option value="zh-CN">Tiếng Trung (zh-CN)</option>
            <option value="en-US">Tiếng Anh (en-US)</option>
            <option value="vi-VN">Tiếng Việt (vi-VN)</option>
          </select>)}
        </div>
      </div>}

      {tab === "pipeline" && <div className="card">
        <h2 className="section-title">Pipeline &amp; xuất bản</h2>
        <div className="grid2">
          {field("Chế độ xuất", <select className="select" value={form.output_mode} onChange={e => set("output_mode", e.target.value)}>
            <option value="final">Bản final (1080x1920)</option>
            <option value="draft">Bản nháp (720x1280, nhanh)</option>
          </select>)}
          {field("Số job chạy cùng lúc (1–5)", <input className="input" type="number" min={1} max={5} value={form.max_parallel_jobs} onChange={e => set("max_parallel_jobs", parseInt(e.target.value) || 2)} />, "Job vượt giới hạn sẽ xếp hàng chờ, không ngốn RAM.")}
          {field("Thư mục pipeline capcut-tts", <input className="input" value={form.capcut_dir} onChange={e => set("capcut_dir", e.target.value)} placeholder="Để trống = tự tìm (ưu tiên ~/workspace/capcut-tts rồi tới cli/ kèm repo)" />, "Chỉ điền khi tool báo không tìm thấy thư mục pipeline. Lỗi cũ: [Errno 2] No such file or directory là do đường dẫn này sai/thiếu.")}
          {field("Python chạy pipeline (tùy chọn)", <input className="input" value={form.capcut_py} onChange={e => set("capcut_py", e.target.value)} placeholder="Để trống = python đang chạy backend" />)}
          {field("Mẫu tiêu đề caption", <input className="input" value={form.title_template} onChange={e => set("title_template", e.target.value)} placeholder="{title}" />, "{title} = tiêu đề gốc. VD: REVIEW PHIM | {title}")}
          {field("Hashtag thêm vào cuối caption", <input className="input" value={form.hashtags} onChange={e => set("hashtags", e.target.value)} placeholder="#reviewphim #phimhay" />, "Áp dụng cho caption.txt và mô tả khi đăng Fanpage.")}
          {check("Tự động up lên Google Drive khi xong", "auto_upload", "Tắt = chỉ render file local, không up Drive.")}
          {check("Chia sẻ link Drive công khai (anyone with link)", "share_drive_link")}
        </div>
      </div>}

      {tab === "dub" && <div className="card">
        <h2 className="section-title">Lồng tiếng</h2>
        <div className="grid2">
          {field("Engine lồng tiếng", <select className="select" value={form.engine} onChange={e => set("engine", e.target.value)}>
            <option value="kokoro">Kokoro — giọng Ngọc Huyền (mặc định)</option>
            <option value="capcut">CapCut TTS</option>
          </select>)}
          {form.engine === "capcut" && field("ID giọng CapCut", <input className="input" list="capcut-voices" value={form.capcut_voice} onChange={e => set("capcut_voice", e.target.value)} placeholder="Để trống = giọng mặc định SDK" />, "Gợi ý: BV560_streaming (Alex Đại Đế), BV074_streaming (Cô Gái Hoạt Ngôn).")}
          {form.engine === "capcut" && <datalist id="capcut-voices"><option value="BV560_streaming" /><option value="BV074_streaming" /><option value="BV421_vivn_streaming" /></datalist>}
          {field("Số luồng TTS song song (1–8)", <input className="input" type="number" min={1} max={8} value={form.jobs} onChange={e => set("jobs", parseInt(e.target.value) || 4)} />)}
          {check("Burn sub Việt lên video", "with_sub", "Mặc định: chỉ dub + che sub cũ, không burn sub.")}
          {field("Thư mục kokoro-vi (tùy chọn)", <input className="input" value={form.kokoro_dir} onChange={e => set("kokoro_dir", e.target.value)} placeholder="VD: ~/kokoro-vi (chứa batch_synth.py)" />, "Chỉ cần khi dùng giọng Kokoro Ngọc Huyền. Để trống = dùng đường dẫn mặc định của máy dev (sẽ lỗi trên máy mới).")}
          {field("Python chạy Kokoro (tùy chọn)", <input className="input" value={form.kokoro_py} onChange={e => set("kokoro_py", e.target.value)} placeholder="Để trống = python đang chạy backend" />)}
        </div>
      </div>}

      {tab === "frame" && <div className="card">
        <h2 className="section-title">Khung 9:16 &amp; che sub</h2>
        <div className="grid2">
          {field("Chế độ khung dọc", <select className="select" value={form.v916} onChange={e => set("v916", e.target.value)}>
            <option value="square">Square — crop vuông + khung màu (video ngang)</option>
            <option value="black">Black — nền đen trên dưới</option>
            <option value="blur">Blur — nền mờ từ video</option>
            <option value="auto">Auto — square nếu video ngang</option>
            <option value="off">Tắt — giữ nguyên khung gốc</option>
          </select>, "Video dọc sẵn 9:16 không áp khung (giữ nguyên).")}
          {field("Chữ khung trên", <input className="input" value={form.banner_top} onChange={e => set("banner_top", e.target.value)} />)}
          {field("Chữ khung dưới", <input className="input" value={form.banner_bottom} onChange={e => set("banner_bottom", e.target.value)} />)}
          {field("Màu khung (hex, không #)", <div className="row"><input className="input" value={form.banner_color} onChange={e => set("banner_color", e.target.value)} /><input type="color" value={"#" + (form.banner_color || "FFCC00")} onChange={e => set("banner_color", e.target.value.replace("#", ""))} /></div>)}
          {field("Độ mờ thanh che sub cũ (0.05–0.9)", <input className="input" type="number" min={0.05} max={0.9} step={0.05} value={form.frost_alpha} onChange={e => set("frost_alpha", parseFloat(e.target.value) || 0.2)} />, "Chuẩn hiện tại: 0.2 (mờ nhẹ trong suốt).")}
          {check("Tự phát hiện vùng sub cũ khi không set tay", "frost_auto", "Đúng ~80% — nên kiểm bằng Frost Editor.")}
        </div>
      </div>}

      {tab === "keys" && <div className="card">
        <h2 className="section-title">Tích hợp &amp; Key</h2>
        <div className="grid2">
          {field("Nexray API URL (tải video)", <input className="input" value={form.nexray_url} onChange={e => set("nexray_url", e.target.value)} placeholder="Để trống = dùng mặc định" />, "Điền khi tự host nexray riêng (tránh chặn IP).")}
          {field("Email cho MyMemory (dịch miễn phí)", <input className="input" value={form.translate_email} onChange={e => set("translate_email", e.target.value)} placeholder="Để trống = quota ẩn danh thấp" />, "Có email → quota dịch 50.000 ký tự/ngày. Chỉ dùng làm mã quota, không phải mật khẩu.")}
          {field("Facebook Page ID", <input className="input" value={form.facebook_page_id} onChange={e => set("facebook_page_id", e.target.value)} placeholder="VD: 123456789..." />)}
          {field("Facebook Page Access Token", <input className="input" type="password" value={form.facebook_page_token} onChange={e => set("facebook_page_token", e.target.value)} placeholder={fbSaved ? "Đã lưu •••• — nhập mới để thay" : "Chưa lưu — dán token vào đây"} />, "Để trống = giữ nguyên key cũ. Token dùng cho tính năng Đăng Fanpage (sắp ra mắt).")}
        </div>
        <div className="hint">Google Drive dùng OAuth qua hatch CLI nên không cần nhập key. File settings.json đã nằm trong .gitignore — không push lên GitHub.</div>
      </div>}

      {tab === "ai" && <div className="card">
        <h2 className="section-title">AI — Dịch phụ đề &amp; viết caption (chuẩn OpenAI-compatible)</h2>
        <div className="grid2">
          {check("Bật tính năng AI", "llm_enabled", "Tắt = nút Dịch AI / Caption AI báo chưa bật.")}
          {field("Nhà cung cấp", <select className="select" value={form.llm_provider} onChange={e => onProvider(e.target.value)}>
            <option value="deepseek">DeepSeek (rẻ, dịch tốt)</option>
            <option value="openai">OpenAI</option>
            <option value="openrouter">OpenRouter (nhiều model)</option>
            <option value="gemini">Google Gemini (chế độ OpenAI-compat)</option>
            <option value="gemini-free">Gemini Free (proxy zinghay — 1 model gemini-free)</option>
            <option value="custom">Tùy chỉnh (LM Studio / Ollama / proxy riêng)</option>
          </select>)}
          {field("Base URL", <input className="input" value={form.llm_base_url} onChange={e => set("llm_base_url", e.target.value)} placeholder="https://api.deepseek.com/v1" />, "Đổi provider sẽ tự điền URL chuẩn (nếu ô đang trống hoặc đang là URL preset khác).")}
          {field("API Key", <input className="input" type="password" value={form.llm_api_key} onChange={e => set("llm_api_key", e.target.value)} placeholder={llmSaved ? "Đã lưu •••• — nhập mới để thay" : "Dán API key vào đây"} />, "Để trống = giữ nguyên key cũ. Key lưu local, API chỉ hiện •••• + 4 ký tự cuối.")}
          {field("Model", <input className="input" value={form.llm_model} onChange={e => set("llm_model", e.target.value)} placeholder={LLM_MODELS[form.llm_provider] || "nhập tên model"} />)}
        </div>
        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn btn-dark" onClick={testLlm}>🔌 Kiểm tra kết nối</button>
          {llmTest && <span className="hint" style={{ alignSelf: "center" }}>{llmTest}</span>}
        </div>
        <div className="hint" style={{ marginTop: 10 }}>Dịch AI và Caption AI dùng chung cấu hình này. Muốn đổi nhà cung cấp chỉ cần đổi 3 ô trên, không sửa code.</div>
      </div>}

      <div className="row">
        <button className="btn btn-brand" onClick={() => save()}>💾 Lưu cài đặt</button>
        <button className="btn btn-ghost" onClick={reset}>↺ Về mặc định</button>
      </div>
    </div>
  );
}
