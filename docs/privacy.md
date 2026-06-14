# CoRoute privacy model — the end-to-end trust story

This is the differentiator versus iMessage polls and every voting app: **your constraints
stay yours.** A group member can never see another member's preferences, yet the AI
produces options that satisfy everyone. This document is the narrative behind the
non-negotiable invariants in [../CLAUDE.md](../CLAUDE.md) and the policies in
[schema.sql](schema.sql).

---

## The promise

> "Tell CoRoute you're vegetarian, capped at $25, and can't do loud places. Nobody in your
> group ever sees that. They just see three options that happen to work for everyone."

---

## How it holds up, layer by layer

### 1. Private by default (data)
`preferences.visibility` defaults to `private`. A row only becomes group-visible if its
owner explicitly opts in (`visibility = 'group'`). Constraints are stored in **structured
columns**, not freeform text, which keeps anonymized aggregation reliable.

### 2. Row-Level Security (database)
The request-path connects to Postgres as an **RLS-subject role** — never a superuser, never
`BYPASSRLS`. On every request the app opens a transaction and runs:

```sql
SET LOCAL app.current_user_id = '<jwt sub uuid>';
```

Policies key on `app_current_user_id()`:
- `preferences`: readable/writable only by the owner; group members may read a row **only**
  when it's explicitly `visibility = 'group'`.
- Group-scoped tables: readable/writable only by members of that `group_id`.
- The helper fails **closed** — if the session var is unset, `app_current_user_id()` is
  `NULL` and no rows match.

This means even a bug in the app layer (a forgotten `WHERE user_id = ...`) cannot leak
another user's private prefs — the database refuses to return them.

### 3. App-layer authorization (defense in depth)
The service/repository layer mirrors the RLS rules. Two independent layers must both fail
for a leak to happen. The frontend is never trusted to hide anything.

### 4. The isolated privileged reader (AI synthesis)
The one job that legitimately needs to read everyone's prefs is generating options. It runs
**server-side only**, on a **separate** DB connection/role that can read across the group's
attendees. Rules for this path:
- It lives in `services/` and is reachable **only** from `POST /plans/{id}/options`.
- It is **never** wired to any client-facing read endpoint.
- It reads prefs **only** to build the anonymized constraint summary — it never returns raw
  preference rows to anyone.

### 5. Anonymization / no attribution
Before anything reaches the LLM, per-user constraints are aggregated into a group-level
summary with **no names and no per-person mapping**:

```
group needs: vegetarian-friendly, ≤ $35/person, quiet (no loud bars),
             reachable without a car, wheelchair accessible
avoid: venues used in the last 5 outings (see history)
```

The same no-attribution rule applies to outputs: `options.ai_reasoning` explains why an
option fits the *group's* constraints, never "because Alex is vegan."

---

## What a CoRoute member can and cannot see

| Data                                   | Owner | Other group member | AI synthesis (server) |
|----------------------------------------|:-----:|:------------------:|:---------------------:|
| Own private preferences                |  ✅   |        ❌          |  ✅ (anonymized only) |
| Another member's private preferences   |  —    |        ❌          |  ✅ (anonymized only) |
| Preferences shared as `group`          |  ✅   |        ✅          |          ✅           |
| Plans, options, votes, outcomes        |  ✅ (members) | ✅ (members)  |          ✅           |
| Anonymized constraint summary          | n/a   |    not exposed     |  used internally      |

---

## Testing the promise (required)

The privacy invariants must be covered by tests; the `privacy-leak-check` skill drives
this. At minimum:

1. **DB-level:** with `app.current_user_id` set to user B, a `SELECT` on user A's private
   `preferences` returns **zero rows**.
2. **API-level:** no endpoint reachable by a member ever returns another member's raw
   preference fields. Fuzz the plan/options/group endpoints and assert the response schema
   contains no foreign preference data.
3. **Prompt-level:** the assembled LLM input and `ai_reasoning` outputs contain no member
   names tied to constraints.
4. **Fail-closed:** with the session var unset, group-scoped and preference reads return
   nothing.

---

## Why judges should care

This is a real security architecture — RLS + isolated reader + anonymization — not a
checkbox. It's what lets CoRoute do the thing voting apps structurally cannot: synthesize a
group answer from inputs no human in the group is allowed to see.
