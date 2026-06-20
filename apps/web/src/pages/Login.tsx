import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { USE_LOCAL } from "../api";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  // Demo credentials match the seeded owner so the deployed app logs in out of the box.
  const [email, setEmail] = useState("owner@buildpilot360.dev");
  const [password, setPassword] = useState(USE_LOCAL ? "demo" : "Bp360-Owner!2026");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={onSubmit}>
        <div className="brand">
          <img src={`${import.meta.env.BASE_URL}logo-mark.svg`} alt="BuildPilot360" />
          <h2>BuildPilot360</h2>
          <div className="sub">AI SDLC Delivery Platform</div>
        </div>
        {USE_LOCAL ? (
          <div className="demo-note">
            Demo mode — runs entirely in your browser (no server). Any credentials work;
            your data is saved locally. The full FastAPI backend is in the repo for production.
          </div>
        ) : (
          <div className="demo-note">
            Demo credentials are pre-filled — just click <b>Sign in</b>. (Rotate the owner
            password after first login.)
          </div>
        )}
        <label>Email</label>
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <label>Password</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        {error && <div className="error">{error}</div>}
        <button className="btn" style={{ width: "100%", marginTop: 18 }} disabled={busy}>
          {busy ? "Signing in…" : USE_LOCAL ? "Enter demo" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
