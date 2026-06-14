import { useEffect, useState } from "react";
import { connectionsApi, Connections as Conns, ConnectionPerson } from "../api";

export function Connections() {
  const [data, setData] = useState<Conns | null>(null);
  const [email, setEmail] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() { setData(await connectionsApi.list()); }
  useEffect(() => { load().catch((e) => setErr(e.message)); }, []);

  const act = async (fn: () => Promise<Conns>) => {
    setErr(""); setBusy(true);
    try { setData(await fn()); } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  async function request(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    await act(() => connectionsApi.request(email).then((d) => { setEmail(""); return d; }));
  }

  if (!data) return <div className="container muted">Loading…</div>;

  const Person = ({ p, children }: { p: ConnectionPerson; children?: React.ReactNode }) => (
    <div className="card spread" style={{ marginBottom: 8 }}>
      <span>
        <span className="avatar" style={{ marginRight: 8 }}>{p.display_name.slice(0, 1).toUpperCase()}</span>
        <b>{p.display_name}</b> <span className="muted small">· {p.email}</span>
      </span>
      <span className="row">{children}</span>
    </div>
  );

  return (
    <div className="container">
      <h1>Connections</h1>

      <form className="card" onSubmit={request}>
        <h2>Add a connection</h2>
        <p className="muted small">Send a request by email. They'll appear once they accept.</p>
        <div className="row">
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="friend@example.com" />
          <button disabled={busy}>Send request</button>
        </div>
      </form>
      {err && <div className="error">{err}</div>}

      {data.incoming.length > 0 && (
        <>
          <h2>Requests for you <span className="badge">{data.incoming.length}</span></h2>
          {data.incoming.map((p) => (
            <Person key={p.connection_id} p={p}>
              <button disabled={busy} onClick={() => act(() => connectionsApi.accept(p.connection_id))}>Accept</button>
              <button className="secondary" disabled={busy} onClick={() => act(() => connectionsApi.remove(p.connection_id))}>Decline</button>
            </Person>
          ))}
        </>
      )}

      <h2 style={{ marginTop: 18 }}>Friends</h2>
      {data.friends.length === 0 && <p className="muted">No connections yet.</p>}
      {data.friends.map((p) => (
        <Person key={p.connection_id} p={p}>
          <button className="secondary" disabled={busy} onClick={() => act(() => connectionsApi.remove(p.connection_id))}>Remove</button>
        </Person>
      ))}

      {data.outgoing.length > 0 && (
        <>
          <h2 style={{ marginTop: 18 }}>Pending (sent)</h2>
          {data.outgoing.map((p) => (
            <Person key={p.connection_id} p={p}>
              <span className="pill">pending</span>
              <button className="ghost" disabled={busy} onClick={() => act(() => connectionsApi.remove(p.connection_id))}>Cancel</button>
            </Person>
          ))}
        </>
      )}
    </div>
  );
}
