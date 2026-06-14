---
name: migration-rls
description: Author a CoRoute Alembic migration together with its Postgres Row-Level Security policies, keep docs/schema.sql in sync, and run the privacy checklist. Use whenever adding or changing tables, columns, or RLS policies — especially anything touching preferences or group-scoped data.
---

# Migration + RLS

In CoRoute, a schema change is incomplete without its RLS policy. This skill makes the two
move together so private preferences can never leak through a new table or column.

## When to use
- Adding/altering a table or column.
- Adding or changing RLS policies.
- Any change to `preferences` or group-scoped tables.

## Before you start
- Read the privacy invariants in `CLAUDE.md` and `docs/privacy.md`.
- Read `docs/schema.sql` — it's the reference DDL and shows the existing policy patterns
  (`app_current_user_id()`, `app_is_group_member()`, fail-closed helpers).

## Steps
1. **Write the Alembic migration** under `backend/alembic/` for the schema change (tables,
   columns, enums, indexes). Use `op.execute(...)` for `CREATE POLICY` /
   `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` — Alembic won't autogenerate these.
2. **Enable RLS** on every new table (`ENABLE ROW LEVEL SECURITY`). A table without RLS is
   a leak by default.
3. **Add policies** following the existing patterns:
   - User-owned data (like `preferences`): `USING (user_id = app_current_user_id())`,
     owner-only for private rows; group read only when explicitly shared.
   - Group-scoped data: gate on `app_is_group_member(group_id)` (or via the parent plan's
     group for child tables).
   - Helpers must **fail closed** when `app.current_user_id` is unset.
4. **Sync `docs/schema.sql`** to match the migration exactly (DDL + policies).
5. **Run the privacy checklist** (below). Use the `privacy-leak-check` skill to verify at
   API level.
6. **Provide a downgrade** path in the migration.

## Privacy checklist (must pass)
- [ ] RLS enabled on every new table.
- [ ] New columns on `preferences` are not exposed by any group-readable policy/view.
- [ ] Owner-only reads on private `preferences` verified: with `app.current_user_id` set to
      user B, selecting user A's private rows returns zero rows.
- [ ] Group-scoped tables gate on membership; non-members get zero rows.
- [ ] Fail-closed verified: unset session var ⇒ no rows.
- [ ] `docs/schema.sql` matches the migration.

## Guardrails
- The request-path DB role must remain RLS-subject — never grant it `BYPASSRLS`.
- Only the isolated AI-synthesis reader role bypasses RLS; never extend that to request
  handlers.
