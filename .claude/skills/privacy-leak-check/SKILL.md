---
name: privacy-leak-check
description: Audit CoRoute's API and DB to confirm raw per-user preferences are never returned to anyone but their owner. Use before merging anything that touches preferences, endpoints, response schemas, the LLM path, or RLS — and as a release gate before the demo.
---

# Privacy-leak check

CoRoute's core promise is that one member can never see another's constraints. This skill is
the adversarial audit that proves it across both layers (RLS + app) and the LLM path.

## When to use
- Before merging changes to `preferences`, endpoints, response schemas, RLS, or the
  synthesis path.
- As a pre-demo release gate.

## Reference
- Invariants: `CLAUDE.md` (Privacy invariants) and `docs/privacy.md`.
- Policies: `docs/schema.sql`.

## Audit steps

### 1. DB layer (RLS)
- With `SET LOCAL app.current_user_id = '<user B>'`, `SELECT * FROM preferences` for user
  A's private rows ⇒ **expect 0 rows**.
- Repeat for every group-scoped table from a non-member ⇒ **0 rows**.
- **Fail-closed:** unset `app.current_user_id` ⇒ group/preference reads return 0 rows.
- Confirm the request-path DB role is **not** `BYPASSRLS` (`\du` / `rolbypassrls = false`).

### 2. API layer
- Enumerate every endpoint reachable by a normal member.
- For each, assert no response body contains another member's raw preference fields
  (`diet`, `budget_*`, `vibe_dislikes`, `transportation`, `hard_nos`,
  `accessibility_needs`, `notes`). The only preference data any response may contain is the
  caller's own, or rows explicitly `visibility='group'`.
- Probe the obvious leak vectors: plan detail, options list (`ai_reasoning`), group roster,
  votes, outcomes, any `/me` or admin route.
- Grep response schemas (Pydantic) for foreign-preference fields that shouldn't be there.

### 3. LLM path
- Inspect the assembled prompt input: it must be the **anonymized aggregate** — no member
  names, no per-person constraint mapping.
- Inspect generated `ai_reasoning`: it explains fit for the *group*, never "because <name>
  is vegan." Grep outputs for member names tied to constraints.
- Confirm the synthesis privileged reader is reachable **only** from
  `POST /plans/{id}/options`, never a client read endpoint.

## Output
Produce a short report: each check, pass/fail, and the offending location for any failure.
Any fail blocks merge / demo. Where practical, encode these as `pytest` tests so the audit
is repeatable (see `docs/privacy.md` → Testing).

## Guardrails
- Treat "no obvious leak found" as insufficient — actively try to leak (different user
  tokens, direct ID access, fuzzed params) before declaring pass.
