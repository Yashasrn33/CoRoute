import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { auth as authApi, getToken, setToken, User } from "./api";

interface AuthCtx {
  user: User | null;
  loading: boolean;
  signIn: (token: string) => Promise<void>;
  signOut: () => void;
  refresh: () => Promise<void>;
}

const Ctx = createContext<AuthCtx>(null!);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) { setLoading(false); return; }
    authApi.me().then(setUser).catch(() => setToken(null)).finally(() => setLoading(false));
  }, []);

  async function signIn(token: string) {
    setToken(token);
    const me = await authApi.me();
    setUser(me);
  }
  function signOut() {
    setToken(null);
    setUser(null);
  }
  async function refresh() {
    setUser(await authApi.me());
  }

  return (
    <Ctx.Provider value={{ user, loading, signIn, signOut, refresh }}>{children}</Ctx.Provider>
  );
}
