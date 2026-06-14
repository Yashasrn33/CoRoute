"""add user_default_preferences (global prefs template)

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-14

A per-user default preferences template that pre-fills a group's preferences when
the user creates or joins a group. Owner-only RLS (the user's own data). Kept in
sync with docs/schema.sql.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Idempotent (see 0006): a fresh DB creates this from docs/schema.sql in 0001.
TABLE = """
CREATE TABLE IF NOT EXISTS user_default_preferences (
  user_id              uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  diet                 text[] NOT NULL DEFAULT '{}',
  budget_min           integer,
  budget_max           integer,
  vibe_dislikes        text[] NOT NULL DEFAULT '{}',
  transportation       text[] NOT NULL DEFAULT '{}',
  hard_nos             text[] NOT NULL DEFAULT '{}',
  accessibility_needs  text[] NOT NULL DEFAULT '{}',
  notes                text,
  updated_at           timestamptz NOT NULL DEFAULT now()
);
"""

POLICY = """
ALTER TABLE user_default_preferences ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS udp_owner_all ON user_default_preferences;
CREATE POLICY udp_owner_all ON user_default_preferences
  USING (user_id = app_current_user_id())
  WITH CHECK (user_id = app_current_user_id());
"""

GRANT = (
    "GRANT SELECT, INSERT, UPDATE, DELETE ON user_default_preferences "
    "TO coroute_app, coroute_reader"
)


def upgrade() -> None:
    op.execute(TABLE)
    op.execute(POLICY)
    op.execute(GRANT)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_default_preferences CASCADE")
