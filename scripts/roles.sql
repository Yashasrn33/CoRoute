-- Local dev Postgres roles for CoRoute (idempotent). Run via `make db-roles`.
-- Kept in a .sql file so the $$ dollar-quoting isn't mangled by make/shell.
--   coroute_app    - request path, RLS-subject (NO BYPASSRLS)
--   coroute_reader - AI synthesis reader only (BYPASSRLS)
--   coroute_owner  - owns tables / runs migrations
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'coroute_app') THEN
    CREATE ROLE coroute_app LOGIN PASSWORD 'coroute_dev' NOSUPERUSER NOBYPASSRLS;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'coroute_reader') THEN
    CREATE ROLE coroute_reader LOGIN PASSWORD 'coroute_dev' NOSUPERUSER BYPASSRLS;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'coroute_owner') THEN
    CREATE ROLE coroute_owner LOGIN PASSWORD 'coroute_dev' NOSUPERUSER CREATEDB;
  END IF;
END
$$;
