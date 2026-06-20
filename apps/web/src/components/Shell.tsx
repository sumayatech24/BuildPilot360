import { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../auth";

const groups: { heading: string; links: { to: string; label: string; end?: boolean }[] }[] = [
  {
    heading: "Delivery",
    links: [
      { to: "/", label: "Dashboard", end: true },
      { to: "/intake", label: "Requirement intake" },
      { to: "/board", label: "Backlog board" },
    ],
  },
  {
    heading: "Blueprint",
    links: [
      { to: "/modules", label: "Modules" },
      { to: "/features", label: "Features" },
      { to: "/stories", label: "User stories" },
      { to: "/nfrs", label: "NFRs & guardrails" },
      { to: "/integrations", label: "Integrations" },
      { to: "/screens", label: "Screens" },
      { to: "/roadmap", label: "Roadmap" },
    ],
  },
];

export function Shell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <img src="/logo-mark.svg" alt="BuildPilot360" />
          <b>BuildPilot<span>360</span></b>
        </div>
        {groups.map((g) => (
          <div key={g.heading} className="nav-group">
            <div className="nav-heading">{g.heading}</div>
            {g.links.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.end}
                className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}>
                {l.label}
              </NavLink>
            ))}
          </div>
        ))}
        <div className="spacer" />
        <div className="who">
          {user?.full_name}<br />{user?.email}
          <button className="btn secondary" style={{ marginTop: 10, padding: "6px 12px" }}
            onClick={logout}>Sign out</button>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
