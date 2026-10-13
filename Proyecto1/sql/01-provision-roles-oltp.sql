-- SG-Food ELT: least-privilege reader for the OLTP database.
-- Run as the database administrator for sgfood_oltp.
-- The provisioning wrapper sets the password from an environment variable;
-- no password is stored in this file.

DO $provision$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sgfood_oltp_reader') THEN
        CREATE ROLE sgfood_oltp_reader;
    END IF;
END
$provision$;

ALTER ROLE sgfood_oltp_reader
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS
    NOINHERIT;

REVOKE CONNECT, CREATE, TEMPORARY ON DATABASE sgfood_oltp
FROM sgfood_oltp_reader;
GRANT CONNECT ON DATABASE sgfood_oltp TO sgfood_oltp_reader;

REVOKE CREATE ON SCHEMA oltp_sgfood FROM sgfood_oltp_reader;
GRANT USAGE ON SCHEMA oltp_sgfood TO sgfood_oltp_reader;

REVOKE SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
ON TABLE
    oltp_sgfood.sucursal,
    oltp_sgfood.categoria,
    oltp_sgfood.marca,
    oltp_sgfood.producto,
    oltp_sgfood.cliente,
    oltp_sgfood.venta,
    oltp_sgfood.venta_detalle
FROM sgfood_oltp_reader;

GRANT SELECT ON TABLE
    oltp_sgfood.sucursal,
    oltp_sgfood.categoria,
    oltp_sgfood.marca,
    oltp_sgfood.producto,
    oltp_sgfood.cliente,
    oltp_sgfood.venta,
    oltp_sgfood.venta_detalle
TO sgfood_oltp_reader;
