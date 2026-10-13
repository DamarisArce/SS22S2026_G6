#!/usr/bin/env python3
"""Provision SG-Food least-privilege PostgreSQL roles.

This script does not accept passwords as command-line arguments and never logs
password values. It reads the local .env file when present, without overriding
already-exported environment variables. SQL changes are transactional and can
be repeated safely.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import os
import re
import secrets
import shlex
import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"
SCRAM_ITERATIONS = 4096
SCRAM_SALT_BYTES = 16
SCRAM_VERIFIER_RE = re.compile(
    r"^SCRAM-SHA-256\$(?P<iterations>[0-9]+):(?P<salt>[A-Za-z0-9+/]+=*)\$"
    r"(?P<stored>[A-Za-z0-9+/]+=*):(?P<server>[A-Za-z0-9+/]+=*)$"
)

EXPECTED = {
    "oltp": {
        "database": "sgfood_oltp",
        "database_env": "POSTGRES_OLTP_DB",
        "admin": "POSTGRES_OLTP_USER",
        "schemas": ("oltp_sgfood",),
        "tables": (
            "sucursal",
            "categoria",
            "marca",
            "producto",
            "cliente",
            "venta",
            "venta_detalle",
        ),
    },
    "dw": {
        "database": "sgfood_dw",
        "database_env": "POSTGRES_DW_DB",
        "admin": "POSTGRES_DW_USER",
        "schemas": ("raw", "staging", "intermediate", "marts"),
        "tables": (),
    },
}


def load_dotenv(path: Path) -> None:
    """Load simple KEY=value entries without overriding the process env."""
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = raw_value.strip()
        if value and value[0] in "'\"":
            try:
                value = shlex.split(value, comments=False)[0]
            except ValueError as exc:
                raise ValueError(f"invalid quoted value for {key}") from exc
        os.environ[key] = value


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value or value.startswith("REPLACE_WITH_"):
        raise ValueError(f"missing local value for {name}")
    return value


def scram_sha256_verifier(password: str, salt: bytes | None = None) -> str:
    """Return a PostgreSQL SCRAM-SHA-256 verifier, never the clear password."""
    if not password:
        raise ValueError("role password cannot be empty")
    salt = secrets.token_bytes(SCRAM_SALT_BYTES) if salt is None else salt
    if len(salt) < 16:
        raise ValueError("SCRAM salt must contain at least 16 bytes")
    salted_password = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, SCRAM_ITERATIONS
    )
    client_key = hmac.new(salted_password, b"Client Key", hashlib.sha256).digest()
    stored_key = hashlib.sha256(client_key).digest()
    server_key = hmac.new(salted_password, b"Server Key", hashlib.sha256).digest()
    encode = lambda value: base64.b64encode(value).decode("ascii")
    return (
        f"SCRAM-SHA-256${SCRAM_ITERATIONS}:{encode(salt)}$"
        f"{encode(stored_key)}:{encode(server_key)}"
    )


def verify_scram_sha256_verifier(verifier: str, password: str) -> bool:
    match = SCRAM_VERIFIER_RE.fullmatch(verifier)
    if match is None:
        return False
    try:
        iterations = int(match.group("iterations"))
        salt = base64.b64decode(match.group("salt"), validate=True)
        stored_key = base64.b64decode(match.group("stored"), validate=True)
        server_key = base64.b64decode(match.group("server"), validate=True)
    except (ValueError, TypeError):
        return False
    if iterations < 1 or len(salt) < 16 or len(stored_key) != 32 or len(server_key) != 32:
        return False
    salted_password = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    client_key = hmac.new(salted_password, b"Client Key", hashlib.sha256).digest()
    expected_stored = hashlib.sha256(client_key).digest()
    expected_server = hmac.new(salted_password, b"Server Key", hashlib.sha256).digest()
    return hmac.compare_digest(stored_key, expected_stored) and hmac.compare_digest(
        server_key, expected_server
    )


def import_driver() -> tuple[Any, Any]:
    try:
        import psycopg  # type: ignore[import-not-found]
        from psycopg import sql  # type: ignore[import-not-found]

        return psycopg, sql
    except ImportError:
        try:
            import psycopg2  # type: ignore[import-not-found]
            from psycopg2 import sql  # type: ignore[import-not-found]

            return psycopg2, sql
        except ImportError as exc:
            raise RuntimeError(
                "install psycopg or psycopg2 in the execution environment"
            ) from exc


def connection_values(target: str) -> dict[str, str]:
    prefix = "POSTGRES_OLTP" if target == "oltp" else "POSTGRES_DW"
    return {
        "host": os.environ.get(f"{prefix}_HOST", "127.0.0.1"),
        "port": required(f"{prefix}_HOST_PORT"),
        "dbname": required(f"{prefix}_DB"),
        "user": required(f"{prefix}_USER"),
        "password": required(f"{prefix}_PASSWORD"),
    }


def role_passwords(target: str) -> dict[str, str]:
    if target == "oltp":
        values = {"sgfood_oltp_reader": required("SGFOOD_OLTP_READER_PASSWORD")}
    else:
        values = {
            "sgfood_raw_loader": required("SGFOOD_RAW_LOADER_PASSWORD"),
            "sgfood_dbt_runner": required("SGFOOD_DBT_RUNNER_PASSWORD"),
        }
    if len(set(values.values())) != len(values):
        raise ValueError("role passwords must be distinct")
    configured_passwords = [
        value
        for name, value in os.environ.items()
        if name.endswith("_PASSWORD") and value and not value.startswith("REPLACE_WITH_")
    ]
    for password in values.values():
        if configured_passwords.count(password) > 1:
            raise ValueError("role passwords must not be reused")
    return values


def validate_preconditions(cursor: Any, target: str, admin_user: str) -> None:
    """Validate identity, required objects, and target-role memberships first."""
    expected = EXPECTED[target]
    cursor.execute(
        """
        SELECT current_database(), current_user, role.rolsuper
        FROM pg_roles AS role
        WHERE role.rolname = current_user
        """
    )
    identity = cursor.fetchone()
    expected_database = expected["database"]
    configured_database = required(expected["database_env"])
    if (
        identity is None
        or identity[0] != expected_database
        or configured_database != expected_database
        or identity[1] != admin_user
        or not identity[2]
    ):
        raise RuntimeError("connection is not the expected database superuser")

    schemas = list(expected["schemas"])
    cursor.execute(
        "SELECT nspname FROM pg_namespace WHERE nspname = ANY(%s)",
        (schemas,),
    )
    found_schemas = {row[0] for row in cursor.fetchall()}
    missing_schemas = sorted(set(schemas) - found_schemas)
    if missing_schemas:
        raise RuntimeError(f"required schemas are missing: {', '.join(missing_schemas)}")

    tables = list(expected["tables"])
    if tables:
        cursor.execute(
            """
            SELECT relation.relname
            FROM pg_class AS relation
            JOIN pg_namespace AS namespace
              ON namespace.oid = relation.relnamespace
            WHERE namespace.nspname = 'oltp_sgfood'
              AND relation.relname = ANY(%s)
              AND relation.relkind IN ('r', 'p')
            """,
            (tables,),
        )
        found_tables = {row[0] for row in cursor.fetchall()}
        missing_tables = sorted(set(tables) - found_tables)
        if missing_tables:
            raise RuntimeError(f"required tables are missing: {', '.join(missing_tables)}")

    role_names = list(role_passwords(target))
    cursor.execute(
        """
        SELECT member.rolname, parent.rolname
        FROM pg_auth_members AS membership
        JOIN pg_roles AS member ON member.oid = membership.member
        JOIN pg_roles AS parent ON parent.oid = membership.roleid
        WHERE member.rolname = ANY(%s)
           OR parent.rolname = ANY(%s)
        ORDER BY member.rolname, parent.rolname
        """,
        (role_names, role_names),
    )
    memberships = cursor.fetchall()
    if memberships:
        details = ", ".join(f"{member}->{parent}" for member, parent in memberships)
        raise RuntimeError(f"unexpected pre-existing role memberships: {details}")


def provision(target: str) -> None:
    driver, sql = import_driver()
    passwords = role_passwords(target)
    connection_parameters = connection_values(target)
    admin_user = required(EXPECTED[target]["admin"])
    connection = driver.connect(**connection_parameters)
    try:
        # This read-only preflight is completed before opening the write
        # transaction or executing either provisioning SQL file.
        connection.autocommit = True
        with connection.cursor() as cursor:
            validate_preconditions(cursor, target, admin_user)

        connection.autocommit = False
        sql_file = SQL_DIR / (
            "01-provision-roles-oltp.sql"
            if target == "oltp"
            else "02-provision-roles-dw.sql"
        )
        script = sql_file.read_text(encoding="utf-8")
        with connection.cursor() as cursor:
            cursor.execute(script)
            for role, password in passwords.items():
                verifier = scram_sha256_verifier(password)
                statement = sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(role), sql.Literal(verifier)
                )
                cursor.execute(statement)
        connection.commit()
    except Exception:
        if not connection.autocommit:
            connection.rollback()
        raise
    finally:
        connection.close()

    print(f"Provisioning completed for {target}: {', '.join(passwords)}")


class ScramVerifierTests(unittest.TestCase):
    def test_format_and_password_verification(self) -> None:
        password = "unit-test-only-password"
        verifier = scram_sha256_verifier(password, salt=b"0123456789abcdef")
        self.assertRegex(verifier, SCRAM_VERIFIER_RE)
        self.assertNotIn(password, verifier)
        self.assertTrue(verify_scram_sha256_verifier(verifier, password))
        self.assertFalse(verify_scram_sha256_verifier(verifier, "wrong-password"))

    def test_components_have_scram_lengths(self) -> None:
        verifier = scram_sha256_verifier("unit-test-only-password")
        match = SCRAM_VERIFIER_RE.fullmatch(verifier)
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(int(match.group("iterations")), SCRAM_ITERATIONS)
        self.assertEqual(len(base64.b64decode(match.group("salt"))), 16)
        self.assertEqual(len(base64.b64decode(match.group("stored"))), 32)
        self.assertEqual(len(base64.b64decode(match.group("server"))), 32)


def run_self_tests() -> bool:
    result = unittest.TextTestRunner(verbosity=1).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(ScramVerifierTests)
    )
    return result.wasSuccessful()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target",
        nargs="?",
        choices=("oltp", "dw"),
        help="database role set to provision; run once per database",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run local SCRAM format tests without connecting to PostgreSQL",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=ROOT / ".env",
        help="local dotenv file; defaults to Proyecto1/.env",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        return 0 if run_self_tests() else 1
    if args.target is None:
        print("a target is required unless --self-test is used", file=sys.stderr)
        return 2
    try:
        load_dotenv(args.env_file)
        provision(args.target)
    except Exception as exc:  # noqa: BLE001 - CLI must avoid secret leakage.
        print(f"Provisioning failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
