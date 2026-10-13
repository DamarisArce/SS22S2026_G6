#!/usr/bin/env python3
"""Comprueba ACL del lector OLTP de SG-Food sin cambios persistentes.

Ejecutar desde la raíz del repositorio con Psycopg 3 instalado.
No imprime ni almacena contraseñas.
"""
from pathlib import Path
import runpy
import secrets

import psycopg
from psycopg import sql


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(f"ERROR: {message}")


module = runpy.run_path(
    "Proyecto1/scripts/provision_roles.py", run_name="sgfood_oltp_acl_test"
)
module["load_dotenv"](Path("Proyecto1/.env"))
parameters = module["connection_values"]("oltp")
require(
    (parameters["dbname"], parameters["host"], int(parameters["port"]))
    == ("sgfood_oltp", "127.0.0.1", 15433),
    "el destino OLTP no coincide con el laboratorio esperado",
)
parameters.update(
    user="sgfood_oltp_reader",
    password=module["required"]("SGFOOD_OLTP_READER_PASSWORD"),
    connect_timeout=5,
)
expected = {
    "sucursal": 6,
    "categoria": 8,
    "marca": 10,
    "producto": 80,
    "cliente": 250,
    "venta": 1200,
    "venta_detalle": 3209,
}

with psycopg.connect(**parameters) as connection:
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_user")
        require(
            cursor.fetchone() == ("sgfood_oltp", "sgfood_oltp_reader"),
            "identidad autenticada incorrecta",
        )
        print("OK: autenticación del lector OLTP")

        cursor.execute(
            """SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
                      rolreplication, rolbypassrls, rolinherit
               FROM pg_roles WHERE rolname = current_user"""
        )
        require(
            cursor.fetchone() == (True, False, False, False, False, False, False),
            "atributos administrativos inesperados",
        )
        print("OK: atributos del rol restringidos")

        cursor.execute(
            """SELECT has_schema_privilege(current_user, 'oltp_sgfood', 'USAGE'),
                      has_schema_privilege(current_user, 'oltp_sgfood', 'CREATE')"""
        )
        require(cursor.fetchone() == (True, False), "permisos del esquema OLTP")
        print("OK: USAGE autorizado; CREATE denegado en oltp_sgfood")

        total = 0
        for table, count in expected.items():
            qualified = f"oltp_sgfood.{table}"
            for privilege in (
                "SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE",
                "REFERENCES", "TRIGGER",
            ):
                cursor.execute(
                    "SELECT has_table_privilege(current_user, %s, %s)",
                    (qualified, privilege),
                )
                require(
                    cursor.fetchone()[0] is (privilege == "SELECT"),
                    f"privilegio {privilege} inesperado en {qualified}",
                )
            cursor.execute(
                sql.SQL("SELECT COUNT(*) FROM {}").format(
                    sql.Identifier("oltp_sgfood", table)
                )
            )
            found = cursor.fetchone()[0]
            require(found == count, f"conteo incorrecto en {qualified}: {found}")
            total += found
            print(f"OK: {table}={found}, únicamente SELECT")
        require(total == 4763, "total OLTP incorrecto")
        print("OK: total OLTP = 4763")

    connection.rollback()

    probe = "__sgfood_acl_reader_" + secrets.token_hex(6)
    rejected_statements = {
        "INSERT": """INSERT INTO oltp_sgfood.categoria (id_categoria, nombre)
                      SELECT -1, '__probe__' WHERE FALSE""",
        "UPDATE": """UPDATE oltp_sgfood.categoria SET nombre = nombre
                      WHERE FALSE""",
        "DELETE": "DELETE FROM oltp_sgfood.categoria WHERE FALSE",
        "CREATE": sql.SQL("CREATE TABLE {} (probe_id integer)").format(
            sql.Identifier("oltp_sgfood", probe)
        ),
    }
    for action, statement in rejected_statements.items():
        rejected = False
        try:
            with connection.cursor() as cursor:
                cursor.execute(statement)
        except psycopg.errors.InsufficientPrivilege:
            rejected = True
        finally:
            connection.rollback()
        require(rejected, f"{action} inesperadamente permitido")
        print(f"OK: {action} rechazado efectivamente")

print("VALIDACIÓN FUNCIONAL DE PERMISOS OLTP APROBADA")
