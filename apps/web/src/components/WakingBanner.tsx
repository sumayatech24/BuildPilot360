import { useEffect, useState } from "react";

// Shows while the free-tier API is waking from sleep (cold start can take ~50s).
// Driven by 'bp360:waking' / 'bp360:ready' events from the API client.
export function WakingBanner() {
  const [waking, setWaking] = useState(false);
  useEffect(() => {
    const on = () => setWaking(true);
    const off = () => setWaking(false);
    window.addEventListener("bp360:waking", on);
    window.addEventListener("bp360:ready", off);
    return () => {
      window.removeEventListener("bp360:waking", on);
      window.removeEventListener("bp360:ready", off);
    };
  }, []);
  if (!waking) return null;
  return (
    <div style={{
      position: "fixed", top: 0, left: 0, right: 0, zIndex: 1000,
      background: "linear-gradient(135deg,#4f46e5,#0ea5e9)", color: "#fff",
      padding: "8px 16px", fontSize: 13, textAlign: "center",
    }}>
      ⏳ Waking the free server — first request after idle can take ~50 seconds. Retrying automatically…
    </div>
  );
}
