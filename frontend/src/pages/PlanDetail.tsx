import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, PlanDetail as PD, Option } from "../api";

const RSVPS = ["yes", "maybe", "no"];

export function PlanDetail() {
  const { planId } = useParams();
  const [plan, setPlan] = useState<PD | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() { setPlan(await api.get<PD>(`/plans/${planId}`)); }
  useEffect(() => { load().catch((e) => setErr(e.message)); }, [planId]);

  const act = async (fn: () => Promise<unknown>) => {
    setErr(""); setBusy(true);
    try { await fn(); await load(); } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  if (!plan) return <div className="container muted">Loading…</div>;

  const executed = plan.status === "executed";
  const winner = executed
    ? [...plan.options].sort((a, b) => b.vote_total - a.vote_total)[0]
    : null;

  return (
    <div className="container">
      <Link to={`/groups/${plan.group_id}`} className="small">← Back to group</Link>
      <div className="spread">
        <h1 style={{ marginBottom: 6 }}>{plan.title}</h1>
        <span className="pill status">{plan.status.replace("_", " ")}</span>
      </div>
      <p className="muted small">{plan.type.replace("_", " ")}{plan.location ? ` · ${plan.location}` : ""}</p>

      <div className="card">
        <h2>Who's coming</h2>
        <div className="row">
          {plan.attendees.map((a) => (
            <span key={a.user_id} className={`pill ${a.rsvp === "yes" ? "yes" : a.rsvp === "no" ? "no" : ""}`}>
              {a.display_name}: {a.rsvp}
            </span>
          ))}
        </div>
        <hr />
        <div className="row">
          <span className="muted small">Your RSVP:</span>
          {RSVPS.map((r) => (
            <button key={r} className="secondary" disabled={busy}
              onClick={() => act(() => api.put(`/plans/${planId}/rsvp`, { rsvp: r }))}>{r}</button>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="spread">
          <h2 style={{ margin: 0 }}>AI options</h2>
          <button disabled={busy}
            onClick={() => act(() => api.post(`/plans/${planId}/options`))}>
            {plan.options.length ? "Regenerate" : "Generate options"}
          </button>
        </div>
        <p className="muted small">
          Built from everyone's private constraints (anonymized) and the group's recent history.
        </p>
        {plan.options.length === 0 && <p className="muted">No options yet — generate them.</p>}
        <div className="grid">
          {plan.options.map((o) => (
            <OptionCard key={o.id} o={o} winner={winner?.id === o.id} executed={executed} busy={busy}
              onVote={() => act(() => api.put(`/plans/${planId}/votes`, { option_id: o.id, score: o.my_score ? 0 : 1 }))}
              onExecute={() => act(() => api.post(`/plans/${planId}/execute`, { option_id: o.id }))}
            />
          ))}
        </div>
      </div>

      {executed && winner && (
        <div className="card" style={{ borderColor: "var(--accent-2)" }}>
          <h2 style={{ color: "var(--accent-2)" }}>Locked in: {winner.title}</h2>
          <p className="muted small">Calendar invite created (stub) and saved to group memory — future plans will avoid repeating it.</p>
        </div>
      )}

      {err && <div className="error">{err}</div>}
    </div>
  );
}

function OptionCard({ o, winner, executed, busy, onVote, onExecute }: {
  o: Option; winner: boolean; executed: boolean; busy: boolean;
  onVote: () => void; onExecute: () => void;
}) {
  const r = o.ai_reasoning?.satisfies ?? {};
  return (
    <div className={`card option ${winner ? "winner" : ""}`} style={{ marginBottom: 0 }}>
      <div className="spread">
        <h3 style={{ margin: 0 }}>
          {o.rank ? `#${o.rank} ` : ""}{o.title}
          {winner && <span className="pill yes" style={{ marginLeft: 8 }}>winner</span>}
        </h3>
        <span className="pill">{o.vote_total} {o.vote_total === 1 ? "vote" : "votes"}</span>
      </div>
      {o.location && <p className="muted small" style={{ margin: "4px 0" }}>{o.location}</p>}
      {o.description && <p style={{ margin: "6px 0" }}>{o.description}</p>}
      <div className="reason stack">
        {Object.entries(r).map(([k, v]) => (
          <div key={k}><b>{k}:</b> {String(v)}</div>
        ))}
        {o.ai_reasoning?.avoids_repeat && <div><b>avoids repeat:</b> {o.ai_reasoning.avoids_repeat}</div>}
      </div>
      {!executed && (
        <div className="row" style={{ marginTop: 10 }}>
          <button className={o.my_score ? "" : "secondary"} disabled={busy} onClick={onVote}>
            {o.my_score ? "✓ Voted" : "👍 Vote"}
          </button>
          <button className="secondary" disabled={busy} onClick={onExecute}>Pick & add to calendar</button>
        </div>
      )}
    </div>
  );
}
