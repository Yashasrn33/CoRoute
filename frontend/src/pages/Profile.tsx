import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { DefaultPreference, profileApi } from "../api";
import { useAuth } from "../auth";
import { PreferenceForm } from "./PreferenceForm";

const EMPTY: DefaultPreference = {
  diet: [], budget_min: null, budget_max: null, vibe_dislikes: [],
  transportation: [], hard_nos: [], accessibility_needs: [], notes: null,
};

export function Profile() {
  const { user, signOut, refresh } = useAuth();
  const nav = useNavigate();
  const [name, setName] = useState(user?.display_name ?? "");
  const [savedName, setSavedName] = useState(false);
  const [defaults, setDefaults] = useState<DefaultPreference | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => { profileApi.getDefaults().then(setDefaults).catch((e) => setErr(e.message)); }, []);

  async function saveName(e: React.FormEvent) {
    e.preventDefault();
    setSavedName(false);
    try { await profileApi.updateName(name); await refresh(); setSavedName(true); }
    catch (e: any) { setErr(e.message); }
  }

  async function saveDefaults(p: DefaultPreference) {
    const { visibility, ...rest } = p as any;  // PreferenceForm includes visibility; defaults don't use it
    void visibility;
    await profileApi.putDefaults(rest);
    setDefaults(rest);
  }

  return (
    <div className="container">
      <div className="spread">
        <h1>Profile</h1>
        <button className="secondary" onClick={() => { signOut(); nav("/login"); }}>Sign out</button>
      </div>

      <div className="card">
        <h2>Account</h2>
        <form onSubmit={saveName}>
          <label>Display name</label>
          <div className="row">
            <input value={name} onChange={(e) => setName(e.target.value)} />
            <button>Save</button>
            {savedName && <span className="small" style={{ color: "var(--accent-2)" }}>Saved ✓</span>}
          </div>
          <p className="muted small" style={{ marginTop: 8 }}>{user?.email}</p>
        </form>
      </div>

      <div className="card">
        <h2>Default preferences</h2>
        <p className="muted small">
          Your starting point. When you create or join a group, these pre-fill that group's
          preferences — which you can still tweak per group (and per plan).
        </p>
        <PreferenceForm
          initial={defaults ? ({ ...defaults, visibility: "private" } as any) : ({ ...EMPTY, visibility: "private" } as any)}
          onSave={saveDefaults}
        />
      </div>
      {err && <div className="error">{err}</div>}
    </div>
  );
}
