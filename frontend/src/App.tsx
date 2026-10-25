import { useState } from "react";
import Dashboard from "./pages/Dashboard";
import JobDetail from "./pages/JobDetail";
import PresetManager from "./pages/PresetManager";

type Page = "dashboard" | "editor" | "presets";

function parseHash(): { page: Page; job: string } {
  const parts = window.location.hash.replace("#/", "").split("/");
  const p = parts[0];
  const page: Page = p === "editor" || p === "presets" ? p : "dashboard";
  return { page, job: parts[1] || "" };
}

export default function App() {
  const initial = parseHash();
  const [page, setPage] = useState<Page>(initial.page);
  const [editJob, setEditJob] = useState(initial.job);

  const go = (p: Page, job = "") => {
    window.location.hash = job ? `#/${p}/${job}` : `#/${p}`;
    setPage(p);
    if (job) setEditJob(job);
  };

  return (
    <div>
      <nav className="nav">
        <div className="nav-brand">Reup Tool <span>v1.1</span></div>
        <a className={page === "dashboard" ? "active" : ""} onClick={() => go("dashboard")}>Dashboard</a>
        <a className={page === "editor" ? "active" : ""} onClick={() => go("editor")}>Editor</a>
        <a className={page === "presets" ? "active" : ""} onClick={() => go("presets")}>Preset</a>
      </nav>
      {page === "dashboard" && (
        <Dashboard onOpenJob={(id) => go("editor", id)} />
      )}
      {page === "editor" && <JobDetail initialJobId={editJob} />}
      {page === "presets" && <PresetManager />}
    </div>
  );
}
