import { useEffect, useState } from "react";
import { Preference } from "../api";

const EMPTY: Preference = {
  visibility: "private", diet: [], budget_min: null, budget_max: null,
  vibe_dislikes: [], transportation: [], hard_nos: [], accessibility_needs: [], notes: null,
};

const csv = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
const join = (a: string[]) => (a || []).join(", ");

export function PreferenceForm({ initial, onSave }: { initial: Preference | null; onSave: (p: Preference) => Promise<void> }) {
  const [p, setP] = useState<Preference>(initial ?? EMPTY);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => { setP(initial ?? EMPTY); }, [initial]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setSaved(false);
    try { await onSave(p); setSaved(true); }
    finally { setBusy(false); }
  }

  return (
    <form onSubmit={save}>
      <label>Diet (comma-separated)</label>
      <input value={join(p.diet)} onChange={(e) => setP({ ...p, diet: csv(e.target.value) })} placeholder="vegetarian, vegan" />
      <div className="row">
        <div style={{ flex: 1 }}>
          <label>Budget min ($)</label>
          <input type="number" value={p.budget_min ?? ""} onChange={(e) => setP({ ...p, budget_min: e.target.value ? +e.target.value : null })} />
        </div>
        <div style={{ flex: 1 }}>
          <label>Budget max ($ / person)</label>
          <input type="number" value={p.budget_max ?? ""} onChange={(e) => setP({ ...p, budget_max: e.target.value ? +e.target.value : null })} />
        </div>
      </div>
      <label>Vibe dislikes</label>
      <input value={join(p.vibe_dislikes)} onChange={(e) => setP({ ...p, vibe_dislikes: csv(e.target.value) })} placeholder="loud bars, long waits" />
      <label>Transportation</label>
      <input value={join(p.transportation)} onChange={(e) => setP({ ...p, transportation: csv(e.target.value) })} placeholder="no car" />
      <label>Hard no's</label>
      <input value={join(p.hard_nos)} onChange={(e) => setP({ ...p, hard_nos: csv(e.target.value) })} placeholder="no smoking sections" />
      <label>Accessibility needs</label>
      <input value={join(p.accessibility_needs)} onChange={(e) => setP({ ...p, accessibility_needs: csv(e.target.value) })} placeholder="step-free entry" />
      <label>Notes</label>
      <textarea value={p.notes ?? ""} onChange={(e) => setP({ ...p, notes: e.target.value || null })} rows={2} />
      <div className="row" style={{ marginTop: 12 }}>
        <button disabled={busy}>{busy ? "Saving…" : "Save preferences"}</button>
        {saved && <span className="small" style={{ color: "var(--accent-2)" }}>Saved ✓</span>}
      </div>
    </form>
  );
}
