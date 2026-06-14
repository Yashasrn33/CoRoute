import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, Group } from "../api";

export function Home() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [name, setName] = useState("");
  const [err, setErr] = useState("");
  const nav = useNavigate();

  useEffect(() => { api.get<Group[]>("/groups").then(setGroups).catch((e) => setErr(e.message)); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      const g = await api.post<Group>("/groups", { name });
      setName("");
      nav(`/groups/${g.id}`);
    } catch (e: any) { setErr(e.message); }
  }

  return (
    <div className="container">
      <h1>Plan something</h1>
      <form className="card" onSubmit={create}>
        <h2>Create a new group</h2>
        <p className="muted small">A standing group of friends. Invite people, set private prefs, then start plans.</p>
        <div className="row">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="World Cup Crew" />
          <button>Create group</button>
        </div>
      </form>
      {err && <div className="error">{err}</div>}
      {groups.length > 0 && (
        <>
          <h2 style={{ marginTop: 24 }}>Your groups</h2>
          <div className="grid">
            {groups.map((g) => (
              <div key={g.id} className="card spread" style={{ cursor: "pointer" }} onClick={() => nav(`/groups/${g.id}`)}>
                <b>{g.name}</b><span className="muted small">Open →</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
