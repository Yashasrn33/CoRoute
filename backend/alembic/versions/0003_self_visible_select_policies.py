"""let creators/self see groups + own memberships (fix INSERT ... RETURNING)

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-14

INSERT ... RETURNING (used by the ORM to fetch generated ids) requires the new
row to pass the SELECT policy. On group creation the owner isn't a member yet,
and a membership row's visibility depended on itself. Widen the SELECT policies
with a self/creator arm. Kept in sync with docs/schema.sql.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP POLICY group_member_read ON groups")
    op.execute(
        "CREATE POLICY group_member_read ON groups "
        "FOR SELECT USING (app_is_group_member(id) OR created_by = app_current_user_id())"
    )
    op.execute("DROP POLICY gm_member_read ON group_members")
    op.execute(
        "CREATE POLICY gm_member_read ON group_members "
        "FOR SELECT USING (app_is_group_member(group_id) OR user_id = app_current_user_id())"
    )


def downgrade() -> None:
    op.execute("DROP POLICY group_member_read ON groups")
    op.execute("CREATE POLICY group_member_read ON groups FOR SELECT USING (app_is_group_member(id))")
    op.execute("DROP POLICY gm_member_read ON group_members")
    op.execute(
        "CREATE POLICY gm_member_read ON group_members "
        "FOR SELECT USING (app_is_group_member(group_id))"
    )
