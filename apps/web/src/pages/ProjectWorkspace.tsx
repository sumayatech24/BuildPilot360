import { FormEvent, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, Project, Requirement, Run, Story } from "../api";

export default function ProjectWorkspace() {
  const { projectId = "" } = useParams();
  const [project, setProject] = useState<Project | null>(null);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [stories, setStories] = useState<Story[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [openFile, setOpenFile] = useState<{ run: Run } | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  // intake form
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const loadStories = () => api.stories(projectId).then((s) => setStories(s.sort((a, b) => (a.rank || 999) - (b.rank || 999))));
  const loadRuns = () => api.runs(projectId).then(setRuns);

  useEffect(() => {
    api.projects().then((ps) => setProject(ps.find((p) => p.id === projectId) || null));
    api.requirements(projectId).then(setRequirements);
    loadStories();
    loadRuns();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  // Poll runs while any are in-flight
  useEffect(() => {
    if (!runs.some((r) => r.status === "queued" || r.status === "running")) return;
    const t = setInterval(loadRuns, 2500);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runs]);

  const addRequirement = async (e: FormEvent) => {
    e.preventDefault();
    setBusy("Capturing requirement…"); setError("");
    try {
      const file = fileRef.current?.files?.[0];
      const req = file
        ? await api.uploadRequirement(projectId, title || file.name, file)
        : await api.createRequirement({ project_id: projectId, title, raw_text: text });
      setRequirements((r) => [...r, req]);
      setBusy("Generating user stories with AI…");
      await api.generateStories(req.id);
      await loadStories();
      setTitle(""); setText(""); if (fileRef.current) fileRef.current.value = "";
      setBusy("");
    } catch (err) { setError((err as Error).message); setBusy(""); }
  };

  const prioritize = async () => {
    setBusy("AI is prioritizing by MVP value…"); setError("");
    try { await api.prioritize(projectId); await loadStories(); setBusy(""); }
    catch (err) { setError((err as Error).message); setBusy(""); }
  };

  const generate = async () => {
    if (selected.size === 0) return;
    setBusy("Generating code & tests…"); setError("");
    try {
      await api.generateCode(projectId, [...selected]);
      setSelected(new Set());
      await loadRuns();
      setBusy("");
    } catch (err) { setError((err as Error).message); setBusy(""); }
  };

  const toggle = (id: string) =>
    setSelected((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });

  return (
    <>
      <div className="topbar">
        <div>
          <p className="muted" style={{ margin: 0 }}><Link to="/projects">Projects</Link> / {project?.code}</p>
          <h1>{project?.name || "Workspace"}</h1>
          <p>{project?.tech_stack}{project?.repo_url ? ` · ${project.repo_url}` : " · no repo linked"}</p>
        </div>
      </div>

      {error && <div className="error" style={{ marginBottom: 12 }}>{error}</div>}
      {busy && <div className="card" style={{ marginBottom: 16, borderColor: "var(--sky)" }}><b>⏳ {busy}</b></div>}

      <div className="pipeline">
        {/* Step 1: intake */}
        <form className="card" onSubmit={addRequirement}>
          <h3>1 · Requirement intake</h3>
          <label>Title</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Tenant onboarding self-service" />
          <label>High-level requirement</label>
          <textarea value={text} onChange={(e) => setText(e.target.value)}
            placeholder="As an admin I want to onboard a new tenant so customers can self-serve…" />
          <label>…or upload a requirements/stories file (.md/.txt/.csv)</label>
          <input type="file" ref={fileRef} accept=".md,.txt,.csv" />
          <button className="btn" style={{ marginTop: 14 }} disabled={!!busy}>Capture &amp; generate stories</button>
          <p className="muted" style={{ marginTop: 8 }}>{requirements.length} requirement(s) captured.</p>
        </form>

        {/* Step 2: stories + prioritize */}
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3>2 · Stories &amp; prioritization ({stories.length})</h3>
            <button className="btn secondary" onClick={prioritize} disabled={!!busy || stories.length === 0}>AI prioritize</button>
          </div>
          {stories.length === 0 && <p className="muted">Capture a requirement to generate stories.</p>}
          <div style={{ maxHeight: 420, overflowY: "auto" }}>
            {stories.map((s) => (
              <label key={s.id} className="story-row">
                <input type="checkbox" checked={selected.has(s.id)} onChange={() => toggle(s.id)} />
                <span style={{ flex: 1 }}>
                  <span className="title">{s.rank ? `#${s.rank} ` : ""}{s.title}</span>
                  {s.priority_rationale && <span className="muted" style={{ display: "block", fontSize: 12 }}>{s.priority_rationale}</span>}
                </span>
                {s.mvp && <span className="badge confidence">MVP</span>}
                <span className={"badge" + (s.priority === "P0" ? " p0" : "")}>{s.priority}</span>
              </label>
            ))}
          </div>
          {stories.length > 0 && (
            <button className="btn" style={{ marginTop: 12 }} onClick={generate} disabled={!!busy || selected.size === 0}>
              3 · Generate code &amp; tests ({selected.size} selected)
            </button>
          )}
        </div>
      </div>

      {/* Runs */}
      <div className="card" style={{ marginTop: 18 }}>
        <h3>Generation runs</h3>
        {runs.length === 0 && <p className="muted">No runs yet. Select stories and generate.</p>}
        {runs.map((r) => (
          <div key={r.id} className="list-row">
            <span>
              {r.files[0]?.path || r.story_id}
              <br /><span className="muted">{r.model} · {r.input_tokens}/{r.output_tokens} tokens · {r.log}</span>
            </span>
            <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <span className={"badge" + (r.status === "succeeded" ? " confidence" : r.status === "failed" ? " p0" : "")}>{r.status}</span>
              {r.pr_url && <a className="badge" href={r.pr_url} target="_blank" rel="noreferrer">View PR ↗</a>}
              {r.files.length > 0 && <button className="btn secondary" style={{ padding: "4px 10px" }} onClick={() => setOpenFile({ run: r })}>{r.files.length} files</button>}
            </span>
          </div>
        ))}
      </div>

      {openFile && (
        <div className="drawer-overlay" onClick={() => setOpenFile(null)}>
          <div className="drawer" style={{ width: 640 }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <h3 style={{ color: "var(--ink)" }}>Generated files</h3>
              <button className="btn secondary" style={{ padding: "4px 10px" }} onClick={() => setOpenFile(null)}>✕</button>
            </div>
            {openFile.run.rationale && <p className="muted">{openFile.run.rationale}</p>}
            {openFile.run.files.map((f) => (
              <div key={f.path} style={{ marginTop: 12 }}>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{f.path} <span className="badge">{f.kind}</span></div>
                <pre className="code">{f.content}</pre>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
