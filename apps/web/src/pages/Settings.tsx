import { FormEvent, useEffect, useState } from "react";
import { api, Provider, Usage, USE_LOCAL } from "../api";

const PROVIDERS = [
  { id: "anthropic", label: "Anthropic (Claude)", needsModel: true },
  { id: "openai", label: "OpenAI", needsModel: true },
  { id: "github", label: "GitHub (token)", needsModel: false },
  { id: "aws", label: "AWS", needsModel: false },
  { id: "azure", label: "Azure", needsModel: false },
  { id: "gcp", label: "GCP", needsModel: false },
];
const MODELS = ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5"];

export default function Settings() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [provider, setProvider] = useState("anthropic");
  const [label, setLabel] = useState("");
  const [secret, setSecret] = useState("");
  const [model, setModel] = useState(MODELS[0]);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => {
    api.providers().then(setProviders).catch(() => {});
    api.usage().then(setUsage).catch(() => {});
  };
  useEffect(load, []);

  const add = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setMsg("");
    try {
      const needsModel = PROVIDERS.find((p) => p.id === provider)?.needsModel;
      await api.addProvider({ provider, label: label || provider, secret, config: needsModel ? { model } : {} });
      setSecret(""); setLabel("");
      load();
      setMsg("Saved.");
    } catch (err) { setMsg((err as Error).message); }
    finally { setBusy(false); }
  };

  const test = async (id: string) => {
    setMsg("Testing…");
    try { const r = await api.testProvider(id); setMsg(r.detail); }
    catch (err) { setMsg((err as Error).message); }
  };

  const used = usage ? usage.input_tokens + usage.output_tokens : 0;
  const pct = usage ? Math.min(100, (used / usage.monthly_budget) * 100) : 0;
  const needsModel = PROVIDERS.find((p) => p.id === provider)?.needsModel;

  return (
    <>
      <div className="topbar">
        <div>
          <h1>Settings &amp; integrations</h1>
          <p>Connect your own LLM and cloud keys. Secrets are encrypted and never shown again.</p>
        </div>
      </div>

      {USE_LOCAL && (
        <div className="demo-note" style={{ marginBottom: 16 }}>
          Demo mode — keys are stored only in your browser and not validated. On the hosted backend
          they are encrypted at rest and used for real generation.
        </div>
      )}

      <div className="grid cols-2">
        <form className="card" onSubmit={add}>
          <h3>Add a provider key</h3>
          <label>Provider</label>
          <select value={provider} onChange={(e) => setProvider(e.target.value)}>
            {PROVIDERS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
          </select>
          <label>Label</label>
          <input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="My Claude key" />
          {needsModel && (
            <>
              <label>Model (controls cost — Haiku is cheapest)</label>
              <select value={model} onChange={(e) => setModel(e.target.value)}>
                {MODELS.map((m) => <option key={m}>{m}</option>)}
              </select>
            </>
          )}
          <label>API key / token</label>
          <input type="password" value={secret} onChange={(e) => setSecret(e.target.value)}
            placeholder="sk-ant-… / ghp_…" required />
          <button className="btn" style={{ marginTop: 14 }} disabled={busy}>
            {busy ? "Saving…" : "Save key"}
          </button>
          {msg && <p className="muted" style={{ marginTop: 10 }}>{msg}</p>}
        </form>

        <div>
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Monthly LLM usage</h3>
            {usage && (
              <>
                <div className="stat">{used.toLocaleString()}<span className="unit">/ {usage.monthly_budget.toLocaleString()} tokens</span></div>
                <div style={{ background: "#e2e8f0", borderRadius: 8, height: 10, marginTop: 10, overflow: "hidden" }}>
                  <div style={{ width: `${pct}%`, height: "100%", background: pct > 80 ? "var(--danger)" : "var(--brand-grad)" }} />
                </div>
                <p className="muted" style={{ marginTop: 8 }}>{usage.calls} calls this period ({usage.period}). Calls are blocked past the budget to protect your quota.</p>
              </>
            )}
          </div>
          <div className="card">
            <h3>Connected providers</h3>
            {providers.length === 0 && <p className="muted">None yet.</p>}
            {providers.map((p) => (
              <div key={p.id} className="list-row">
                <span>
                  <b>{p.provider}</b> — {p.label}
                  <br /><span className="muted">{p.masked_secret} {p.config?.model ? `· ${p.config.model}` : ""}</span>
                </span>
                <span style={{ display: "flex", gap: 6 }}>
                  <button className="btn secondary" style={{ padding: "4px 10px" }} onClick={() => test(p.id)}>Test</button>
                  <button className="btn secondary" style={{ padding: "4px 10px" }}
                    onClick={() => api.deleteProvider(p.id).then(load)}>Remove</button>
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
