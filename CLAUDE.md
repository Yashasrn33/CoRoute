# CLAUDE.md — CoRoute engineering guide

This is the operational doc for working in this repo. Read it before writing code. The
**privacy invariants** below are non-negotiable — every change is checked against them.

For the product story and demo, see [README.md](README.md).

---

## Product principles (these drive design tradeoffs)

1. **Privacy-first.** A user's preferences are theirs alone. The whole product collapses if
   one person can see another's constraints. Privacy is enforced in the database, not just
   the app.
2. **Execution closes the loop.** A decision that isn't booked is a half-feature. The
   pipeline always ends at an `execution` (calendar invite minimum).
3. **Memory compounds.** Every plan reads the group's recent outcomes and avoids repeating
   them. The product gets more valuable the longer a group uses it.

---

## Stack & layout

- **Backend:** Python 3.12+, **FastAPI** (async), **SQLAlchemy 2.x** (async engine),
  **Alembic** migrations, **Pydantic v2** schemas.
- **Database:** **Postgres** with **Row-Level Security** on. Local dev via Docker.
- **Frontend:** **Vite + React** SPA (TypeScript) calling the FastAPI JSON API.
  > Default chosen for clean client/server separation against a standalone FastAPI backend.
  > Swappable to Next.js later; nothing in the data model or API depends on the choice.
- **AI:** **Claude API** via the official `anthropic` Python SDK.
- **Integrations (planned, Day 3):** Google Calendar (execute), Google Maps Platform
  (venue data). Not wired yet — keep code behind an interface so they can be stubbed.

```
backend/
  app/
    routers/          FastAPI route handlers (thin)
    services/         business logic (the LLM synthesis lives here)
    repositories/     DB access; every query runs under the RLS session var
    models/           SQLAlchemy ORM models
    schemas/          Pydantic request/response models
    core/             config, db engine(s), auth, logging
  alembic/            migrations (authoritative schema)
  tests/
frontend/
docs/
.claude/skills/
```

> `docs/schema.sql` is **reference DDL**. The authoritative schema is the Alembic
> migrations. The `migration-rls` skill keeps the two in sync.

---

## Data model

Authoritative description: [docs/data-model.md](docs/data-model.md). Tables:

`users` · `groups` · `group_members` · `preferences` · `plans` · `plan_attendees` ·
`options` · `votes` · `outcomes` · `executions`

Key columns to know:
- `preferences.visibility` — defaults to `private`; the entire trust story.
- `plans.parent_plan_id` — self-referential, enables trip sub-plans (model only, not built).
- `options.ai_reasoning` (jsonb) — why the AI picked each option; surfaced in the UI.
- `outcomes` — what the group actually did = **group memory**, fed into the next prompt.

---

## Privacy invariants (NON-NEGOTIABLE)

Any code change that touches preferences, the DB layer, or the LLM path is reviewed
against these. The `privacy-leak-check` skill audits them.

1. **Private by default.** `preferences.visibility` defaults to `private`. Private prefs
   are readable only by their owner — never by other group members, never in any API
   response.
2. **RLS, not just app checks.** The app's request connection runs as an **RLS-subject
   role**. Every request opens a transaction and sets
   `SET LOCAL app.current_user_id = '<jwt sub>'`. Policies enforce owner-only reads on
   `preferences` and member-only reads on group-scoped tables. **Never** connect the
   request path as a superuser / `BYPASSRLS` role.
3. **The privileged reader is isolated.** The LLM synthesis path uses a **separate**
   connection/role that can read all attendees' prefs *server-side only*, solely to build
   the anonymized constraint summary. It is never reachable from a client-facing read
   endpoint and never returns raw rows.
4. **No attribution.** The constraint summary aggregates ("group needs: vegetarian-
   friendly, ≤$35/person, quiet") and never maps a constraint to a person — not in the
   prompt, not in `ai_reasoning`, not in any response.
5. **Defense in depth.** App-layer authorization mirrors RLS so a bug in one layer doesn't
   leak. Don't rely on the frontend to hide anything.

Full narrative: [docs/privacy.md](docs/privacy.md).

---

## LLM endpoint contract

`POST /plans/{id}/options` — generates the AI options for a plan.

**Inputs (assembled server-side, under the privileged reader):**
- Attendee preferences for everyone marked `yes`/`maybe` on the plan.
- The group's **last 5 outcomes** (for anti-repeat / memory).
- Plan constraints (type, scheduled_for, location, any organizer notes).

**Pipeline:**
1. Build an **anonymized constraint summary** (no names, aggregated).
2. Compute an **input hash**; check the options cache. Same inputs ⇒ same outputs (cache
   hit). Caching keeps LLM cost flat and demos deterministic.
3. Call Claude with the prompt in
   [docs/prompts/generate-options.md](docs/prompts/generate-options.md), using **structured
   output** (tool use) so the response validates against the options schema.
4. Persist 3–5 `options`, each with `ai_reasoning` jsonb. Return them.

Synthesis runs **only** under the privileged reader, in `services/`, never in a router.

---

## LLM provider & Claude usage

- `LLM_PROVIDER` selects the synthesis backend: `auto` (Anthropic key → OpenAI key → stub),
  `anthropic`, `openai` (ChatGPT, JSON mode), `ollama` (local, e.g. `phi3:mini`), or `stub`
  (deterministic, offline). The chosen provider is part of the options cache key.
- Default Claude model: **`claude-opus-4-8`** (best reasoning for constraint satisfaction).
  **`claude-sonnet-4-6`** for cheaper iterations, **`claude-haiku-4-5-20251001`** for light
  calls. (`claude-fable-5` also available.)
- Claude path uses **structured output via tool use** — do not parse free text. The Ollama
  path uses JSON mode (`format: "json"`) and degrades to the stub on unparseable output.
- Use **prompt caching** for the stable parts of the system prompt.
- **Do not memorize pricing/params.** When implementing anything LLM-shaped, consult the
  `claude-api` skill for current model IDs, pricing, token limits, streaming, and tool-use
  details. Treat it as the source of truth over anything written here.

---

## Conventions

- **Async everywhere** — async FastAPI handlers, async SQLAlchemy, async Anthropic calls.
- **Layering:** routers (thin, validation) → services (logic) → repositories (DB). The LLM
  call is a service, never a router.
- **Schemas:** Pydantic v2 for all request/response bodies. Never return ORM models
  directly; map through response schemas (also prevents accidental field leaks).
- **Lint/type:** `ruff` (lint + format) and `mypy` (strict on `app/`).
- **Tests:** `pytest`. The privacy invariants must have tests (a non-owner reading another
  user's prefs must fail at the DB layer).
- **Observability:** structured logs around the LLM call — latency, token counts,
  cache hit/miss. Sentry on the calendar/execute paths.
- **Errors:** never leak raw DB rows or another user's data in error messages.

---

## Commands

> Placeholders until the app scaffold lands; a `Makefile` will back these.

| Command          | Purpose                                            |
|------------------|----------------------------------------------------|
| `make dev`       | Run backend (uvicorn) + frontend (vite) for local  |
| `make migrate`   | Apply Alembic migrations                            |
| `make seed`      | Seed the World Cup demo group (see seed skill)      |
| `make test`      | Run pytest + privacy invariant tests               |
| `make lint`      | ruff + mypy                                         |

---

## Project skills (`.claude/skills/`)

Invoke these during the build:

- **option-prompt-tuning** — iterate the option-generation prompt and eval it against the
  demo fixture; confirm outputs respect every hidden constraint and avoid recent outcomes.
- **migration-rls** — author an Alembic migration *and* its matching RLS policies, keep
  `docs/schema.sql` in sync, and run the preferences-stay-owner-only checklist.
- **seed-demo-data** — generate the demo group with ~6 months of history so group memory
  lands in the demo.
- **privacy-leak-check** — audit endpoints/responses to confirm raw per-user preferences
  are never returned to anyone but their owner.
