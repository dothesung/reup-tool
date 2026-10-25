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
};

export default function Settings() {
  const [form, setForm] = useState<any>({ ...DEFAULTS });
  const [presets, setPresets] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const [msgKind, setMsgKind] = useState("msg-info");
  const [fbSaved, setFbSaved] = useState(false);
  const [tab, setTab] = useState("general");
  const TABS = [
    { id: "general", label: "Chung" },
    { id: "pipeline", label: "Pipeline" },
    { id: "dub", label: "Lồng tiếng" },
    { id: "frame", label: "Khung & Che" },
    { id: "keys", label: "Key & Tích hợp" },
  ];

  useEffect(() => {
    (async () => {
      try {
        const s = await getSettings();
        const { _secrets_saved, ...rest } = s;
        setForm({ ...DEFAULTS, ...rest, facebook_page_token: "" });
        setFbSaved(!!_secrets_saved?.facebook_page_token);
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

      <div className="row">
        <button className="btn btn-brand" onClick={() => save()}>💾 Lưu cài đặt</button>
        <button className="btn btn-ghost" onClick={reset}>↺ Về mặc định</button>
      </div>
    </div>
  );
}
