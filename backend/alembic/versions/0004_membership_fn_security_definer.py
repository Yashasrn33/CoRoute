"""make app_is_group_member SECURITY DEFINER to stop RLS recursion

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-14

group_members' SELECT policy calls app_is_group_member(), which itself reads
group_members under RLS -> calls app_is_group_member() -> infinite recursion
("stack depth limit exceeded"). Running the helper as SECURITY DEFINER (as the
table-owner) makes its internal read bypass RLS, breaking the loop. Kept in sync
with docs/schema.sql.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFINER = """
CREATE OR REPLACE FUNCTION app_is_group_member(gid uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM group_members gm
    WHERE gm.group_id = gid AND gm.user_id = app_current_user_id()
  )
$$;
"""

INVOKER = """
CREATE OR REPLACE FUNCTION app_is_group_member(gid uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM group_members gm
    WHERE gm.group_id = gid AND gm.user_id = app_current_user_id()
  )
$$;
"""


def upgrade() -> None:
    op.execute(DEFINER)


def downgrade() -> None:
    op.execute(INVOKER)
