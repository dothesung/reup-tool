import { useEffect, useState } from "react";
import Dashboard from "./pages/Dashboard";
import JobDetail from "./pages/JobDetail";
import PresetManager from "./pages/PresetManager";
import Settings from "./pages/Settings";
import { getSettings } from "./api";

type Page = "dashboard" | "editor" | "presets" | "settings";

function parseHash(): { page: Page; job: string } {
  const parts = window.location.hash.replace("#/", "").split("/");
  const p = parts[0];
  const page: Page = p === "editor" || p === "presets" || p === "settings" ? p : "dashboard";
  return { page, job: parts[1] || "" };
}

export default function App() {
  const initial = parseHash();
  const [page, setPage] = useState<Page>(initial.page);
  const [editJob, setEditJob] = useState(initial.job);
  const [brand, setBrand] = useState("Reup Tool");
  const [contact, setContact] = useState("0981228722");

  useEffect(() => {
    getSettings().then(s => { if (s.brand_name) setBrand(s.brand_name); if (s.admin_contact) setContact(s.admin_contact); }).catch(() => {});
  }, []);

  const go = (p: Page, job = "") => {
    window.location.hash = job ? `#/${p}/${job}` : `#/${p}`;
    setPage(p);
    if (job) setEditJob(job);
  };

  return (
    <div>
      <nav className="nav">
        <div className="nav-brand">{brand} <span>v1.6</span></div>
        <a className={page === "dashboard" ? "active" : ""} onClick={() => go("dashboard")}>Dashboard</a>
        <a className={page === "editor" ? "active" : ""} onClick={() => go("editor")}>Editor</a>
        <a className={page === "presets" ? "active" : ""} onClick={() => go("presets")}>Preset</a>
        <a className={page === "settings" ? "active" : ""} onClick={() => go("settings")}>⚙ Cài đặt</a>
      </nav>
      {page === "dashboard" && (
        <Dashboard onOpenJob={(id) => go("editor", id)} />
      )}
      {page === "editor" && <JobDetail initialJobId={editJob} />}
      {page === "presets" && <PresetManager />}
      {page === "settings" && <Settings />}
      <footer className="footer">
        {brand} — Hỗ trợ &amp; mua key: Zalo/SĐT {contact}
      </footer>
    </div>
  );
}
