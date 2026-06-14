# CoRoute

**Group plans that respect what nobody wants to say out loud — then actually happen.**

CoRoute turns "where should we go?" group chats into decisions and bookings. Each person
sets their constraints **privately, once** (diet, budget, vibe dislikes, transport, hard
no's). When someone starts a plan, an AI generates concrete options that satisfy
*everyone's hidden constraints* — without ever revealing or attributing them — the group
votes, and the winner gets **executed** (calendar invite at minimum). Every outcome is
remembered, so the AI stops sending you to the same three places.

---

## Why CoRoute exists

iMessage polls and existing voting apps make you vote on options *someone manually added*.
They stop at the decision and forget everything the moment it's made. CoRoute is built
around the four things none of them do:

1. **Private constraints → public answer.** "I'm vegetarian, my budget is $25, I can't do
   loud places" stays private to each person. The AI generates options that fit everyone's
   hidden constraints. This is exactly what LLMs are good at and what voting apps can't do.
2. **Execution, not just decision.** Apps stop at "the group picked Sushi Palace." Nobody
   books the table, drops the pin, makes the calendar invite. The decision is the easy 10%.
3. **Group memory.** "We always end up at the same three places" is the real problem. No
   app remembers your rotations, who hasn't picked lately, who's been flaking.
4. **Plans, not picks.** A real Saturday night is *where to eat + what to do after + who's
   driving*. Every app handles one decision at a time.
5. **Mixed-attendance reality.** "Who's even coming" usually isn't settled when planning
   starts. Most apps assume a fixed group.

---

## The core loop

```
Create group ──▶ invite by link
     │
     ▼
Each person sets PRIVATE preferences once (only they ever see their own)
     │
     ▼
Someone starts a Plan (dinner Sat / trip to Lisbon / watch party Sun)
     │
     ▼
Quick attendance check (yes / maybe / no)
     │
     ▼
AI generates 3–5 concrete options that satisfy every hidden constraint
        and avoid recent group history
     │
     ▼
Group votes (ranked or thumbs)
     │
     ▼
Winner ──▶ one-tap execute (calendar invite; booking/payments are stretch)
     │
     ▼
Outcome saved to GROUP MEMORY ──▶ feeds the next plan
```

Trips are the same shape with linked sub-plans (destination → dates → lodging →
activities). The data model handles it; we don't build trip mode for the first demo.

---

## The 2-minute demo: "4 friends, World Cup final Sunday"

1. Show each person's **private** prefs side by side — vegan, $30 cap, no loud bars, no
   car. Nobody else in the group can see these.
2. The AI returns **three venues**, each with reasoning that visibly respects every
   constraint.
3. The group **votes**. Winner drops a **calendar invite**.
4. The kicker: *"last month they did the same sports bar — notice the AI didn't suggest it
   again."* Group memory at work.
5. Close with a 10-second flash of trip-mode UI to show the primitives extend.

---

## Stack

| Layer        | Choice                                                        |
|--------------|--------------------------------------------------------------|
| Backend      | Python **FastAPI** (async), SQLAlchemy 2.x, Alembic          |
| Database     | **Postgres** with Row-Level Security (privacy enforcement)   |
| Frontend     | **Vite + React** SPA over a JSON API                         |
| AI synthesis | **Claude API** (Anthropic SDK), structured output + caching  |
| Execute      | Google Calendar API (planned, Day 3)                         |
| Venues       | Google Maps Platform (planned)                               |
| Ops          | Sentry (errors), structured logs around the LLM call         |

> The privacy model is the differentiator: a user can only ever read their *own*
> preferences (enforced by Postgres RLS), and the AI call happens server-side with an
> isolated reader that builds an **anonymized** constraint summary. See
> [docs/privacy.md](docs/privacy.md).

---

## Planned repo layout

```
backend/          FastAPI app (routers, services, repositories, models)
frontend/         Vite + React SPA
docs/             data model, schema, privacy story, LLM prompts
.claude/skills/   project dev workflows (prompt tuning, migrations+RLS, seed, leak check)
```

> This repo currently contains the **foundation only**: product + engineering docs, the
> data model, the LLM prompt, and the dev skills. App code lands in the scaffold step.

---

## Hackathon scope (honest)

Don't ship all five pillars in a weekend. The two that differentiate CoRoute and showcase
the architecture are **private constraints → AI options** and **group memory** — build
those hard. **Execution** gets one working integration (calendar invite) to prove the
pattern. **Multi-decision plans** and **attendance** are stubbed: the data model supports
them, the UI shows them, they don't have to be finished by Sunday.

---

## Documentation

- [CLAUDE.md](CLAUDE.md) — engineering guide, privacy invariants, conventions, commands
- [docs/data-model.md](docs/data-model.md) — tables, relationships, RLS notes
- [docs/schema.sql](docs/schema.sql) — reference DDL with RLS policies
- [docs/privacy.md](docs/privacy.md) — the end-to-end trust story
- [docs/prompts/generate-options.md](docs/prompts/generate-options.md) — the AI prompt + I/O contract

## Getting started

Prereqs: Python 3.11+, [uv](https://github.com/astral-sh/uv), Node 18+, a local Postgres
on `:5432` you can administer.

```bash
# 1. Database: create roles + db, then apply migrations
make db-roles
cp .env.example .env          # local dev values already point at the roles below
make migrate

# 2. Backend (FastAPI on :8000)
make api                      # or: cd backend && uv run uvicorn app.main:app --reload

# 3. Frontend (Vite + React on :5173)
cd frontend && npm install && npm run dev

# 4. Tests (incl. privacy invariants)
make test
```

Then open http://localhost:5173 — dev mode signs you in instantly (no email needed).

**AI options:** without an `ANTHROPIC_API_KEY` the option generator uses a deterministic
stub so everything runs offline. Set `ANTHROPIC_API_KEY` in `.env` to switch to real Claude
synthesis (model `claude-opus-4-8`). See [CLAUDE.md](CLAUDE.md) for the privacy invariants
any code must uphold.

### Local roles (the privacy model in dev)

`make db-roles` creates three Postgres roles so RLS is actually exercised locally:
- `coroute_app` — RLS-subject (no BYPASSRLS); the request path connects as this.
- `coroute_reader` — BYPASSRLS; used only by the server-side AI synthesis reader.
- `coroute_owner` — owns tables / runs migrations.
