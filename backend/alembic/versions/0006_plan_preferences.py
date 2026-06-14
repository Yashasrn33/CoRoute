"""add plan_preferences (per-user, per-plan overrides)

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-14

Per-plan preferences that override a user's general (group) preferences for a
single plan. Same privacy model as `preferences`: owner-only by default, group
read only when explicitly shared; the synthesis reader aggregates anonymously.
Kept in sync with docs/schema.sql.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Idempotent: a fresh DB creates this table from docs/schema.sql in migration 0001,
# so guard everything to converge on both the fresh and incremental paths.
TABLE = """
CREATE TABLE IF NOT EXISTS plan_preferences (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id              uuid NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  user_id              uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  visibility           pref_visibility NOT NULL DEFAULT 'private',
  diet                 text[] NOT NULL DEFAULT '{}',
  budget_min           integer,
  budget_max           integer,
  vibe_dislikes        text[] NOT NULL DEFAULT '{}',
  transportation       text[] NOT NULL DEFAULT '{}',
  hard_nos             text[] NOT NULL DEFAULT '{}',
  accessibility_needs  text[] NOT NULL DEFAULT '{}',
  notes                text,
  updated_at           timestamptz NOT NULL DEFAULT now(),
  UNIQUE (plan_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_plan_preferences_plan ON plan_preferences(plan_id);
"""

POLICIES = """
ALTER TABLE plan_preferences ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS planpref_owner_all ON plan_preferences;
CREATE POLICY planpref_owner_all ON plan_preferences
  USING (user_id = app_current_user_id())
  WITH CHECK (user_id = app_current_user_id());

DROP POLICY IF EXISTS planpref_group_read_shared ON plan_preferences;
CREATE POLICY planpref_group_read_shared ON plan_preferences
  FOR SELECT
  USING (visibility = 'group'
         AND app_is_group_member((SELECT p.group_id FROM plans p WHERE p.id = plan_id)));
"""

GRANTS = (
    "GRANT SELECT, INSERT, UPDATE, DELETE ON plan_preferences "
    "TO coroute_app, coroute_reader"
)


def upgrade() -> None:
    op.execute(TABLE)
    op.execute(POLICIES)
    op.execute(GRANTS)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS plan_preferences CASCADE")
