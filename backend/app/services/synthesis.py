"""AI option synthesis — the core differentiator.

Privacy-critical flow (see docs/privacy.md):
  1. Read attendees' preferences via the ISOLATED synthesis reader (BYPASSRLS),
     server-side only.
  2. Aggregate into an ANONYMIZED constraint summary — no names, no per-person
     mapping.
  3. Hash the inputs; reuse cached options on a hit (flat cost, deterministic demo).
  4. Call Claude with structured output (or a deterministic stub if no API key).
  5. Persist options via the caller's RLS session.

Nothing here returns raw per-user preference rows to any caller.
"""

import hashlib
import json
import time
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import SynthesisSessionLocal
from app.core.logging import get_logger
from app.models import Option, Outcome, Plan, PlanAttendee
from app.models.enums import PlanStatus, RsvpStatus

settings = get_settings()
log = get_logger("coroute.synthesis")

# Simple in-process cache: input hash -> list[option dict]. Same inputs => same
# options. Swap for Redis in production.
_OPTIONS_CACHE: dict[str, list[dict]] = {}


_PREF_COLS = "diet, budget_max, vibe_dislikes, transportation, hard_nos, accessibility_needs, notes"
_ARRAY_FIELDS = ("diet", "vibe_dislikes", "transportation", "hard_nos", "accessibility_needs")


def _row_to_pref(row) -> dict:
    diet_, budget_max, vibe_, transport_, hard_, access_, notes_ = row
    return {
        "diet": list(diet_ or []),
        "budget_max": budget_max,
        "vibe_dislikes": list(vibe_ or []),
        "transportation": list(transport_ or []),
        "hard_nos": list(hard_ or []),
        "accessibility_needs": list(access_ or []),
        "notes": notes_,
    }


def _override(general: dict | None, plan: dict | None) -> dict:
    """Effective per-user pref: each field on the plan pref REPLACES the general
    one when set (non-empty list / non-null number / non-empty notes); otherwise
    the general value is used."""
    g = general or {}
    p = plan or {}
    eff: dict = {}
    for f in _ARRAY_FIELDS:
        eff[f] = p[f] if p.get(f) else g.get(f, [])
    eff["budget_max"] = p["budget_max"] if (p.get("budget_max") is not None) else g.get("budget_max")
    eff["notes"] = (p.get("notes") or "").strip() or (g.get("notes") or "").strip() or None
    return eff


async def _build_anonymized_summary(
    group_id: UUID, plan_id: UUID, attendee_ids: list[UUID]
) -> dict:
    """Aggregate attendees' EFFECTIVE preferences (general overridden per-field by
    any per-plan prefs) into a names-free constraint summary.

    Uses the privileged synthesis reader. Returns counts/unions/bounds only —
    plus an anonymized list of free-text requests. No names, ever.
    """
    if SynthesisSessionLocal is None:
        raise RuntimeError(
            "DATABASE_URL_SYNTHESIS not configured — synthesis reader required."
        )
    empty = {"party_size": 0, "respondents": 0, "diet": [], "budget_per_person_max": None,
             "vibe_dislikes": [], "transportation": [], "hard_nos": [], "accessibility": [],
             "additional_requests": []}
    if not attendee_ids:
        return empty

    ids = [str(i) for i in attendee_ids]
    async with SynthesisSessionLocal() as s:
        general_rows = (await s.execute(
            text(f"SELECT user_id, {_PREF_COLS} FROM preferences "
                 "WHERE group_id = :g AND user_id = ANY(:ids)"),
            {"g": str(group_id), "ids": ids},
        )).all()
        plan_rows = (await s.execute(
            text(f"SELECT user_id, {_PREF_COLS} FROM plan_preferences "
                 "WHERE plan_id = :p AND user_id = ANY(:ids)"),
            {"p": str(plan_id), "ids": ids},
        )).all()

    general = {r[0]: _row_to_pref(r[1:]) for r in general_rows}
    plan = {r[0]: _row_to_pref(r[1:]) for r in plan_rows}

    diet: set[str] = set(); vibe: set[str] = set(); transport: set[str] = set()
    hard_nos: set[str] = set(); access: set[str] = set()
    budgets: list[int] = []
    requests: list[str] = []
    respondents = 0
    for uid in attendee_ids:
        if uid not in general and uid not in plan:
            continue
        respondents += 1
        eff = _override(general.get(uid), plan.get(uid))
        diet.update(eff["diet"]); vibe.update(eff["vibe_dislikes"])
        transport.update(eff["transportation"]); hard_nos.update(eff["hard_nos"])
        access.update(eff["accessibility_needs"])
        if eff["budget_max"] is not None:
            budgets.append(eff["budget_max"])
        if eff["notes"]:
            requests.append(eff["notes"])

    return {
        "party_size": len(attendee_ids),
        "respondents": respondents,
        "diet": sorted(diet),
        "budget_per_person_max": min(budgets) if budgets else None,
        "vibe_dislikes": sorted(vibe),
        "transportation": sorted(transport),
        "hard_nos": sorted(hard_nos),
        "accessibility": sorted(access),
        # Free-text per-plan requests, aggregated WITHOUT names.
        "additional_requests": requests,
    }


def _input_hash(summary: dict, outcomes: list[dict], plan_kind: dict) -> str:
    blob = json.dumps(
        {"summary": summary, "outcomes": outcomes, "plan": plan_kind},
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode()).hexdigest()


def _stub_options(summary: dict, outcomes: list[dict], plan_kind: dict) -> list[dict]:
    """Deterministic fallback when no Anthropic key is set. Keeps the demo working
    and visibly respects constraints + avoids recent outcomes."""
    cap = summary.get("budget_per_person_max")
    cap_txt = f"under ${cap}/person" if cap else "budget-friendly"
    avoid = ", ".join(o["summary"] for o in outcomes[:3]) or "nothing recent"
    diet_txt = ", ".join(summary.get("diet") or ["no restrictions"])
    venues = [
        ("Mesa Verde — back patio", "Quiet patio, full veg menu, transit-accessible."),
        ("The Greenhouse Kitchen", "Plant-forward, step-free entry, calm room."),
        ("Riverside Commons", "Spacious, varied menu, easy to reach without a car."),
    ]
    out = []
    for i, (title, desc) in enumerate(venues, start=1):
        out.append({
            "title": title,
            "location": "Downtown",
            "description": desc,
            "rank": i,
            "ai_reasoning": {
                "satisfies": {
                    "diet": f"Accommodates: {diet_txt}.",
                    "budget": f"Mains {cap_txt}.",
                    "vibe": "Avoids loud-bar atmosphere.",
                    "transportation": "Reachable without a car.",
                    "accessibility": "Step-free entrance.",
                },
                "avoids_repeat": f"Different from recent outings ({avoid}).",
                "tradeoffs": None,
                "_generated_by": "stub",
            },
        })
    return out


def _json_instructions(summary: dict, outcomes: list[dict], plan_kind: dict) -> tuple[str, str]:
    """Shared system+user prompt for JSON-mode providers (Ollama and the like)."""
    system = (
        "You are CoRoute's planning engine. Generate 3-5 concrete real-world options for a "
        "group outing that satisfy ALL of the group's constraints at once. Honor hard_nos and "
        "accessibility as strict filters. AVOID anything similar to recent_outcomes. NEVER "
        "attribute a constraint to a person. "
        'Reply with ONLY valid JSON of the form: {"options":[{"title":str,"location":str,'
        '"description":str,"rank":int,"ai_reasoning":{"satisfies":{"diet":str,"budget":str,'
        '"vibe":str,"transportation":str,"accessibility":str},"avoids_repeat":str,'
        '"tradeoffs":str|null}}]}'
    )
    user = json.dumps({"constraints": summary, "recent_outcomes": outcomes, "plan": plan_kind})
    return system, user


async def _ollama_options(summary: dict, outcomes: list[dict], plan_kind: dict) -> list[dict]:
    """Call a local Ollama model (e.g. phi3:mini) in JSON mode and parse options.

    Falls back to the stub if the small model returns unusable output, so the demo
    never breaks.
    """
    import httpx

    system, user = _json_instructions(summary, outcomes, plan_kind)
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": settings.ollama_model,
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0.4},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
        data = json.loads(content)
        options = data.get("options") if isinstance(data, dict) else data
        if not isinstance(options, list) or not options:
            raise ValueError("no options array in model output")
        # Ensure ranks exist.
        for i, o in enumerate(options, start=1):
            o.setdefault("rank", i)
        return options
    except Exception as exc:  # noqa: BLE001 — degrade gracefully for a tiny local model
        log.warning("ollama synthesis failed (%s); falling back to stub", exc)
        return _stub_options(summary, outcomes, plan_kind)


async def _openai_options(summary: dict, outcomes: list[dict], plan_kind: dict) -> list[dict]:
    """Call the OpenAI (ChatGPT) API in JSON mode and parse options."""
    import httpx

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    system, user = _json_instructions(summary, outcomes, plan_kind)
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.openai_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model,
                "temperature": 0.5,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    data = json.loads(content)
    options = data.get("options") if isinstance(data, dict) else data
    if not isinstance(options, list) or not options:
        raise RuntimeError("OpenAI did not return an options array")
    for i, o in enumerate(options, start=1):
        o.setdefault("rank", i)
    return options


async def _claude_options(summary: dict, outcomes: list[dict], plan_kind: dict) -> list[dict]:
    """Call Claude with structured output (tool use). Imported lazily so the app
    runs without the SDK/key configured."""
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    tool = {
        "name": "propose_options",
        "description": "Return 3-5 concrete options satisfying all group constraints.",
        "input_schema": {
            "type": "object",
            "properties": {
                "options": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "location": {"type": "string"},
                            "description": {"type": "string"},
                            "rank": {"type": "integer"},
                            "ai_reasoning": {"type": "object"},
                        },
                        "required": ["title", "description", "rank", "ai_reasoning"],
                    },
                }
            },
            "required": ["options"],
        },
    }
    system = (
        "You are CoRoute's planning engine. Generate concrete options that satisfy ALL "
        "of the group's constraints at once. Honor hard_nos and accessibility as strict "
        "filters. AVOID anything similar to recent outcomes. Never attribute a constraint "
        "to a person. Return 3-5 options, best first, each explaining how it fits each "
        "constraint group."
    )
    user = json.dumps({"constraints": summary, "recent_outcomes": outcomes, "plan": plan_kind})
    msg = await client.messages.create(
        model=settings.claude_model,
        max_tokens=2000,
        system=system,
        tools=[tool],
        tool_choice={"type": "tool", "name": "propose_options"},
        messages=[{"role": "user", "content": user}],
    )
    for block in msg.content:
        if block.type == "tool_use":
            return block.input["options"]
    raise RuntimeError("Claude did not return structured options")


async def _chat_json(system: str, user: str, max_tokens: int = 800) -> dict:
    """Provider-dispatched single JSON response. Raises if no chat provider."""
    provider = settings.resolve_llm_provider()
    if provider == "openai":
        import httpx

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.openai_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={"model": settings.openai_model, "temperature": 0.4,
                      "response_format": {"type": "json_object"},
                      "messages": [{"role": "system", "content": system},
                                   {"role": "user", "content": user}]},
            )
            resp.raise_for_status()
            return json.loads(resp.json()["choices"][0]["message"]["content"])
    if provider == "ollama":
        import httpx

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json={"model": settings.ollama_model, "format": "json", "stream": False,
                      "messages": [{"role": "system", "content": system},
                                   {"role": "user", "content": user}]},
            )
            resp.raise_for_status()
            return json.loads(resp.json()["message"]["content"])
    if provider == "anthropic":
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        msg = await client.messages.create(
            model=settings.claude_model, max_tokens=max_tokens,
            system=system + " Reply with ONLY valid JSON.",
            messages=[{"role": "user", "content": user}],
        )
        txt = "".join(b.text for b in msg.content if b.type == "text").strip()
        if txt.startswith("```"):
            txt = txt.split("```")[1].lstrip("json").strip()
        return json.loads(txt)
    raise RuntimeError("no chat provider configured for suggestions")


def _stub_suggestion(plan: Plan, general: dict | None) -> dict:
    by_type = {
        "watch_party": ("Wants a big screen with good sound to watch the match.",
                        ["venues that won't show the game"]),
        "dinner": ("In the mood for a relaxed sit-down dinner.", []),
        "activity": ("Up for something active and hands-on.", []),
        "trip": ("Prefers a calm, well-organized itinerary.", []),
    }
    notes, vibe = by_type.get(plan.type.value, ("No strong extra preferences for this one.", []))
    return {**(general or {}), "vibe_dislikes": vibe, "notes": notes,
            "rationale": f"Suggested from the {plan.type.value.replace('_', ' ')} plan (stub)."}


async def suggest_plan_preferences(plan: Plan, general: dict | None) -> dict:
    """Suggest per-plan preference overrides from the plan context + the user's own
    general prefs. Returns a PlanPreferenceIn-shaped dict (+ rationale), not saved.
    Falls back to a deterministic suggestion if no/failed model."""
    provider = settings.resolve_llm_provider()
    if provider == "stub":
        return _stub_suggestion(plan, general)
    system = (
        "You help one person set preferences for a single group outing. Given the plan "
        "and the person's general preferences, suggest sensible per-plan overrides for "
        "THIS plan only. Keep their hard constraints. Reply with JSON of the form: "
        '{"diet":[str],"budget_min":int|null,"budget_max":int|null,"vibe_dislikes":[str],'
        '"transportation":[str],"hard_nos":[str],"accessibility_needs":[str],'
        '"notes":str,"rationale":str}'
    )
    user = json.dumps({
        "plan": {"type": plan.type.value, "title": plan.title,
                 "location": plan.location,
                 "scheduled_for": plan.scheduled_for.isoformat() if plan.scheduled_for else None},
        "general_preferences": general or {},
    })
    try:
        data = await _chat_json(system, user)
    except Exception as exc:  # noqa: BLE001 — degrade gracefully
        log.warning("plan-pref suggestion failed (%s); using stub", exc)
        return _stub_suggestion(plan, general)
    # Coerce to the expected shape.
    out: dict = {}
    for f in _ARRAY_FIELDS:
        v = data.get(f)
        out[f] = v if isinstance(v, list) else []
    for f in ("budget_min", "budget_max"):
        v = data.get(f)
        out[f] = v if isinstance(v, int) else None
    out["notes"] = data.get("notes") if isinstance(data.get("notes"), str) else None
    out["rationale"] = data.get("rationale") if isinstance(data.get("rationale"), str) else None
    return out


async def generate_and_store_options(session: AsyncSession, plan: Plan) -> list[Option]:
    """Orchestrate synthesis and persist options on the caller's RLS session."""
    # Attendees who are coming (yes/maybe) — read on the RLS session (member-scoped).
    att_ids = list(
        (
            await session.execute(
                select(PlanAttendee.user_id).where(
                    PlanAttendee.plan_id == plan.id,
                    PlanAttendee.rsvp.in_([RsvpStatus.yes, RsvpStatus.maybe]),
                )
            )
        ).scalars().all()
    )
    summary = await _build_anonymized_summary(plan.group_id, plan.id, att_ids)

    recent = (
        await session.execute(
            select(Outcome).where(Outcome.group_id == plan.group_id)
            .order_by(Outcome.happened_at.desc()).limit(5)
        )
    ).scalars().all()
    outcomes = [{"summary": o.summary, "happened_at": o.happened_at.isoformat()} for o in recent]

    plan_kind = {"type": plan.type.value, "title": plan.title,
                 "scheduled_for": plan.scheduled_for.isoformat() if plan.scheduled_for else None,
                 "location_hint": plan.location}

    provider = settings.resolve_llm_provider()
    # Cache key includes the provider so switching providers regenerates.
    h = _input_hash(summary, outcomes, {**plan_kind, "_provider": provider})
    started = time.monotonic()
    cache_hit = h in _OPTIONS_CACHE
    if cache_hit:
        options_data = _OPTIONS_CACHE[h]
    else:
        if provider == "anthropic":
            options_data = await _claude_options(summary, outcomes, plan_kind)
        elif provider == "openai":
            options_data = await _openai_options(summary, outcomes, plan_kind)
        elif provider == "ollama":
            options_data = await _ollama_options(summary, outcomes, plan_kind)
        else:
            options_data = _stub_options(summary, outcomes, plan_kind)
        _OPTIONS_CACHE[h] = options_data
    log.info(
        "synthesis plan=%s cache_hit=%s provider=%s options=%d latency_ms=%d",
        plan.id, cache_hit, provider,
        len(options_data), int((time.monotonic() - started) * 1000),
    )

    # Replace any existing options for the plan.
    existing = (await session.execute(select(Option).where(Option.plan_id == plan.id))).scalars().all()
    for o in existing:
        await session.delete(o)
    await session.flush()

    created: list[Option] = []
    for od in options_data:
        opt = Option(
            plan_id=plan.id,
            title=od["title"],
            location=od.get("location"),
            description=od.get("description"),
            ai_reasoning=od.get("ai_reasoning", {}),
            rank=od.get("rank"),
        )
        session.add(opt)
        created.append(opt)
    plan.status = PlanStatus.options_ready
    await session.flush()
    created.sort(key=lambda o: (o.rank or 99))
    return created
