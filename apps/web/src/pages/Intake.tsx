import { FormEvent, useEffect, useState } from "react";
import { api, Analysis, Project } from "../api";

export default function Intake() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [title, setTitle] = useState("");
  const [rawText, setRawText] = useState("");
  const [requirementId, setRequirementId] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.projects().then((p) => {
      setProjects(p);
      if (p[0]) setProjectId(p[0].id);
    });
  }, []);

  const ensureProject = async (): Promise<string> => {
    if (projectId) return projectId;
    const p = await api.createProject({ name: "Default Project", code: "DEFAULT" });
    setProjects((prev) => [...prev, p]);
    setProjectId(p.id);
    return p.id;
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setError(""); setAnalysis(null); setRequirementId(null);
    try {
      const pid = await ensureProject();
      setStatus("Capturing requirement…");
      const req = await api.createRequirement({ project_id: pid, title, raw_text: rawText });
      setRequirementId(req.id);
      setStatus("Running AI analysis…");
      const result = await api.analyze(req.id);
      setAnalysis(result);
      setStatus("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const generate = async () => {
    if (!requirementId) return;
    setBusy(true); setError("");
    try {
      const { created_story_ids } = await api.generateBacklog(requirementId);
      setStatus(`Generated ${created_story_ids.length} stories. View them on the Backlog board.`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Requirement intake</h1>
          <p>Capture a requirement, run provider-neutral AI analysis, then generate a backlog.</p>
        </div>
      </div>

      <div className="grid cols-2">
        <form className="card" onSubmit={submit}>
          <h3>New requirement</h3>
          <label>Project</label>
          <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            <option value="">+ Create default project</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.code})</option>)}
          </select>
          <label>Title</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)}
            placeholder="Tenant onboarding self-service" required />
          <label>Requirement text</label>
          <textarea value={rawText} onChange={(e) => setRawText(e.target.value)}
            placeholder="As an admin I want to onboard a new tenant so that customers can self-serve…" required />
          <button className="btn" style={{ marginTop: 16 }} disabled={busy}>
            {busy ? "Working…" : "Capture & analyze"}
          </button>
          {status && <p className="muted" style={{ marginTop: 10 }}>{status}</p>}
          {error && <div className="error">{error}</div>}
        </form>

        <div className="card">
          <h3>AI analysis</h3>
          {!analysis && <p className="muted">Submit a requirement to see the AI breakdown.</p>}
          {analysis && (
            <div>
              <p>{analysis.summary}</p>
              <div style={{ display: "flex", gap: 8, margin: "8px 0 14px" }}>
                <span className="badge">{analysis.classification}</span>
                <span className="badge confidence">
                  {(analysis.confidence * 100).toFixed(0)}% confidence
                </span>
                <span className="badge">{analysis.provider}</span>
              </div>
              <Section title="Gaps" items={analysis.gaps} empty="No gaps detected." />
              <Section title="Clarifying questions" items={analysis.questions} />
              <Section title="Non-functional requirements" items={analysis.nfrs} />
              <Section title="Acceptance criteria" items={analysis.acceptance_criteria} />
              <button className="btn" style={{ marginTop: 14 }} onClick={generate} disabled={busy}>
                Generate backlog ({analysis.suggested_stories.length} stories)
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function Section({ title, items, empty }: { title: string; items: string[]; empty?: string }) {
  return (
    <div style={{ marginTop: 10 }}>
      <h3 style={{ color: "var(--ink)" }}>{title}</h3>
      {items.length === 0 && <p className="muted">{empty || "—"}</p>}
      <ul style={{ margin: "4px 0", paddingLeft: 18, fontSize: 14 }}>
        {items.map((i, idx) => <li key={idx} style={{ marginBottom: 4 }}>{i}</li>)}
      </ul>
    </div>
  );
}
