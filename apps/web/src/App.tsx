import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import { Shell } from "./components/Shell";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Intake from "./pages/Intake";
import Board from "./pages/Board";
import Modules from "./pages/Modules";
import ModuleWorkspace from "./pages/ModuleWorkspace";
import Projects from "./pages/Projects";
import ProjectWorkspace from "./pages/ProjectWorkspace";
import Settings from "./pages/Settings";
import Features from "./pages/Features";
import Stories from "./pages/Stories";
import Nfrs from "./pages/Nfrs";
import Integrations from "./pages/Integrations";
import Screens from "./pages/Screens";
import Roadmap from "./pages/Roadmap";

function Protected({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth();
  if (loading) return <div style={{ padding: 40 }}>Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Shell>{children}</Shell>;
}

const routes: [string, JSX.Element][] = [
  ["/", <Dashboard />],
  ["/projects", <Projects />],
  ["/workspace/:projectId", <ProjectWorkspace />],
  ["/settings", <Settings />],
  ["/intake", <Intake />],
  ["/board", <Board />],
  ["/modules", <Modules />],
  ["/modules/:moduleId", <ModuleWorkspace />],
  ["/features", <Features />],
  ["/stories", <Stories />],
  ["/nfrs", <Nfrs />],
  ["/integrations", <Integrations />],
  ["/screens", <Screens />],
  ["/roadmap", <Roadmap />],
];

function Inner() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      {routes.map(([path, el]) => (
        <Route key={path} path={path} element={<Protected>{el}</Protected>} />
      ))}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Inner />
    </AuthProvider>
  );
}
