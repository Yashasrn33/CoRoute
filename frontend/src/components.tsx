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

function GroupNav({ group }: { group: Group }) {
  const [open, setOpen] = useState(false);
  const [plans, setPlans] = useState<Plan[] | null>(null);
  const loc = useLocation();
  const nav = useNavigate();
  const active = loc.pathname === `/groups/${group.id}`;

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next && plans === null) {
      setPlans(await api.get<Plan[]>(`/groups/${group.id}/plans`).catch(() => []));
    }
  }

  const live = (plans ?? []).filter((p) => p.status !== "executed");
  const history = (plans ?? []).filter((p) => p.status === "executed");

  return (
    <div>
      <div className="row" style={{ gap: 2 }}>
        <button className="navlink ghost" style={{ width: 22, padding: 4 }} onClick={toggle}>
          {open ? "▾" : "▸"}
        </button>
        <button className={`navlink ${active ? "active" : ""}`} onClick={() => nav(`/groups/${group.id}`)}>
          {group.name}
        </button>
      </div>
      {open && (
        <div>
          {live.map((p) => (
            <button key={p.id} className={`navlink sub ${loc.pathname === `/plans/${p.id}` ? "active" : ""}`}
              onClick={() => nav(`/plans/${p.id}`)}>• {p.title}</button>
          ))}
          {history.length > 0 && <div className="navlink sub" style={{ opacity: 0.6 }}>History</div>}
          {history.map((p) => (
            <button key={p.id} className={`navlink sub ${loc.pathname === `/plans/${p.id}` ? "active" : ""}`}
              onClick={() => nav(`/plans/${p.id}`)} style={{ opacity: 0.7 }}>◦ {p.title}</button>
          ))}
          {plans !== null && live.length === 0 && history.length === 0 && (
            <div className="empty">No plans yet</div>
          )}
        </div>
      )}
    </div>
  );
}

export function Sidebar() {
  const [groups, setGroups] = useState<Group[]>([]);
  const loc = useLocation();
  useEffect(() => { api.get<Group[]>("/groups").then(setGroups).catch(() => {}); }, [loc.pathname]);
  return (
    <aside className="sidebar">
      <NavLink to="/" end className={({ isActive }) => `navlink ${isActive ? "active" : ""}`}>
        + New group
      </NavLink>
      <h4>Groups</h4>
      {groups.length === 0 && <div className="empty">No groups yet</div>}
      {groups.map((g) => <GroupNav key={g.id} group={g} />)}
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
