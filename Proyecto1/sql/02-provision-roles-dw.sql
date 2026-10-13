-- SG-Food ELT: least-privilege loader and dbt runner for the DW database.
-- Run as the database administrator for sgfood_dw.
-- The provisioning wrapper sets passwords from environment variables;
-- no password is stored in this file.

DO $provision$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sgfood_raw_loader') THEN
        CREATE ROLE sgfood_raw_loader;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sgfood_dbt_runner') THEN
        CREATE ROLE sgfood_dbt_runner;
    END IF;
END
$provision$;

ALTER ROLE sgfood_raw_loader
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS
    NOINHERIT;

ALTER ROLE sgfood_dbt_runner
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS
    NOINHERIT;

REVOKE CONNECT, CREATE, TEMPORARY ON DATABASE sgfood_dw
FROM sgfood_raw_loader;
GRANT CONNECT ON DATABASE sgfood_dw TO sgfood_raw_loader;

REVOKE CONNECT, CREATE, TEMPORARY ON DATABASE sgfood_dw
FROM sgfood_dbt_runner;
GRANT CONNECT ON DATABASE sgfood_dw TO sgfood_dbt_runner;

REVOKE USAGE, CREATE ON SCHEMA raw
FROM sgfood_raw_loader;
GRANT USAGE, CREATE ON SCHEMA raw TO sgfood_raw_loader;

REVOKE USAGE, CREATE ON SCHEMA staging, intermediate, marts
FROM sgfood_raw_loader;
REVOKE SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
ON ALL TABLES IN SCHEMA staging, intermediate, marts
FROM sgfood_raw_loader;

REVOKE USAGE, CREATE ON SCHEMA raw
FROM sgfood_dbt_runner;
GRANT USAGE ON SCHEMA raw TO sgfood_dbt_runner;
REVOKE SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
ON ALL TABLES IN SCHEMA raw
FROM sgfood_dbt_runner;
GRANT SELECT ON ALL TABLES IN SCHEMA raw TO sgfood_dbt_runner;

REVOKE USAGE, CREATE ON SCHEMA staging, intermediate, marts
FROM sgfood_dbt_runner;
GRANT USAGE, CREATE ON SCHEMA staging, intermediate, marts
TO sgfood_dbt_runner;

-- The object creator is explicit: future raw tables created by the loader
-- become readable by the dbt runner, without granting it write privileges.
ALTER DEFAULT PRIVILEGES FOR ROLE sgfood_raw_loader IN SCHEMA raw
REVOKE ALL PRIVILEGES ON TABLES FROM sgfood_dbt_runner;
ALTER DEFAULT PRIVILEGES FOR ROLE sgfood_raw_loader IN SCHEMA raw
GRANT SELECT ON TABLES TO sgfood_dbt_runner;
