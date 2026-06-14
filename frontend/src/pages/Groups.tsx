import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Group } from "../api";

export function Groups() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [name, setName] = useState("");
  const [err, setErr] = useState("");

  async function load() {
    setGroups(await api.get<Group[]>("/groups"));
  }
  useEffect(() => { load().catch((e) => setErr(e.message)); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await api.post<Group>("/groups", { name });
      setName("");
      await load();
    } catch (e: any) { setErr(e.message); }
  }

  return (
    <div className="container">
      <h1>Your groups</h1>
      <form className="card" onSubmit={create}>
        <h2>Create a group</h2>
        <div className="row">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="World Cup Crew" />
          <button>Create</button>
        </div>
      </form>
      {err && <div className="error">{err}</div>}
      {groups.length === 0 && <p className="muted">No groups yet. Create one above.</p>}
      <div className="grid">
        {groups.map((g) => (
          <Link key={g.id} to={`/groups/${g.id}`} className="card spread" style={{ color: "var(--text)" }}>
            <span><b>{g.name}</b></span>
            <span className="muted small">Open →</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
