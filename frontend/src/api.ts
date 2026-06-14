// Thin typed API client. Token lives in localStorage; every call attaches it.
const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
const TOKEN_KEY = "coroute_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string | null) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(p: string) => req<T>("GET", p),
  post: <T>(p: string, b?: unknown) => req<T>("POST", p, b),
  put: <T>(p: string, b?: unknown) => req<T>("PUT", p, b),
};

// ---- Types (mirror backend schemas) ----
export interface User { id: string; email: string; display_name: string; }
export interface Group { id: string; name: string; created_by: string; created_at: string; }
export interface Member { user_id: string; display_name: string; role: string; }
export interface GroupDetail extends Group { members: Member[]; }
export interface Preference {
  visibility: string; diet: string[]; budget_min: number | null; budget_max: number | null;
  vibe_dislikes: string[]; transportation: string[]; hard_nos: string[];
  accessibility_needs: string[]; notes: string | null;
}
export interface PrefStatus {
  group_id: string; ready: number; total: number;
  members: { user_id: string; display_name: string; has_prefs: boolean }[];
}
export interface Plan {
  id: string; group_id: string; type: string; status: string; title: string;
  scheduled_for: string | null; location: string | null; created_at: string;
}
export interface Attendee { user_id: string; display_name: string; rsvp: string; }
export interface Option {
  id: string; plan_id: string; title: string; location: string | null;
  description: string | null; ai_reasoning: any; rank: number | null;
  vote_total: number; my_score: number;
}
export interface PlanDetail extends Plan { attendees: Attendee[]; options: Option[]; }

// ---- Auth ----
export const auth = {
  requestMagicLink: (email: string, display_name?: string) =>
    api.post<{ sent: boolean; dev_magic_token: string | null }>("/auth/magic-link", { email, display_name }),
  verify: (token: string) =>
    api.post<{ access_token: string; user_id: string }>("/auth/verify", { token }),
  me: () => api.get<User>("/auth/me"),
};
