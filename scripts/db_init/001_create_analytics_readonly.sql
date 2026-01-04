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

SELECT format('CREATE ROLE %I NOLOGIN', :'analytics_role')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'analytics_role')
\gexec

SELECT format('GRANT USAGE ON SCHEMA public TO %I', :'analytics_role')
\gexec
SELECT format('GRANT SELECT ON ALL TABLES IN SCHEMA public TO %I', :'analytics_role')
\gexec
SELECT format('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO %I', :'analytics_role')
\gexec

\if :'app_user' <> ''
SELECT format('GRANT %I TO %I', :'analytics_role', :'app_user')
\gexec
\endif
