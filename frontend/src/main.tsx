import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./styles.css";
import { AuthProvider, useAuth } from "./auth";
import { Login } from "./pages/Login";
import { Groups } from "./pages/Groups";
import { GroupDetail } from "./pages/GroupDetail";
import { PlanDetail } from "./pages/PlanDetail";
import { Join } from "./pages/Join";
import { TopBar } from "./components";

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="center muted">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function App() {
  return (
    <BrowserRouter>
      <TopBar />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/join" element={<Protected><Join /></Protected>} />
        <Route path="/" element={<Protected><Groups /></Protected>} />
        <Route path="/groups/:groupId" element={<Protected><GroupDetail /></Protected>} />
        <Route path="/plans/:planId" element={<Protected><PlanDetail /></Protected>} />
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
