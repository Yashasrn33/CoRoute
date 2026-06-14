"""add group_pref_status() readiness helper (existence, not content)

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-14

Members need to see WHO has filled preferences ("3 of 4 ready") without seeing
the content (RLS keeps content owner-only). A SECURITY DEFINER function returns
booleans only, guarded to members of the group. Kept in sync with docs/schema.sql.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FN = """
CREATE OR REPLACE FUNCTION group_pref_status(gid uuid)
RETURNS TABLE(user_id uuid, has_prefs boolean)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT gm.user_id,
         EXISTS (SELECT 1 FROM preferences p
                 WHERE p.group_id = gm.group_id AND p.user_id = gm.user_id)
  FROM group_members gm
  WHERE gm.group_id = gid AND app_is_group_member(gid)
$$;
"""


def upgrade() -> None:
    op.execute(FN)
    op.execute("GRANT EXECUTE ON FUNCTION group_pref_status(uuid) TO coroute_app, coroute_reader")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS group_pref_status(uuid)")
