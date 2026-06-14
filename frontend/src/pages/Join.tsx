import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";

export function Join() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const [msg, setMsg] = useState("Joining…");
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;
    const token = params.get("token");
    if (!token) { setMsg("Missing invite token."); return; }
    api.post<{ group_id: string; joined: boolean }>("/groups/join", { token })
      .then((r) => nav(`/groups/${r.group_id}`))
      .catch((e) => setMsg(e.message));
  }, []);

  return <div className="center muted">{msg}</div>;
}
