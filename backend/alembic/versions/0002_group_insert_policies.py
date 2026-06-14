"""add INSERT RLS policies for groups and group_members

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-14

0001's groups/group_members had SELECT-only policies, so the RLS-subject app role
could not create or join groups. Add self-scoped INSERT policies:
  * groups: a user may insert a group they own (created_by = self)
  * group_members: a user may add only themselves (covers create + invite-join)
Kept in sync with docs/schema.sql.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE POLICY group_insert_self ON groups "
        "FOR INSERT WITH CHECK (created_by = app_current_user_id())"
    )
    op.execute(
        "CREATE POLICY gm_insert_self ON group_members "
        "FOR INSERT WITH CHECK (user_id = app_current_user_id())"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS gm_insert_self ON group_members")
    op.execute("DROP POLICY IF EXISTS group_insert_self ON groups")
