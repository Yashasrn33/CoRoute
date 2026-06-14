-- CoRoute reference schema (Postgres)
-- =====================================================================
-- This file is REFERENCE DDL for whiteboarding and review. The authoritative
-- schema once code lands is the Alembic migrations under backend/alembic/.
-- The `migration-rls` skill keeps this file in sync with those migrations.
--
-- Privacy model (see docs/privacy.md and CLAUDE.md invariants):
--   * The request-path DB role is RLS-subject (NOT a superuser / BYPASSRLS).
--   * Each request runs:  SET LOCAL app.current_user_id = '<jwt sub uuid>';
--   * Policies below read current_setting('app.current_user_id')::uuid.
--   * A SEPARATE privileged reader role does AI synthesis server-side only.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- gen_random_uuid()

-- ---------- helper: current request user ----------------------------
-- Returns NULL when unset so policies fail closed.
CREATE OR REPLACE FUNCTION app_current_user_id() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT NULLIF(current_setting('app.current_user_id', true), '')::uuid
$$;

-- ---------- enums ---------------------------------------------------
CREATE TYPE member_role     AS ENUM ('owner', 'member');
CREATE TYPE pref_visibility AS ENUM ('private', 'group');
CREATE TYPE plan_type       AS ENUM ('dinner', 'watch_party', 'trip', 'activity', 'other');
CREATE TYPE plan_status     AS ENUM ('draft','collecting','options_ready','voting','decided','executed');
CREATE TYPE rsvp_status     AS ENUM ('yes', 'maybe', 'no', 'pending');
CREATE TYPE execution_kind  AS ENUM ('calendar', 'booking', 'payment_split');

-- ---------- users ---------------------------------------------------
CREATE TABLE users (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email         text NOT NULL UNIQUE,
  display_name  text NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
);

-- ---------- groups --------------------------------------------------
CREATE TABLE groups (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text NOT NULL,
  created_by  uuid NOT NULL REFERENCES users(id),
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------- group_members ------------------------------------------
CREATE TABLE group_members (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id   uuid NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role       member_role NOT NULL DEFAULT 'member',
  joined_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (group_id, user_id)
);
CREATE INDEX idx_group_members_user ON group_members(user_id);

-- membership predicate reused by group-scoped policies
CREATE OR REPLACE FUNCTION app_is_group_member(gid uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT EXISTS (
    SELECT 1 FROM group_members gm
    WHERE gm.group_id = gid AND gm.user_id = app_current_user_id()
  )
$$;

-- ---------- preferences (the trust story) --------------------------
CREATE TABLE preferences (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id             uuid NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
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
  UNIQUE (group_id, user_id)
);
CREATE INDEX idx_preferences_group ON preferences(group_id);

-- ---------- plans (self-ref for trip sub-plans) --------------------
CREATE TABLE plans (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id        uuid NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  created_by      uuid NOT NULL REFERENCES users(id),
  parent_plan_id  uuid REFERENCES plans(id) ON DELETE CASCADE,
  type            plan_type NOT NULL,
  status          plan_status NOT NULL DEFAULT 'draft',
  title           text NOT NULL,
  scheduled_for   timestamptz,
  location        text,
  constraints     jsonb NOT NULL DEFAULT '{}',
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_plans_group ON plans(group_id);
CREATE INDEX idx_plans_parent ON plans(parent_plan_id);

-- ---------- plan_attendees -----------------------------------------
CREATE TABLE plan_attendees (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id       uuid NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  rsvp          rsvp_status NOT NULL DEFAULT 'pending',
  responded_at  timestamptz,
  UNIQUE (plan_id, user_id)
);

-- ---------- options (AI-generated) ---------------------------------
CREATE TABLE options (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id       uuid NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  title         text NOT NULL,
  location      text,
  description   text,
  ai_reasoning  jsonb NOT NULL DEFAULT '{}',  -- per-constraint satisfaction; NEVER attributed
  external_ref  jsonb NOT NULL DEFAULT '{}',  -- e.g. Maps place id
  rank          integer,
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_options_plan ON options(plan_id);

-- ---------- votes ---------------------------------------------------
CREATE TABLE votes (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id     uuid NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  option_id   uuid NOT NULL REFERENCES options(id) ON DELETE CASCADE,
  user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  score       integer NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (plan_id, option_id, user_id)
);

-- ---------- outcomes (group memory) --------------------------------
CREATE TABLE outcomes (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id    uuid NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
  plan_id     uuid NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  option_id   uuid REFERENCES options(id) ON DELETE SET NULL,
  summary     text NOT NULL,
  happened_at timestamptz NOT NULL,
  metadata    jsonb NOT NULL DEFAULT '{}',   -- rotation/fairness signals
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_outcomes_group_time ON outcomes(group_id, happened_at DESC);

-- ---------- executions (loop closes here) --------------------------
CREATE TABLE executions (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id      uuid NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
  option_id    uuid NOT NULL REFERENCES options(id) ON DELETE CASCADE,
  kind         execution_kind NOT NULL,
  status       text NOT NULL DEFAULT 'pending',
  external_id  text,                          -- e.g. Google Calendar event id
  payload      jsonb NOT NULL DEFAULT '{}',
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- =====================================================================
-- Row-Level Security
-- =====================================================================
ALTER TABLE groups         ENABLE ROW LEVEL SECURITY;
ALTER TABLE group_members  ENABLE ROW LEVEL SECURITY;
ALTER TABLE preferences    ENABLE ROW LEVEL SECURITY;
ALTER TABLE plans          ENABLE ROW LEVEL SECURITY;
ALTER TABLE plan_attendees ENABLE ROW LEVEL SECURITY;
ALTER TABLE options        ENABLE ROW LEVEL SECURITY;
ALTER TABLE votes          ENABLE ROW LEVEL SECURITY;
ALTER TABLE outcomes       ENABLE ROW LEVEL SECURITY;
ALTER TABLE executions     ENABLE ROW LEVEL SECURITY;

-- preferences: owner sees/edits own rows; group members may read only when
-- a row is explicitly shared (visibility='group'). Private rows are owner-only.
CREATE POLICY pref_owner_all ON preferences
  USING (user_id = app_current_user_id())
  WITH CHECK (user_id = app_current_user_id());

CREATE POLICY pref_group_read_shared ON preferences
  FOR SELECT
  USING (visibility = 'group' AND app_is_group_member(group_id));

-- groups: members can read; (writes handled in app/service layer with checks)
CREATE POLICY group_member_read ON groups
  FOR SELECT USING (app_is_group_member(id));

-- group_members: a member can see the roster of their groups
CREATE POLICY gm_member_read ON group_members
  FOR SELECT USING (app_is_group_member(group_id));

-- generic group-scoped read/write for the remaining tables
CREATE POLICY plans_member_all ON plans
  USING (app_is_group_member(group_id))
  WITH CHECK (app_is_group_member(group_id));

CREATE POLICY attendees_member_all ON plan_attendees
  USING (app_is_group_member((SELECT p.group_id FROM plans p WHERE p.id = plan_id)))
  WITH CHECK (app_is_group_member((SELECT p.group_id FROM plans p WHERE p.id = plan_id)));

CREATE POLICY options_member_all ON options
  USING (app_is_group_member((SELECT p.group_id FROM plans p WHERE p.id = plan_id)))
  WITH CHECK (app_is_group_member((SELECT p.group_id FROM plans p WHERE p.id = plan_id)));

CREATE POLICY votes_member_all ON votes
  USING (app_is_group_member((SELECT p.group_id FROM plans p WHERE p.id = plan_id)))
  WITH CHECK (app_is_group_member((SELECT p.group_id FROM plans p WHERE p.id = plan_id)));

CREATE POLICY outcomes_member_all ON outcomes
  USING (app_is_group_member(group_id))
  WITH CHECK (app_is_group_member(group_id));

CREATE POLICY executions_member_all ON executions
  USING (app_is_group_member((SELECT p.group_id FROM plans p WHERE p.id = plan_id)))
  WITH CHECK (app_is_group_member((SELECT p.group_id FROM plans p WHERE p.id = plan_id)));

-- NOTE: the AI synthesis path connects as a SEPARATE privileged reader role
-- (BYPASSRLS) and is the only path permitted to read other members' private
-- preferences — server-side only, to build the anonymized constraint summary.
-- It must never be wired to a client-facing read endpoint. See docs/privacy.md.
