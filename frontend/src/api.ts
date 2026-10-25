const API = "http://localhost:8000/api/v1";

export async function getJobInfo(jid: string) {
  const r = await fetch(`${API}/jobs/${jid}/info`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getSubs(jid: string) {
  const r = await fetch(`${API}/jobs/${jid}/subs`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function saveSubs(jid: string, cues: any[]) {
  const r = await fetch(`${API}/jobs/${jid}/subs`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cues }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function detectText(jid: string) {
  const r = await fetch(`${API}/jobs/${jid}/detect`, { method: "POST" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getFrost(jid: string) {
  const r = await fetch(`${API}/jobs/${jid}/frost`);
  return r.json();
}

export async function saveFrost(jid: string, cfg: any) {
  const r = await fetch(`${API}/jobs/${jid}/frost`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cfg),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getSettings() {
  const r = await fetch(`${API}/settings`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function saveSettings(body: any) {
  const r = await fetch(`${API}/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getPresets() {
  const r = await fetch(`${API}/presets`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export function frameUrl(jid: string, t: number, w = 720) {
  return `${API}/jobs/${jid}/frame?t=${t}&w=${w}`;
}
