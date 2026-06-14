---
name: seed-demo-data
description: Generate CoRoute's "World Cup final watch party" demo group with ~6 months of history so the group-memory feature lands in the demo. Use when preparing the demo, refreshing seed data, or building the fixture the option-prompt-tuning skill evaluates against.
---

# Seed demo data

The group-memory feature only lands in a demo if the group has a believable past. This skill
seeds the canonical scenario so "the AI didn't suggest the same sports bar again" is real.

## When to use
- Preparing the 2-minute demo (see README).
- Refreshing or resetting local seed data.
- Producing the anonymized fixture the `option-prompt-tuning` skill evals against.

## What to create
A `make seed` script (idempotent) that inserts:

1. **One group** — e.g. "The Group Chat" — with **4 users**:
   - Distinct, demo-legible private `preferences`:
     - User A: vegetarian, budget ≤ $30, dislikes loud bars.
     - User B: vegan, budget ≤ $25, no car (transit only).
     - User C: no dietary limits, budget ≤ $50, dislikes long waits.
     - User D: step-free access needed, budget ≤ $35.
   - All preferences `visibility = 'private'` (the whole point).
2. **~6 months of history** — ~10–12 past `plans` (decided/executed) with `outcomes`,
   including **a recent visit to "The Anchor Sports Bar"** so anti-repeat is demonstrable.
   Vary venues and include 1–2 rotation/fairness signals in `outcomes.metadata`
   (who picked, who flaked) to show memory beyond venues.
3. **One open plan** — "World Cup final, Sunday" in `collecting`/`options_ready`, with all 4
   as `yes`/`maybe` attendees, ready to generate options live.

## Steps
1. Read `docs/data-model.md` for exact columns and the demo prefs above.
2. Implement/extend the seed script; make it idempotent (clear demo group first or upsert).
3. Insert users → group → members → preferences → historical plans/outcomes → the open plan
   + attendees. Respect FKs and RLS (seed via a privileged/admin connection).
4. **Export the anonymized fixture** for the open plan (aggregated constraints + last-5
   outcomes) for use by `option-prompt-tuning`.
5. Verify: run the option endpoint on the open plan and confirm options avoid "The Anchor".

## Guardrails
- Use obviously-fake names/emails; no real personal data.
- Dates are relative to demo day — accept a base date as a parameter (don't hardcode a year
  that goes stale; convert "6 months ago" from the provided base date).
- Keep prefs private; the demo's reveal is showing them side-by-side in an admin/owner view,
  not exposing them through the member API.
