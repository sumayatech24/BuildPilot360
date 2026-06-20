import { useEffect, useState } from "react";
import { api, CatalogItem } from "../api";

export default function Roadmap() {
  const [items, setItems] = useState<CatalogItem[]>([]);
  useEffect(() => { api.catalog("roadmap", { limit: 50 }).then((p) => setItems(p.items)); }, []);

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Delivery roadmap</h1>
          <p>Phased plan from foundation to enterprise governance, cloud and data platforms.</p>
        </div>
      </div>
      <div className="timeline">
        {items.map((it, i) => (
          <div className="timeline-item" key={it.id}>
            <div className="timeline-dot">{i + 1}</div>
            <div className="card" style={{ flex: 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3 style={{ color: "var(--ink)", margin: 0 }}>
                  {it.data["Phase"]} — {it.data["Milestone"]}
                </h3>
                <span className="badge">{it.data["Suggested Duration"]}</span>
              </div>
              <p style={{ margin: "8px 0 4px" }}>{it.data["Scope"]}</p>
              <p className="muted"><b>Exit:</b> {it.data["Exit Criteria"]}</p>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
