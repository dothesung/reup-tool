import { useEffect, useState } from "react";
import Dashboard from "./pages/Dashboard";
import JobDetail from "./pages/JobDetail";
import PresetManager from "./pages/PresetManager";
import Settings from "./pages/Settings";
import Admin from "./pages/Admin";
import LicenseModal from "./components/LicenseModal";
import { getSettings } from "./api";

type Page = "dashboard" | "editor" | "presets" | "settings" | "admin";

function parseHash(): { page: Page; job: string } {
  const parts = window.location.hash.replace("#/", "").split("/");
  const p = parts[0];
  const page: Page = p === "editor" || p === "presets" || p === "settings" || p === "admin" ? p : "dashboard";
  return { page, job: parts[1] || "" };
}

export default function App() {
  const initial = parseHash();
  const [page, setPage] = useState<Page>(initial.page);
  const [editJob, setEditJob] = useState(initial.job);
  const [brand, setBrand] = useState("Reup Tool");  const [contact, setContact] = useState("0981228722");
  const [license, setLicense] = useState<any>(null);
  const [showLicense, setShowLicense] = useState(false);

  const refreshLicense = () => {
    fetch("http://localhost:8000/api/v1/license").then(r => r.json()).then(setLicense).catch(() => {});
  };

  useEffect(() => {
    getSettings().then(s => { if (s.brand_name) setBrand(s.brand_name); if (s.admin_contact) setContact(s.admin_contact); }).catch(() => {});
    refreshLicense();
  }, []);

  const go = (p: Page, job = "") => {
    window.location.hash = job ? `#/${p}/${job}` : `#/${p}`;
    setPage(p);
    if (job) setEditJob(job);
  };

  const licenseLabel = () => {
    if (!license) return "Key";
    if (license.mode === "licensed") return `🔑 ${license.plan}`;
    if (license.mode === "trial") return `🆓 Dùng thử: ${license.days_left} ngày / ${license.videos_left} video`;
    if (license.mode === "dev") return "🛠 Dev";
    return "⛔ Hết hạn — bấm để nhập key";
  };

  return (
    <div>
      <nav className="nav">
        <div className="nav-brand">{brand} <span>v1.8</span></div>
        <a className={page === "dashboard" ? "active" : ""} onClick={() => go("dashboard")}>Dashboard</a>
        <a className={page === "editor" ? "active" : ""} onClick={() => go("editor")}>Editor</a>
        <a className={page === "presets" ? "active" : ""} onClick={() => go("presets")}>Preset</a>
        <a className={page === "settings" ? "active" : ""} onClick={() => go("settings")}>⚙ Cài đặt</a>
        <a className={page === "admin" ? "active" : ""} onClick={() => go("admin")}>Admin</a>
      </nav>
      <div className="license-bar">
        <span>{licenseLabel()}</span>
        <button className="btn btn-ghost btn-sm" onClick={() => setShowLicense(true)}>Key &amp; mã máy</button>
      </div>
      {showLicense && (
        <LicenseModal license={license} contact={contact} onClose={() => setShowLicense(false)} onActivated={refreshLicense} />
      )}
      {page === "dashboard" && (
        <Dashboard onOpenJob={(id) => go("editor", id)} />
      )}
      {page === "editor" && <JobDetail initialJobId={editJob} />}
      {page === "presets" && <PresetManager />}
      {page === "settings" && <Settings />}
      {page === "admin" && <Admin />}
      <footer className="footer">
        {brand} — Hỗ trợ &amp; mua key: Zalo/SĐT {contact}
      </footer>
    </div>
  );
}
