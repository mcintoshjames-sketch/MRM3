-- Create an analytics read-only role and grant it minimal access.
\set ON_ERROR_STOP on

\if :{?analytics_role}
\else
\set analytics_role 'analytics_readonly'
\endif

\if :{?app_user}
\else
\set app_user ''
\endif

DO $$
DECLARE
  role_name text := :'analytics_role';
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
    EXECUTE format('CREATE ROLE %I NOLOGIN', role_name);
  END IF;
END
$$;

DO $$
DECLARE
  role_name text := :'analytics_role';
BEGIN
  EXECUTE format('GRANT USAGE ON SCHEMA public TO %I', role_name);
  EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA public TO %I', role_name);
  EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO %I', role_name);
END
$$;

DO $$
DECLARE
  role_name text := :'analytics_role';
  target_user text := :'app_user';
BEGIN
  IF target_user IS NOT NULL AND target_user <> '' THEN
    EXECUTE format('GRANT %I TO %I', role_name, target_user);
  END IF;
END
$$;
