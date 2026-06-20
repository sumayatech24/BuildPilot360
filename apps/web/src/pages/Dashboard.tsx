import { useEffect, useState } from "react";
import { api, Project, Requirement, Story, LifecycleStage, CatalogSummary } from "../api";

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [reqs, setReqs] = useState<Requirement[]>([]);
  const [stories, setStories] = useState<Story[]>([]);
  const [stages, setStages] = useState<LifecycleStage[]>([]);
  const [summary, setSummary] = useState<CatalogSummary | null>(null);

  useEffect(() => {
    api.projects().then(setProjects).catch(() => {});
    api.requirements().then(setReqs).catch(() => {});
    api.stories().then(setStories).catch(() => {});
    api.lifecycle().then(setStages).catch(() => {});
    api.catalogSummary().then(setSummary).catch(() => {});
  }, []);

  const done = stories.filter((s) => s.status_code === "DONE").length;
  const t = summary?.totals;

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Delivery dashboard</h1>
          <p>End-to-end traceability from requirement to deployment.</p>
        </div>
      </div>

      <div className="grid cols-4" style={{ marginBottom: 18 }}>
        <Stat label="Modules" value={t?.modules ?? 0} />
        <Stat label="Planned features" value={t?.features ?? 0} />
        <Stat label="User stories" value={t?.user_stories ?? 0} />
        <Stat label="NFRs & guardrails" value={t?.nfrs ?? 0} />
      </div>

      <div className="grid cols-4">
        <Stat label="Projects" value={projects.length} />
        <Stat label="Requirements" value={reqs.length} />
        <Stat label="Stories generated" value={stories.length} />
        <Stat label="Stories closed" value={done} />
      </div>

      <div className="grid cols-2" style={{ marginTop: 18 }}>
        <div className="card">
          <h3>Recent requirements</h3>
          {reqs.length === 0 && <p className="muted">No requirements yet. Add one from Requirement intake.</p>}
          {reqs.slice(0, 6).map((r) => (
            <div key={r.id} className="list-row">
              <span>{r.title}</span>
              <span className={"badge" + (r.priority === "P0" ? " p0" : "")}>{r.status}</span>
            </div>
          ))}
        </div>
        <div className="card">
          <h3>Story lifecycle ({stages.length} stages)</h3>
          {stages.slice(0, 8).map((s) => (
            <div key={s.status_code} className="list-row">
              <span>{s.stage_no}. {s.stage_name}</span>
              <span className="muted">{s.primary_owner}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="card">
      <h3>{label}</h3>
      <div className="stat">{value}</div>
    </div>
  );
}
