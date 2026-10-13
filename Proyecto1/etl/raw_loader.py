"""Extract the seven OLTP tables and five CSV sources into PostgreSQL raw.

The module intentionally does not connect on import.  The command line entry
point reads Proyecto1/.env, while tests can inject connection factories.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import logging
import os
import shlex
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

try:
    import psycopg
    from psycopg import sql
except ImportError:  # pragma: no cover - exercised only without dependencies
    psycopg = None  # type: ignore[assignment]
    sql = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
RAW_DDL = ROOT / "sql" / "03-create-raw.sql"
OLTP_TABLES = (
    "sucursal", "categoria", "marca", "producto", "cliente", "venta",
    "venta_detalle",
)

OLTP_COLUMNS: dict[str, tuple[str, ...]] = {
    "sucursal": ("id_sucursal", "nombre", "ciudad", "departamento"),
    "categoria": ("id_categoria", "nombre"),
    "marca": ("id_marca", "nombre"),
    "producto": ("id_producto", "sku", "nombre", "id_categoria", "id_marca",
                 "unidad_medida", "costo_base", "precio_lista", "activo"),
    "cliente": ("id_cliente", "nit", "nombre", "tipo_cliente", "municipio",
                 "departamento", "fecha_alta"),
    "venta": ("id_venta", "fecha", "id_cliente", "id_sucursal", "canal",
              "metodo_pago", "estado"),
    "venta_detalle": ("id_detalle", "id_venta", "id_producto", "cantidad",
                      "precio_unitario", "descuento", "subtotal"),
}

RAW_COLUMNS: dict[str, tuple[str, ...]] = {
    f"oltp_{name}": columns + ("_etl_load_id", "_etl_loaded_at", "_etl_source_table", "_etl_extracted_at")
    for name, columns in OLTP_COLUMNS.items()
}

RAW_CONTRACTS: dict[str, tuple[tuple[str, str, bool], ...]] = {
    "oltp_sucursal": (("id_sucursal", "integer", False), ("nombre", "character varying(100)", False), ("ciudad", "character varying(100)", False), ("departamento", "character varying(100)", False), ("_etl_load_id", "uuid", False), ("_etl_loaded_at", "timestamp with time zone", False), ("_etl_source_table", "text", False), ("_etl_extracted_at", "timestamp with time zone", False)),
    "oltp_categoria": (("id_categoria", "integer", False), ("nombre", "character varying(100)", False), ("_etl_load_id", "uuid", False), ("_etl_loaded_at", "timestamp with time zone", False), ("_etl_source_table", "text", False), ("_etl_extracted_at", "timestamp with time zone", False)),
    "oltp_marca": (("id_marca", "integer", False), ("nombre", "character varying(100)", False), ("_etl_load_id", "uuid", False), ("_etl_loaded_at", "timestamp with time zone", False), ("_etl_source_table", "text", False), ("_etl_extracted_at", "timestamp with time zone", False)),
    "oltp_producto": (("id_producto", "integer", False), ("sku", "character varying(20)", False), ("nombre", "character varying(150)", False), ("id_categoria", "integer", False), ("id_marca", "integer", False), ("unidad_medida", "character varying(30)", False), ("costo_base", "numeric(12,2)", False), ("precio_lista", "numeric(12,2)", False), ("activo", "boolean", False), ("_etl_load_id", "uuid", False), ("_etl_loaded_at", "timestamp with time zone", False), ("_etl_source_table", "text", False), ("_etl_extracted_at", "timestamp with time zone", False)),
    "oltp_cliente": (("id_cliente", "integer", False), ("nit", "character varying(20)", False), ("nombre", "character varying(150)", False), ("tipo_cliente", "character varying(40)", False), ("municipio", "character varying(100)", True), ("departamento", "character varying(100)", True), ("fecha_alta", "date", False), ("_etl_load_id", "uuid", False), ("_etl_loaded_at", "timestamp with time zone", False), ("_etl_source_table", "text", False), ("_etl_extracted_at", "timestamp with time zone", False)),
    "oltp_venta": (("id_venta", "bigint", False), ("fecha", "date", False), ("id_cliente", "integer", False), ("id_sucursal", "integer", False), ("canal", "character varying(30)", False), ("metodo_pago", "character varying(30)", False), ("estado", "character varying(20)", False), ("_etl_load_id", "uuid", False), ("_etl_loaded_at", "timestamp with time zone", False), ("_etl_source_table", "text", False), ("_etl_extracted_at", "timestamp with time zone", False)),
    "oltp_venta_detalle": (("id_detalle", "bigint", False), ("id_venta", "bigint", False), ("id_producto", "integer", False), ("cantidad", "integer", False), ("precio_unitario", "numeric(12,2)", False), ("descuento", "numeric(5,4)", False), ("subtotal", "numeric(14,2)", False), ("_etl_load_id", "uuid", False), ("_etl_loaded_at", "timestamp with time zone", False), ("_etl_source_table", "text", False), ("_etl_extracted_at", "timestamp with time zone", False)),
}


@dataclass(frozen=True)
class CsvSpec:
    filename: str
    table: str
    columns: tuple[str, ...]
    natural_key: tuple[str, ...]


CSV_SPECS = (
    CsvSpec("inventario_bodega.csv", "csv_inventario_bodega",
            ("fecha_corte", "id_sucursal", "id_producto", "stock_disponible", "stock_minimo", "stock_maximo", "lote", "fecha_vencimiento"),
            ("fecha_corte", "id_sucursal", "id_producto", "lote")),
    CsvSpec("devoluciones.csv", "csv_devoluciones",
            ("id_devolucion", "fecha", "id_venta", "id_producto", "cantidad", "motivo"),
            ("id_devolucion",)),
    CsvSpec("metas_ventas.csv", "csv_metas_ventas",
            ("periodo", "id_sucursal", "meta_ventas", "meta_unidades"),
            ("periodo", "id_sucursal")),
    CsvSpec("promociones.csv", "csv_promociones",
            ("id_promocion", "nombre", "fecha_inicio", "fecha_fin", "id_categoria", "porcentaje_descuento"),
            ("id_promocion",)),
    CsvSpec("proveedores_precios.csv", "csv_proveedores_precios",
            ("id_proveedor", "proveedor", "id_producto", "costo_proveedor", "plazo_dias", "fecha_vigencia"),
            ("id_proveedor", "id_producto", "fecha_vigencia")),
)

for _spec in CSV_SPECS:
    RAW_COLUMNS[_spec.table] = _spec.columns + (
        "_etl_load_id", "_etl_loaded_at", "_etl_source_name", "_etl_source_sha256", "_etl_row_number"
    )
    RAW_CONTRACTS[_spec.table] = tuple(
        (column, "text", False) for column in _spec.columns
    ) + (
        ("_etl_load_id", "uuid", False),
        ("_etl_loaded_at", "timestamp with time zone", False),
        ("_etl_source_name", "text", False),
        ("_etl_source_sha256", "character(64)", False),
        ("_etl_row_number", "bigint", False),
    )


@dataclass(frozen=True)
class CsvData:
    spec: CsvSpec
    source_name: str
    sha256: str
    rows: tuple[tuple[str, ...], ...]


class RawLoadError(RuntimeError):
    """Expected validation or load failure without sensitive details."""


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            value = value.strip()
            if value[:1] in {"'", '"'}:
                value = shlex.split(value, comments=False)[0]
            os.environ[key] = value


def read_csv_source(source_dir: Path, spec: CsvSpec) -> CsvData:
    path = source_dir / spec.filename
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RawLoadError(f"cannot read CSV source {spec.filename}") from exc
    digest = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        header = tuple(next(reader))
    except (UnicodeDecodeError, StopIteration, csv.Error) as exc:
        raise RawLoadError(f"invalid CSV source {spec.filename}") from exc
    if header != spec.columns:
        raise RawLoadError(f"invalid CSV header for {spec.filename}")
    rows: list[tuple[str, ...]] = []
    key_positions = tuple(spec.columns.index(column) for column in spec.natural_key)
    seen: set[tuple[str, ...]] = set()
    try:
        for row_number, row in enumerate(reader, start=2):
            if len(row) != len(spec.columns):
                raise RawLoadError(f"invalid CSV field count for {spec.filename} at row {row_number}")
            key = tuple(row[position] for position in key_positions)
            if key in seen:
                raise RawLoadError(f"duplicate natural key in {spec.filename} at row {row_number}")
            seen.add(key)
            rows.append(tuple(row))
    except csv.Error as exc:
        raise RawLoadError(f"invalid CSV source {spec.filename}") from exc
    return CsvData(spec, spec.filename, digest, tuple(rows))


def read_csv_sources(source_dir: Path) -> tuple[CsvData, ...]:
    return tuple(read_csv_source(source_dir, spec) for spec in CSV_SPECS)


def _identifier(schema: str, table: str) -> Any:
    if sql is None:  # pragma: no cover
        raise RawLoadError("psycopg is not installed")
    return sql.Identifier(schema, table)


def _fetch_oltp(connection: Any) -> tuple[dict[str, tuple[Any, ...]], datetime]:
    extracted_at = datetime.now(timezone.utc)
    values: dict[str, tuple[Any, ...]] = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            cursor.execute("SELECT current_database(), current_user")
            identity = cursor.fetchone()
            if identity != ("sgfood_oltp", "sgfood_oltp_reader"):
                raise RawLoadError("OLTP connection identity is invalid")
            for table in OLTP_TABLES:
                columns = sql.SQL(", ").join(sql.Identifier(column) for column in OLTP_COLUMNS[table])
                cursor.execute(sql.SQL("SELECT {columns} FROM {table}").format(
                    columns=columns, table=_identifier("oltp_sgfood", table)
                ))
                values[table] = tuple(cursor.fetchall())
        connection.commit()
    except Exception:
        connection.rollback()
        raise RawLoadError("OLTP extraction failed")
    return values, extracted_at


def _managed_tables() -> tuple[str, ...]:
    return tuple(f"oltp_{name}" for name in OLTP_TABLES) + tuple(spec.table for spec in CSV_SPECS)


def _insert_sql(table: str, columns: Sequence[str]) -> Any:
    if sql is None:  # pragma: no cover
        raise RawLoadError("psycopg is not installed")
    identifiers = sql.SQL(", ").join(sql.Identifier(column) for column in columns)
    placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in columns)
    return sql.SQL("INSERT INTO {table} ({columns}) VALUES ({values})").format(
        table=_identifier("raw", table), columns=identifiers, values=placeholders
    )


def _verify_raw_contract(cursor: Any) -> None:
    for table in _managed_tables():
        cursor.execute(
            """SELECT n.nspname, c.relname, c.relkind, pg_get_userbyid(c.relowner),
                      a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull,
                      a.attnum
               FROM pg_catalog.pg_class AS c
               JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
               JOIN pg_catalog.pg_attribute AS a ON a.attrelid = c.oid
               WHERE n.nspname = %s AND c.relname = %s
                 AND a.attnum > 0 AND NOT a.attisdropped
               ORDER BY a.attnum""",
            ("raw", table),
        )
        rows = cursor.fetchall()
        contract = RAW_CONTRACTS[table]
        if not rows or any(row[0:4] != ("raw", table, "r", "sgfood_raw_loader") for row in rows):
            raise RawLoadError("raw table structure or ownership is invalid")
        actual = tuple((row[4], row[5], not row[6]) for row in rows)
        if actual[:len(contract)] != contract:
            raise RawLoadError("raw table structure or ownership is invalid")
        if any(nullable is False for _, _, nullable in actual[len(contract):]):
            raise RawLoadError("raw table structure or ownership is invalid")


def _count_raw_tables(cursor: Any) -> dict[str, int]:
    result = {}
    for table in _managed_tables():
        cursor.execute(sql.SQL("SELECT COUNT(*) FROM {table}").format(table=_identifier("raw", table)))
        result[table] = int(cursor.fetchone()[0])
    return result


def load_raw(
    oltp_connection: Any,
    dw_connection: Any,
    source_dir: Path,
    ddl_path: Path = RAW_DDL,
    expected_counts: dict[str, int] | None = None,
    logger: logging.Logger | None = None,
) -> dict[str, int]:
    """Perform one atomic raw load and return actual counts by source.

    Extraction commits only the read-only OLTP transaction.  All DW DDL,
    truncation and inserts share one write transaction; any error rolls it back.
    """
    logger = logger or logging.getLogger(__name__)
    csv_data = read_csv_sources(source_dir)
    oltp_rows, extracted_at = _fetch_oltp(oltp_connection)
    load_id = uuid.uuid4()
    loaded_at = datetime.now(timezone.utc)
    counts: dict[str, int] = {name: len(rows) for name, rows in oltp_rows.items()}
    counts.update({data.spec.filename: len(data.rows) for data in csv_data})
    if expected_counts:
        for source, expected in expected_counts.items():
            if source in counts and counts[source] != expected:
                logger.warning("source count differs for %s: actual=%d expected=%d", source, counts[source], expected)
    try:
        with dw_connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user")
            if cursor.fetchone() != ("sgfood_dw", "sgfood_raw_loader"):
                raise RawLoadError("DW connection identity is invalid")
            cursor.execute(ddl_path.read_text(encoding="utf-8"))
            _verify_raw_contract(cursor)
            truncate = sql.SQL(", ").join(_identifier("raw", table) for table in _managed_tables())
            cursor.execute(sql.SQL("TRUNCATE TABLE {tables}").format(tables=truncate))
            for source_table, rows in oltp_rows.items():
                table = f"oltp_{source_table}"
                columns = RAW_COLUMNS[table]
                cursor.executemany(_insert_sql(table, columns), [
                    tuple(row) + (load_id, loaded_at, source_table, extracted_at) for row in rows
                ])
            for data in csv_data:
                table = data.spec.table
                columns = data.spec.columns + ("_etl_load_id", "_etl_loaded_at", "_etl_source_name", "_etl_source_sha256", "_etl_row_number")
                cursor.executemany(_insert_sql(table, columns), [
                    tuple(row) + (load_id, loaded_at, data.source_name, data.sha256, row_number)
                    for row_number, row in enumerate(data.rows, start=2)
                ])
            actual_counts = _count_raw_tables(cursor)
            expected_destinations = {f"oltp_{source}": count for source, count in counts.items() if source in OLTP_TABLES}
            expected_destinations.update({data.spec.table: len(data.rows) for data in csv_data})
            if actual_counts != expected_destinations:
                raise RawLoadError("raw reconciliation failed")
        dw_connection.commit()
    except Exception as exc:
        dw_connection.rollback()
        raise RawLoadError("raw load failed; transaction rolled back") from exc
    for source, count in counts.items():
        logger.info("raw source count: load_id=%s source=%s rows=%d", load_id, source, count)
    return counts


def _connection_parameters(prefix: str, role: str, password_variable: str) -> dict[str, str]:
    required = (f"{prefix}_DB", f"{prefix}_HOST_PORT", password_variable)
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RawLoadError("missing local database configuration")
    return {
        "host": os.environ.get(f"{prefix}_HOST", "127.0.0.1"),
        "port": os.environ[f"{prefix}_HOST_PORT"],
        "dbname": os.environ[f"{prefix}_DB"],
        "user": role,
        "password": os.environ[password_variable],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, connect: Callable[..., Any] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        load_dotenv(args.env_file)
        if psycopg is None and connect is None:
            raise RawLoadError("psycopg is not installed")
        connect = connect or psycopg.connect  # type: ignore[union-attr]
        oltp = connect(**_connection_parameters(
            "POSTGRES_OLTP", "sgfood_oltp_reader", "SGFOOD_OLTP_READER_PASSWORD"
        ))
        dw = None
        try:
            dw = connect(**_connection_parameters(
                "POSTGRES_DW", "sgfood_raw_loader", "SGFOOD_RAW_LOADER_PASSWORD"
            ))
            load_raw(oltp, dw, args.source_dir)
        finally:
            oltp.close()
            if dw is not None:
                dw.close()
    except Exception as exc:  # noqa: BLE001 - CLI deliberately avoids details.
        print(f"raw load failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
