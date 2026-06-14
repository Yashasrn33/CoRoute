"""initial schema — applies docs/schema.sql and grants role privileges

Revision ID: 0001
Revises:
Create Date: 2026-06-14

We apply docs/schema.sql verbatim so it stays the single human-readable source of
truth (the migration-rls skill keeps the two in lockstep). Then we grant the
RLS-subject app role and the BYPASSRLS synthesis reader the privileges they need.
"""

from collections.abc import Sequence

from alembic import op

from app.core.config import REPO_ROOT

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA_SQL = (REPO_ROOT / "docs" / "schema.sql").read_text()

GRANTS = """
GRANT USAGE ON SCHEMA public TO coroute_app, coroute_reader;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public
  TO coroute_app, coroute_reader;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO coroute_app, coroute_reader;
"""

# Objects created by docs/schema.sql, for a clean downgrade.
TABLES = [
    "executions", "outcomes", "votes", "options", "plan_attendees",
    "plans", "preferences", "group_members", "groups", "users",
]
ENUMS = [
    "member_role", "pref_visibility", "plan_type", "plan_status",
    "rsvp_status", "execution_kind",
]
FUNCTIONS = ["app_is_group_member(uuid)", "app_current_user_id()"]


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(SCHEMA_SQL)
    bind.exec_driver_sql(GRANTS)


def downgrade() -> None:
    bind = op.get_bind()
    for t in TABLES:
        bind.exec_driver_sql(f"DROP TABLE IF EXISTS {t} CASCADE")
    for fn in FUNCTIONS:
        bind.exec_driver_sql(f"DROP FUNCTION IF EXISTS {fn} CASCADE")
    for e in ENUMS:
        bind.exec_driver_sql(f"DROP TYPE IF EXISTS {e} CASCADE")
