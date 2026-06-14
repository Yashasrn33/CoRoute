import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { api, Group, Plan } from "./api";
import { useAuth } from "./auth";

export function TopBar() {
  const { user } = useAuth();
  return (
    <div className="topbar">
      <Link to="/" className="brand">Co<span>Route</span></Link>
      {user && (
        <div className="topnav">
          <NavLink to="/connections">Connections</NavLink>
          <NavLink to="/profile" title="Profile">
            <span className="avatar">{user.display_name.slice(0, 1).toUpperCase()}</span>
          </NavLink>
        </div>
      )}
    </div>
  );
}

type PlanWithGroup = Plan & { groupName: string };

export function Sidebar() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [plans, setPlans] = useState<PlanWithGroup[]>([]);
  const loc = useLocation();
  const nav = useNavigate();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const gs = await api.get<Group[]>("/groups").catch(() => []);
      if (cancelled) return;
      setGroups(gs);
      const lists = await Promise.all(
        gs.map((g) =>
          api.get<Plan[]>(`/groups/${g.id}/plans`)
            .then((ps) => ps.map((p) => ({ ...p, groupName: g.name })))
            .catch(() => [] as PlanWithGroup[])
        )
      );
      if (cancelled) return;
      const all = lists.flat().sort((a, b) => b.created_at.localeCompare(a.created_at));
      setPlans(all);
    })();
    return () => { cancelled = true; };
  }, [loc.pathname]);

  // Groups still being planned: have an active (non-executed) plan, or are new (no plans).
  const activeGroups = groups.filter((g) => {
    const gp = plans.filter((p) => p.group_id === g.id);
    return gp.length === 0 || gp.some((p) => p.status !== "executed");
  });
  // History: completed plans only.
  const history = plans.filter((p) => p.status === "executed");

  return (
    <aside className="sidebar">
      <NavLink to="/" end className={({ isActive }) => `navlink ${isActive ? "active" : ""}`}>
        + New group
      </NavLink>

      <h4>Groups</h4>
      {activeGroups.length === 0 && <div className="empty">Nothing being planned</div>}
      {activeGroups.map((g) => (
        <button key={g.id} className={`navlink ${loc.pathname === `/groups/${g.id}` ? "active" : ""}`}
          onClick={() => nav(`/groups/${g.id}`)}>{g.name}</button>
      ))}

      <h4>History</h4>
      {history.length === 0 && <div className="empty">No completed plans</div>}
      {history.map((p) => (
        <button key={p.id} className={`navlink ${loc.pathname === `/plans/${p.id}` ? "active" : ""}`}
          onClick={() => nav(`/plans/${p.id}`)} title={`${p.groupName} · ${p.status.replace("_", " ")}`}>
          <span>{p.title}</span>
          <span className="muted small" style={{ display: "block" }}>{p.groupName}</span>
        </button>
      ))}
    </aside>
  );
}

export function AppShell() {
  return (
    <>
      <TopBar />
      <div className="shell">
        <Sidebar />
        <main className="main"><Outlet /></main>
      </div>
    </>
  );
}

export function Tags({ items }: { items: string[] }) {
  if (!items?.length) return <span className="muted small">—</span>;
  return <>{items.map((t) => <span key={t} className="tag">{t}</span>)}</>;
}
