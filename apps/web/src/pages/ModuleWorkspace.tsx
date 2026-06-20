import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, CatalogItem, ModuleInfo, ModuleRecord } from "../api";

export default function ModuleWorkspace() {
  const { moduleId = "" } = useParams();
  const [info, setInfo] = useState<ModuleInfo | null>(null);
  const [features, setFeatures] = useState<CatalogItem[]>([]);
  const [records, setRecords] = useState<ModuleRecord[]>([]);
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("P2");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const loadRecords = () => api.moduleRecords(moduleId).then((r) => setRecords(r.items));

  useEffect(() => {
    api.modules().then((m) => setInfo(m.find((x) => x.module_id === moduleId) || null));
    api.catalog("feature", { module_id: moduleId, limit: 200 }).then((p) => setFeatures(p.items));
    loadRecords();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [moduleId]);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      await api.createModuleRecord(moduleId, { title, priority });
      setTitle("");
      await loadRecords();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: string) => {
    await api.deleteModuleRecord(moduleId, id);
    loadRecords();
  };

  return (
    <>
      <div className="topbar">
        <div>
          <p className="muted" style={{ margin: 0 }}>
            <Link to="/modules">Modules</Link> / {moduleId}
          </p>
          <h1>{info?.name || moduleId}</h1>
          <p>{info?.data["Purpose"]}</p>
        </div>
        <span className="badge">{info?.mvp_priority}</span>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h3>Records ({records.length})</h3>
          <form onSubmit={create} style={{ display: "flex", gap: 8, margin: "8px 0 14px" }}>
            <input value={title} onChange={(e) => setTitle(e.target.value)}
              placeholder={`New ${moduleId} record title`} required />
            <select value={priority} onChange={(e) => setPriority(e.target.value)} style={{ maxWidth: 90 }}>
              {["P0", "P1", "P2", "P3"].map((p) => <option key={p}>{p}</option>)}
            </select>
            <button className="btn" disabled={busy}>Add</button>
          </form>
          {error && <div className="error">{error}</div>}
          {records.length === 0 && <p className="muted">No records yet. Create one above.</p>}
          {records.map((r) => (
            <div key={r.id} className="list-row">
              <span>{r.title}</span>
              <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span className={"badge" + (r.priority === "P0" ? " p0" : "")}>{r.priority}</span>
                <span className="badge">{r.status}</span>
                <button className="btn secondary" style={{ padding: "3px 9px" }}
                  onClick={() => remove(r.id)}>Delete</button>
              </span>
            </div>
          ))}
        </div>

        <div className="card">
          <h3>Planned features ({features.length})</h3>
          {features.length === 0 && <p className="muted">No features mapped to this module.</p>}
          <div style={{ maxHeight: 460, overflowY: "auto" }}>
            {features.map((f) => (
              <div key={f.id} className="list-row">
                <span style={{ fontSize: 13 }}>{f.title}</span>
                <span className={"badge" + (f.priority === "P0" ? " p0" : "")}>{f.priority}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
