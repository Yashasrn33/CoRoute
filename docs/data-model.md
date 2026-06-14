# CoRoute data model

This is the authoritative narrative of the data model — be ready to whiteboard it. The
reference DDL is in [schema.sql](schema.sql); the *authoritative* schema once code lands is
the Alembic migrations (kept in sync via the `migration-rls` skill).

The model is built so the demo's primitives (private prefs → AI options → vote → execute →
memory) extend unchanged to trips (linked sub-plans) without a redesign.

---

## Entity overview

```
users ──< group_members >── groups
                               │
        users ──< preferences (per user, per group, visibility=private) 
                               │
                          plans (type, status, scheduled_for, location,
                               │   parent_plan_id ──┐ self-ref for trip sub-plans)
                               │                    │
        ┌──────────────┬───────┴────────┬──────────┴───────┐
   plan_attendees    options          votes             outcomes
   (yes/maybe/no)  (AI-generated,   (per user,       (what happened =
                    ai_reasoning)    per option)      group memory)
                        │
                   executions (calendar event id, booking ref)
```

---

## Tables

### `users`
Identity. Magic-link auth (passwordless); JWT `sub` = `users.id`.
- `id` uuid pk, `email` unique, `display_name`, `created_at`.

### `groups`
A standing group of friends.
- `id` uuid pk, `name`, `created_by` → users, `created_at`.

### `group_members`
Membership + role; backs invite-by-link.
- `id` uuid pk, `group_id` → groups, `user_id` → users, `role` (`owner`|`member`),
  `joined_at`. Unique `(group_id, user_id)`.

### `preferences` — the trust story
A person's constraints, **scoped per group** (your budget with college friends ≠ with
coworkers).
- `id` uuid pk, `group_id` → groups, `user_id` → users,
- `visibility` (`private`|`group`) **default `private`**,
- structured constraint columns (kept structured, not freeform — ~10–12 fields):
  `diet` (text[]), `budget_min`, `budget_max`, `vibe_dislikes` (text[]),
  `transportation` (text[]), `hard_nos` (text[]), `accessibility_needs` (text[]),
  `notes` (short free text), `updated_at`.
- Unique `(group_id, user_id)`.
- **RLS:** a row is readable only by `user_id = current_user` (when `private`), or by group
  members (when explicitly `group`). This is invariant #1/#2 in CLAUDE.md.

### `plans`
A decision to make. Dinner Saturday, watch party Sunday, or a trip (which links sub-plans).
- `id` uuid pk, `group_id` → groups, `created_by` → users,
- `type` (`dinner`|`watch_party`|`trip`|`activity`|…),
- `status` (`draft`|`collecting`|`options_ready`|`voting`|`decided`|`executed`),
- `title`, `scheduled_for` (timestamptz, nullable), `location` (text, nullable),
- `parent_plan_id` → plans (nullable, **self-ref**) for trip sub-plans,
- `constraints` jsonb (organizer notes / overrides), `created_at`.

### `plan_attendees` — mixed-attendance reality
Who's actually coming. Planning starts before this is settled.
- `id` uuid pk, `plan_id` → plans, `user_id` → users,
  `rsvp` (`yes`|`maybe`|`no`|`pending`), `responded_at`. Unique `(plan_id, user_id)`.
- The AI considers prefs for `yes` + `maybe` attendees.

### `options` — AI-generated
The 3–5 concrete options the AI produced for a plan.
- `id` uuid pk, `plan_id` → plans, `title`, `location`, `description`,
- `ai_reasoning` jsonb — per-constraint satisfaction + why-not-repeat ("avoids last
  month's venue"). Surfaced in UI; **never contains attributions**.
- `external_ref` jsonb (e.g. Maps place id), `rank` (AI suggested order), `created_at`.

### `votes`
Group voting; ranked or thumbs (`score`).
- `id` uuid pk, `plan_id` → plans, `option_id` → options, `user_id` → users,
  `score` int, `created_at`. Unique `(plan_id, option_id, user_id)`.

### `outcomes` — group memory
What the group actually did. Read back into the next plan's prompt (last 5) so the AI
avoids repeats and notices rotations.
- `id` uuid pk, `group_id` → groups, `plan_id` → plans, `option_id` → options (nullable),
- `summary` (text), `happened_at`, `metadata` jsonb (e.g. who picked, who flaked — used for
  fairness/rotation, stored at group scope), `created_at`.

### `executions`
The execute step output — proves the loop closes.
- `id` uuid pk, `plan_id` → plans, `option_id` → options,
- `kind` (`calendar`|`booking`|`payment_split`), `status`,
- `external_id` (e.g. Google Calendar event id), `payload` jsonb, `created_at`.

---

## RLS summary

- `app.current_user_id` is set per request via `SET LOCAL`.
- `preferences`: `SELECT/UPDATE/DELETE` only where `user_id = current_user`
  (plus group-members read when `visibility='group'`).
- Group-scoped tables (`groups`, `group_members`, `plans`, `plan_attendees`, `options`,
  `votes`, `outcomes`, `executions`): readable/writable only by members of the relevant
  `group_id`.
- The LLM synthesis path uses a separate privileged reader (see
  [privacy.md](privacy.md)); it is the *only* path that reads other members' prefs, and it
  never returns raw rows.

See [schema.sql](schema.sql) for the concrete policies.
