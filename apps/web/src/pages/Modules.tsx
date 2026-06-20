import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ModuleInfo } from "../api";

export default function Modules() {
  const [mods, setMods] = useState<ModuleInfo[]>([]);
  useEffect(() => { api.modules().then(setMods); }, []);

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Module catalog</h1>
          <p>All 27 platform modules. Each has a live, tenant-scoped workspace with full CRUD.</p>
        </div>
        <span className="badge">{mods.length} modules</span>
      </div>
      <div className="module-grid">
        {mods.map((m) => (
          <Link to={`/modules/${m.module_id}`} key={m.module_id} className="module-card">
            <div className="module-id">{m.module_id}</div>
            <div className="module-name">{m.name}</div>
            <div className="muted" style={{ fontSize: 12, margin: "6px 0" }}>{m.data["Purpose"]}</div>
            <div style={{ display: "flex", gap: 6, marginTop: "auto" }}>
              <span className="badge">{m.domain}</span>
              <span className={"badge" + (m.mvp_priority === "MVP" ? " confidence" : "")}>{m.mvp_priority}</span>
            </div>
          </Link>
        ))}
      </div>
    </>
  );
}
