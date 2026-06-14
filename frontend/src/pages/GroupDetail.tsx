import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, connectionsApi, ConnectionPerson, GroupDetail as GD, PrefStatus, Plan } from "../api";

export function GroupDetail() {
  const { groupId } = useParams();
  const [group, setGroup] = useState<GD | null>(null);
  const [status, setStatus] = useState<PrefStatus | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [invite, setInvite] = useState<string>("");
  const [friends, setFriends] = useState<ConnectionPerson[]>([]);
  const [err, setErr] = useState("");

  // new plan form
  const [title, setTitle] = useState("");
  const [type, setType] = useState("watch_party");
  const [location, setLocation] = useState("");

  async function load() {
    const [g, st, pl] = await Promise.all([
      api.get<GD>(`/groups/${groupId}`),
      api.get<PrefStatus>(`/groups/${groupId}/preferences/status`),
      api.get<Plan[]>(`/groups/${groupId}/plans`),
    ]);
    setGroup(g); setStatus(st); setPlans(pl);
  }
  useEffect(() => { load().catch((e) => setErr(e.message)); }, [groupId]);
  useEffect(() => { connectionsApi.list().then((c) => setFriends(c.friends)).catch(() => {}); }, [groupId]);

  async function addFriend(userId: string) {
    try { setGroup(await connectionsApi.addToGroup(groupId!, userId)); }
    catch (e: any) { setErr(e.message); }
  }

  async function makeInvite() {
    const res = await api.post<{ invite_url: string; token: string }>(`/groups/${groupId}/invite`);
    // For the demo we share the in-app join link with the token.
    setInvite(`${window.location.origin}/join?token=${res.token}`);
  }

  async function createPlan(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    try {
      await api.post<Plan>(`/groups/${groupId}/plans`, { type, title, location: location || null });
      setTitle(""); setLocation("");
      await load();
    } catch (e: any) { setErr(e.message); }
  }

  if (!group) return <div className="container muted">Loading…</div>;

  return (
    <div className="container">
      <Link to="/" className="small">← All groups</Link>
      <h1>{group.name}</h1>

      <div className="card">
        <div className="spread">
          <h2 style={{ margin: 0 }}>Members</h2>
          <button className="secondary" onClick={makeInvite}>Create invite link</button>
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          {group.members.map((m) => (
            <span key={m.user_id} className="pill">
              {m.display_name}{m.role === "owner" ? " ★" : ""}
            </span>
          ))}
        </div>
        {invite && (
          <>
            <label>Share this link (opens in-app join):</label>
            <div className="codeblock">{invite}</div>
          </>
        )}
        {(() => {
          const memberIds = new Set(group.members.map((m) => m.user_id));
          const addable = friends.filter((f) => !memberIds.has(f.user_id));
          if (addable.length === 0) return null;
          return (
            <>
              <hr />
              <label>Add a connection to this group</label>
              <div className="row">
                {addable.map((f) => (
                  <button key={f.user_id} className="secondary" onClick={() => addFriend(f.user_id)}>
                    + {f.display_name}
                  </button>
                ))}
              </div>
            </>
          );
        })()}
      </div>

      {status && (
        <div className="card">
          <div className="spread">
            <h2 style={{ margin: 0 }}>Preferences readiness</h2>
            <span className="pill status">{status.ready}/{status.total} ready</span>
          </div>
          <p className="muted small">
            Set your general preferences in <Link to="/profile">Profile</Link>; adjust per-plan
            on each plan. Readiness shows existence only — never anyone's preference content.
          </p>
          <div className="row">
            {status.members.map((m) => (
              <span key={m.user_id} className={`pill ${m.has_prefs ? "yes" : ""}`}>
                {m.display_name}: {m.has_prefs ? "set ✓" : "not set"}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <h2>Plans</h2>
        <form className="row" onSubmit={createPlan} style={{ marginBottom: 12 }}>
          <input style={{ flex: 2 }} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="World Cup Final" />
          <select style={{ flex: 1 }} value={type} onChange={(e) => setType(e.target.value)}>
            <option value="watch_party">Watch party</option>
            <option value="dinner">Dinner</option>
            <option value="activity">Activity</option>
            <option value="trip">Trip</option>
            <option value="other">Other</option>
          </select>
          <input style={{ flex: 1 }} value={location} onChange={(e) => setLocation(e.target.value)} placeholder="downtown" />
          <button>Start plan</button>
        </form>
        {plans.length === 0 && <p className="muted">No plans yet.</p>}
        <div className="grid">
          {plans.map((p) => (
            <Link key={p.id} to={`/plans/${p.id}`} className="card spread" style={{ color: "var(--text)", marginBottom: 0 }}>
              <span><b>{p.title}</b> <span className="muted small">· {p.type.replace("_", " ")}</span></span>
              <span className="pill status">{p.status.replace("_", " ")}</span>
            </Link>
          ))}
        </div>
      </div>

      {err && <div className="error">{err}</div>}
    </div>
  );
}
