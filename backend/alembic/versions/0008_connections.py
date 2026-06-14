"""add connections (friends) + app_is_friend + add-friend-to-group policy

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-14

Friend graph: connections(requester -> addressee, status). RLS lets each party
see/manage their own rows; only the addressee accepts. app_is_friend() (SECURITY
DEFINER) powers a new group_members INSERT policy so a member can add a confirmed
friend directly to a group. Kept in sync with docs/schema.sql.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Idempotent (see 0006): a fresh DB creates these from docs/schema.sql in 0001.
TABLE = """
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'connection_status') THEN
    CREATE TYPE connection_status AS ENUM ('pending', 'accepted');
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS connections (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  requester_id  uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  addressee_id  uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status        connection_status NOT NULL DEFAULT 'pending',
  created_at    timestamptz NOT NULL DEFAULT now(),
  responded_at  timestamptz,
  UNIQUE (requester_id, addressee_id),
  CHECK (requester_id <> addressee_id)
);
CREATE INDEX IF NOT EXISTS idx_connections_addressee ON connections(addressee_id);
"""

FRIEND_FN = """
CREATE OR REPLACE FUNCTION app_is_friend(a uuid, b uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM connections c
    WHERE c.status = 'accepted'
      AND ((c.requester_id = a AND c.addressee_id = b)
        OR (c.requester_id = b AND c.addressee_id = a))
  )
$$;
"""

POLICIES = """
ALTER TABLE connections ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS conn_select ON connections;
CREATE POLICY conn_select ON connections FOR SELECT
  USING (requester_id = app_current_user_id() OR addressee_id = app_current_user_id());
DROP POLICY IF EXISTS conn_insert ON connections;
CREATE POLICY conn_insert ON connections FOR INSERT
  WITH CHECK (requester_id = app_current_user_id());
DROP POLICY IF EXISTS conn_update ON connections;
CREATE POLICY conn_update ON connections FOR UPDATE
  USING (addressee_id = app_current_user_id())
  WITH CHECK (addressee_id = app_current_user_id());
DROP POLICY IF EXISTS conn_delete ON connections;
CREATE POLICY conn_delete ON connections FOR DELETE
  USING (requester_id = app_current_user_id() OR addressee_id = app_current_user_id());

-- A group member may add a confirmed friend directly to the group.
DROP POLICY IF EXISTS gm_insert_friend ON group_members;
CREATE POLICY gm_insert_friend ON group_members FOR INSERT
  WITH CHECK (app_is_group_member(group_id)
             AND app_is_friend(app_current_user_id(), user_id));
"""

GRANTS = """
GRANT SELECT, INSERT, UPDATE, DELETE ON connections TO coroute_app, coroute_reader;
GRANT EXECUTE ON FUNCTION app_is_friend(uuid, uuid) TO coroute_app, coroute_reader;
"""


def upgrade() -> None:
    op.execute(TABLE)
    op.execute(FRIEND_FN)
    op.execute(POLICIES)
    op.execute(GRANTS)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS gm_insert_friend ON group_members")
    op.execute("DROP TABLE IF EXISTS connections CASCADE")
    op.execute("DROP FUNCTION IF EXISTS app_is_friend(uuid, uuid)")
    op.execute("DROP TYPE IF EXISTS connection_status")
