"""
Conexión de la aplicación ETL con Microsoft SQL Server mediante pyodbc.
"""

from contextlib import contextmanager
from typing import Iterator

import pyodbc

from src.config import settings


def build_connection_string() -> str:
    """
    Construye la cadena ODBC.

    En el entorno local se mantiene cifrado y se confía explícitamente
    en el certificado presentado por el SQL Server del contenedor.
    """

    return (
        f"DRIVER={{{settings.db_driver}}};"
        f"SERVER={settings.db_host},{settings.db_port};"
        f"DATABASE={settings.db_name};"
        f"UID={settings.db_user};"
        f"PWD={settings.db_password};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=10;"
    )


@contextmanager
def get_connection() -> Iterator[pyodbc.Connection]:
    """
    Entrega una conexión transaccional.

    Si el bloque termina correctamente se confirma la transacción.
    Ante cualquier excepción se realiza rollback.
    """

    connection = pyodbc.connect(
        build_connection_string(),
        autocommit=False,
    )

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def test_connection() -> None:
    """Comprueba la conexión y que la base esperada esté disponible."""

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                DB_NAME() AS database_name,
                @@SERVERNAME AS server_name,
                CONVERT(
                    VARCHAR(100),
                    SERVERPROPERTY('ProductVersion')
                ) AS product_version,
                CONVERT(
                    VARCHAR(200),
                    SERVERPROPERTY('Edition')
                ) AS edition;
            """
        )

        database_name, server_name, version, edition = cursor.fetchone()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM sys.tables AS t
            INNER JOIN sys.schemas AS s
                ON s.schema_id = t.schema_id
            WHERE s.name IN ('audit', 'stg', 'dw');
            """
        )

        table_count = cursor.fetchone()[0]

        print("===== CONEXION A SQL SERVER =====")
        print(f"Base: {database_name}")
        print(f"Servidor: {server_name}")
        print(f"Version: {version}")
        print(f"Edicion: {edition}")
        print(f"Tablas del proyecto: {table_count}")

        if database_name != settings.db_name:
            raise RuntimeError(
                "La conexión abrió una base distinta de la configurada."
            )

        if table_count != 14:
            raise RuntimeError(
                "El modelo esperado debe contener 14 tablas."
            )

        print("Estado: OK")


if __name__ == "__main__":
    test_connection()
