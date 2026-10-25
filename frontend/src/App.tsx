import { useState } from "react";
import Dashboard from "./pages/Dashboard";
import JobDetail from "./pages/JobDetail";
import PresetManager from "./pages/PresetManager";

type Page = "dashboard" | "editor" | "presets";

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [editJob, setEditJob] = useState("");

  const nav = (p: Page) => setPage(p);

  return (
    <div>
      <nav style={{ display: "flex", gap: 16, padding: "12px 20px", background: "#222", color: "#fff", fontFamily: "system-ui" }}>
        <b style={{ color: "#FFCC00" }}>Reup Tool</b>
        <a onClick={() => nav("dashboard")} style={{ cursor: "pointer", textDecoration: page === "dashboard" ? "underline" : "none" }}>Dashboard</a>
        <a onClick={() => nav("editor")} style={{ cursor: "pointer", textDecoration: page === "editor" ? "underline" : "none" }}>Editor</a>
        <a onClick={() => nav("presets")} style={{ cursor: "pointer", textDecoration: page === "presets" ? "underline" : "none" }}>Preset</a>
      </nav>
      {page === "dashboard" && (
        <Dashboard onOpenJob={(id) => { setEditJob(id); setPage("editor"); }} />
      )}
      {page === "editor" && <JobDetail initialJobId={editJob} />}
      {page === "presets" && <PresetManager />}
    </div>
  );
}
