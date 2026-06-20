import { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../auth";

const links = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/intake", label: "Requirement intake", end: false },
  { to: "/board", label: "Backlog board", end: false },
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
        {links.map((l) => (
          <NavLink key={l.to} to={l.to} end={l.end}
            className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}>
            {l.label}
          </NavLink>
        ))}
        <div className="spacer" />
        <div className="who">
          {user?.full_name}
          <br />
          {user?.email}
          <br />
          <button className="btn secondary" style={{ marginTop: 10, padding: "6px 12px" }}
            onClick={logout}>Sign out</button>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
