import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { auth } from "../api";
import { useAuth } from "../auth";

export function Login() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const { signIn } = useAuth();
  const nav = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      const res = await auth.requestMagicLink(email, name || undefined);
      // Dev: the magic token comes back so we can complete login immediately.
      if (res.dev_magic_token) {
        const v = await auth.verify(res.dev_magic_token);
        await signIn(v.access_token);
        nav("/");
      } else {
        setErr("Check your email for a sign-in link.");
      }
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="center">
      <form className="card" style={{ width: 360 }} onSubmit={submit}>
        <h1 style={{ marginTop: 0 }}>Sign in to Co<span style={{ color: "var(--accent)" }}>Route</span></h1>
        <p className="muted small">Group plans that respect what nobody wants to say out loud.</p>
        <label>Email</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required type="email" />
        <label>Display name (first time)</label>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Alex" />
        {err && <div className="error">{err}</div>}
        <div style={{ marginTop: 14 }}>
          <button disabled={busy}>{busy ? "Signing in…" : "Continue"}</button>
        </div>
        <p className="muted small" style={{ marginTop: 12 }}>
          Dev mode signs you in instantly (no email needed).
        </p>
      </form>
    </div>
  );
}
