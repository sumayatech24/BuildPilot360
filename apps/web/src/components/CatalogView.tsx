import { useEffect, useState } from "react";
import { api, CatalogItem } from "../api";

export interface Column {
  label: string;
  /** Read from a typed catalog column, or from the raw data map. */
  col?: keyof CatalogItem;
  dataKey?: string;
  width?: string;
  badge?: boolean;
}

interface Props {
  category: string;
  title: string;
  subtitle: string;
  columns: Column[];
  filters?: ("module_id" | "phase" | "priority" | "domain" | "q")[];
  pageSize?: number;
}

const value = (item: CatalogItem, c: Column): string => {
  if (c.col) return (item[c.col] as string) || "";
  if (c.dataKey) return item.data?.[c.dataKey] || "";
  return "";
};

export function CatalogView({ category, title, subtitle, columns, filters = ["q"], pageSize = 25 }: Props) {
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [params, setParams] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState<CatalogItem | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v));
    api.catalog(category, { ...clean, limit: pageSize, offset })
      .then((p) => { setItems(p.items); setTotal(p.total); })
      .finally(() => setLoading(false));
  }, [category, params, offset, pageSize]);

  const setFilter = (k: string, v: string) => { setOffset(0); setParams((p) => ({ ...p, [k]: v })); };

  return (
    <>
      <div className="topbar">
        <div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        <span className="badge">{total} items</span>
      </div>

      <div className="card" style={{ padding: 14, marginBottom: 16, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
        {filters.includes("q") && (
          <input placeholder="Search title…" style={{ maxWidth: 280 }}
            onChange={(e) => setFilter("q", e.target.value)} />
        )}
        {filters.includes("module_id") && (
          <input placeholder="Module (e.g. M01)" style={{ maxWidth: 160 }}
            onChange={(e) => setFilter("module_id", e.target.value.toUpperCase())} />
        )}
        {filters.includes("priority") && (
          <select onChange={(e) => setFilter("priority", e.target.value)} style={{ maxWidth: 140 }}>
            <option value="">All priorities</option>
            {["P0", "P1", "P2", "P3", "MVP"].map((p) => <option key={p}>{p}</option>)}
          </select>
        )}
        {filters.includes("phase") && (
          <select onChange={(e) => setFilter("phase", e.target.value)} style={{ maxWidth: 160 }}>
            <option value="">All phases</option>
            {["MVP", "Phase 2", "Phase 2+", "Phase 4"].map((p) => <option key={p}>{p}</option>)}
          </select>
        )}
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table className="data-table">
          <thead>
            <tr>{columns.map((c) => <th key={c.label} style={{ width: c.width }}>{c.label}</th>)}</tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} onClick={() => setSelected(item)} className="clickable">
                {columns.map((c) => (
                  <td key={c.label}>
                    {c.badge
                      ? <span className={"badge" + (value(item, c) === "P0" ? " p0" : "")}>{value(item, c)}</span>
                      : <span title={value(item, c)}>{value(item, c)}</span>}
                  </td>
                ))}
              </tr>
            ))}
            {!loading && items.length === 0 && (
              <tr><td colSpan={columns.length} className="muted" style={{ padding: 20 }}>No items.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 14 }}>
        <span className="muted">Showing {items.length ? offset + 1 : 0}–{offset + items.length} of {total}</span>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn secondary" disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - pageSize))}>← Prev</button>
          <button className="btn secondary" disabled={offset + pageSize >= total}
            onClick={() => setOffset(offset + pageSize)}>Next →</button>
        </div>
      </div>

      {selected && (
        <div className="drawer-overlay" onClick={() => setSelected(null)}>
          <div className="drawer" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
              <h3 style={{ color: "var(--ink)" }}>{selected.title || selected.item_id}</h3>
              <button className="btn secondary" style={{ padding: "4px 10px" }} onClick={() => setSelected(null)}>✕</button>
            </div>
            {selected.item_id && <p className="muted">{selected.item_id}</p>}
            <dl className="kv">
              {Object.entries(selected.data).map(([k, v]) => v && (
                <div key={k}><dt>{k}</dt><dd>{v}</dd></div>
              ))}
            </dl>
          </div>
        </div>
      )}
    </>
  );
}
