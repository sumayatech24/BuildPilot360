import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import { Shell } from "./components/Shell";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Intake from "./pages/Intake";
import Board from "./pages/Board";

function Protected({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth();
  if (loading) return <div style={{ padding: 40 }}>Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Shell>{children}</Shell>;
}

function Inner() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Protected><Dashboard /></Protected>} />
      <Route path="/intake" element={<Protected><Intake /></Protected>} />
      <Route path="/board" element={<Protected><Board /></Protected>} />
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
