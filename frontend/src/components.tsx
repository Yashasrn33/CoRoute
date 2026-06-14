import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "./auth";

export function TopBar() {
  const { user, signOut } = useAuth();
  const nav = useNavigate();
  return (
    <div className="topbar">
      <Link to="/" className="brand">Co<span>Route</span></Link>
      {user && (
        <div className="row">
          <span className="muted small">{user.display_name}</span>
          <button className="ghost" onClick={() => { signOut(); nav("/login"); }}>Sign out</button>
        </div>
      )}
    </div>
  );
}

export function Tags({ items }: { items: string[] }) {
  if (!items?.length) return <span className="muted small">—</span>;
  return <>{items.map((t) => <span key={t} className="tag">{t}</span>)}</>;
}
