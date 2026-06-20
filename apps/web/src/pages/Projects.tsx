import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Project } from "../api";

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [repo, setRepo] = useState("");
  const [stack, setStack] = useState("");
  const [error, setError] = useState("");

  const load = () => { api.projects().then(setProjects).catch(() => {}); };
  useEffect(load, []);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.createProject({ name, code: code || name.slice(0, 8).toUpperCase(), repo_url: repo || undefined, tech_stack: stack || undefined });
      setName(""); setCode(""); setRepo(""); setStack(""); setOpen(false);
      load();
    } catch (err) { setError((err as Error).message); }
  };

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Projects</h1>
          <p>Each project is a workspace: requirements → AI stories → prioritize → code + tests → PR.</p>
        </div>
        <button className="btn" onClick={() => setOpen((o) => !o)}>{open ? "Close" : "+ New project"}</button>
      </div>

      {open && (
        <form className="card" onSubmit={create} style={{ marginBottom: 18 }}>
          <div className="grid cols-2">
            <div>
              <label>Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} required />
              <label>Code</label>
              <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="PILOT" />
            </div>
            <div>
              <label>GitHub repo (owner/repo) — for AI pull requests</label>
              <input value={repo} onChange={(e) => setRepo(e.target.value)} placeholder="sumayatech24/my-app" />
              <label>Tech stack — guides code generation</label>
              <input value={stack} onChange={(e) => setStack(e.target.value)} placeholder="FastAPI + React + Postgres" />
            </div>
          </div>
          {error && <div className="error">{error}</div>}
          <button className="btn" style={{ marginTop: 14 }}>Create project</button>
        </form>
      )}

      <div className="module-grid">
        {projects.map((p) => (
          <Link to={`/workspace/${p.id}`} key={p.id} className="module-card">
            <div className="module-id">{p.code}</div>
            <div className="module-name">{p.name}</div>
            <div className="muted" style={{ fontSize: 12, margin: "6px 0" }}>{p.tech_stack || "No stack set"}</div>
            <div style={{ marginTop: "auto", display: "flex", gap: 6, flexWrap: "wrap" }}>
              {p.repo_url ? <span className="badge confidence">repo linked</span> : <span className="badge">no repo</span>}
            </div>
          </Link>
        ))}
        {projects.length === 0 && <p className="muted">No projects yet. Create one to begin.</p>}
      </div>
    </>
  );
}
