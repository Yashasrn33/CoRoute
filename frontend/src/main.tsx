import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./styles.css";
import { AuthProvider, useAuth } from "./auth";
import { Login } from "./pages/Login";
import { Home } from "./pages/Home";
import { GroupDetail } from "./pages/GroupDetail";
import { PlanDetail } from "./pages/PlanDetail";
import { Join } from "./pages/Join";
import { Profile } from "./pages/Profile";
import { Connections } from "./pages/Connections";
import { AppShell } from "./components";

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="center muted">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/join" element={<Protected><Join /></Protected>} />
        <Route element={<Protected><AppShell /></Protected>}>
          <Route path="/" element={<Home />} />
          <Route path="/groups/:groupId" element={<GroupDetail />} />
          <Route path="/plans/:planId" element={<PlanDetail />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/connections" element={<Connections />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>
);
