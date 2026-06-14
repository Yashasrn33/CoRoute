import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, Group } from "../api";

export function Home() {
  const [name, setName] = useState("");
  const [err, setErr] = useState("");
  const nav = useNavigate();

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
        <p className="muted small">
          A standing group of friends. Invite people, then start plans. Your groups and their
          history are in the left panel.
        </p>
        <div className="row">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="World Cup Crew" />
          <button>Create group</button>
        </div>
      </form>
      {err && <div className="error">{err}</div>}
    </div>
  );
}
