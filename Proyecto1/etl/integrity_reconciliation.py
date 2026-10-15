"""Read-only reconciliation between SG-Food sources, raw and dbt outputs.

The checks deliberately use the repository's business columns and obtain all
expected values from the databases at run time.  This module has no import-time
connection and is usable with small fake connection/cursor objects in tests.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

try:
    import psycopg
except ImportError:  # pragma: no cover - supplied by the Airflow image
    psycopg = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[1]


class ReconciliationError(RuntimeError):
    """A source, raw, or modeled relation does not reconcile."""


@dataclass(frozen=True)
class MetricMismatch:
    name: str
    expected: Any
    actual: Any


OLTP_CONTRACTS: Mapping[str, tuple[str, ...]] = {
    "sucursal": ("id_sucursal", "nombre", "ciudad", "departamento"),
    "categoria": ("id_categoria", "nombre"),
    "marca": ("id_marca", "nombre"),
    "producto": ("id_producto", "sku", "nombre", "id_categoria", "id_marca", "unidad_medida", "costo_base", "precio_lista", "activo"),
    "cliente": ("id_cliente", "nit", "nombre", "tipo_cliente", "municipio", "departamento", "fecha_alta"),
    "venta": ("id_venta", "fecha", "id_cliente", "id_sucursal", "canal", "metodo_pago", "estado"),
    "venta_detalle": ("id_detalle", "id_venta", "id_producto", "cantidad", "precio_unitario", "descuento", "subtotal"),
}

NATURAL_KEYS: Mapping[str, tuple[str, ...]] = {
    "oltp_sucursal": ("id_sucursal",), "oltp_categoria": ("id_categoria",),
    "oltp_marca": ("id_marca",), "oltp_producto": ("id_producto",),
    "oltp_cliente": ("id_cliente",), "oltp_venta": ("id_venta",),
    "oltp_venta_detalle": ("id_detalle",),
    "csv_inventario_bodega": ("fecha_corte", "id_sucursal", "id_producto", "lote"),
    "csv_devoluciones": ("id_devolucion",),
    "csv_metas_ventas": ("periodo", "id_sucursal"),
    "csv_promociones": ("id_promocion",),
    "csv_proveedores_precios": ("id_proveedor", "id_producto", "fecha_vigencia"),
}

CSV_TABLES = tuple(name for name in NATURAL_KEYS if name.startswith("csv_"))


def compare_metrics(metrics: Iterable[MetricMismatch]) -> None:
    mismatches = tuple(metrics)
    if mismatches:
        raise ReconciliationError("reconciliation mismatch: " + "; ".join(
            f"{item.name} expected={item.expected!r} actual={item.actual!r}"
            for item in mismatches
        ))


def _one(cursor: Any, query: str, params: tuple[Any, ...] = ()) -> Any:
    cursor.execute(query, params)
    row = cursor.fetchone()
    if row is None:
        raise ReconciliationError("reconciliation query returned no result")
    return row[0] if len(row) == 1 else row


def _count(cursor: Any, relation: str) -> int:
    return int(_one(cursor, f"SELECT COUNT(*) FROM {relation}"))


def _check_oltp_vs_raw(oltp: Any, dw: Any) -> list[MetricMismatch]:
    mismatches: list[MetricMismatch] = []
    for table, columns in OLTP_CONTRACTS.items():
        columns_sql = ", ".join(columns)
        source = _all(oltp, f"SELECT {columns_sql} FROM oltp_sgfood.{table} ORDER BY {columns_sql}")
        raw = _all(dw, f"SELECT {columns_sql} FROM raw.oltp_{table} ORDER BY {columns_sql}")
        mismatch = _compare_rows(f"content oltp.{table} vs raw.oltp_{table}", source, raw)
        if mismatch:
            mismatches.append(mismatch)
    return mismatches


def _check_csv_and_keys(dw: Any) -> list[MetricMismatch]:
    mismatches: list[MetricMismatch] = []
    for table, keys in NATURAL_KEYS.items():
        key_sql = ", ".join(keys)
        duplicate_groups = int(_one(dw, f"SELECT COUNT(*) FROM (SELECT {key_sql} FROM raw.{table} GROUP BY {key_sql} HAVING COUNT(*) > 1) AS duplicates"))
        if duplicate_groups:
            mismatches.append(MetricMismatch(f"duplicate natural keys raw.{table}", 0, duplicate_groups))
        if table in CSV_TABLES:
            count, hashes = _one(dw, f"SELECT COUNT(*), COUNT(DISTINCT _etl_source_sha256) FROM raw.{table}")
            if int(count) and int(hashes) != 1:
                mismatches.append(MetricMismatch(f"CSV source hash raw.{table}", 1, hashes))
    return mismatches


def _check_relationships(dw: Any) -> list[MetricMismatch]:
    relationships = (
        ("raw.oltp_producto", "id_categoria", "raw.oltp_categoria", "id_categoria"),
        ("raw.oltp_producto", "id_marca", "raw.oltp_marca", "id_marca"),
        ("raw.oltp_venta", "id_cliente", "raw.oltp_cliente", "id_cliente"),
        ("raw.oltp_venta", "id_sucursal", "raw.oltp_sucursal", "id_sucursal"),
        ("raw.oltp_venta_detalle", "id_venta", "raw.oltp_venta", "id_venta"),
        ("raw.oltp_venta_detalle", "id_producto", "raw.oltp_producto", "id_producto"),
    )
    mismatches: list[MetricMismatch] = []
    for child, child_key, parent, parent_key in relationships:
        orphaned = int(_one(dw, f"SELECT COUNT(*) FROM {child} AS child LEFT JOIN {parent} AS parent ON child.{child_key} = parent.{parent_key} WHERE parent.{parent_key} IS NULL"))
        if orphaned:
            mismatches.append(MetricMismatch(f"referential integrity {child}.{child_key}", 0, orphaned))
    return mismatches


def _connect_parameters(prefix: str, user: str, password_variable: str) -> dict[str, str]:
    required = (f"{prefix}_DB", f"{prefix}_HOST", f"{prefix}_HOST_PORT", password_variable)
    if any(not os.environ.get(name) for name in required):
        raise ReconciliationError("missing database configuration")
    return {"host": os.environ[f"{prefix}_HOST"], "port": os.environ[f"{prefix}_HOST_PORT"], "dbname": os.environ[f"{prefix}_DB"], "user": user, "password": os.environ[password_variable]}


CSV_COLUMNS: Mapping[str, tuple[str, ...]] = {
    "csv_inventario_bodega": ("fecha_corte", "id_sucursal", "id_producto", "stock_disponible", "stock_minimo", "stock_maximo", "lote", "fecha_vencimiento"),
    "csv_devoluciones": ("id_devolucion", "fecha", "id_venta", "id_producto", "cantidad", "motivo"),
    "csv_metas_ventas": ("periodo", "id_sucursal", "meta_ventas", "meta_unidades"),
    "csv_promociones": ("id_promocion", "nombre", "fecha_inicio", "fecha_fin", "id_categoria", "porcentaje_descuento"),
    "csv_proveedores_precios": ("id_proveedor", "proveedor", "id_producto", "costo_proveedor", "plazo_dias", "fecha_vigencia"),
}
CSV_FILES = {
    "csv_inventario_bodega": "inventario_bodega.csv",
    "csv_devoluciones": "devoluciones.csv",
    "csv_metas_ventas": "metas_ventas.csv",
    "csv_promociones": "promociones.csv",
    "csv_proveedores_precios": "proveedores_precios.csv",
}
CSV_DATE_FIELDS = {"fecha_corte", "fecha_vencimiento", "fecha", "fecha_inicio", "fecha_fin", "fecha_vigencia"}
CSV_INTEGER_FIELDS = {"id_sucursal", "id_producto", "id_devolucion", "id_venta", "id_categoria", "id_proveedor", "plazo_dias"}
CSV_NUMERIC_FIELDS = {"stock_disponible", "stock_minimo", "stock_maximo", "cantidad", "meta_ventas", "meta_unidades", "porcentaje_descuento", "costo_proveedor", "precio_unitario", "descuento", "subtotal"}


def _normalized(value: Any, field: str) -> Any:
    if value is None:
        return None
    value = value.strip() if isinstance(value, str) else value
    if value == "":
        return None
    try:
        if field in CSV_DATE_FIELDS:
            return date.fromisoformat(str(value))
        if field in CSV_INTEGER_FIELDS:
            return int(value)
        if field in CSV_NUMERIC_FIELDS:
            return Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation) as exc:
        raise ReconciliationError(f"invalid normalized value for {field}") from exc
    return value


def _normalized_rows(rows: Iterable[tuple[Any, ...]], columns: tuple[str, ...]) -> list[tuple[Any, ...]]:
    return [tuple(_normalized(value, field) for value, field in zip(row, columns)) for row in rows]


def _all(cursor: Any, query: str) -> list[tuple[Any, ...]]:
    cursor.execute(query)
    return list(cursor.fetchall())


def _compare_rows(name: str, expected: Iterable[tuple[Any, ...]], actual: Iterable[tuple[Any, ...]]) -> MetricMismatch | None:
    expected_counter = Counter(expected)
    actual_counter = Counter(actual)
    if expected_counter != actual_counter:
        return MetricMismatch(name, dict(expected_counter), dict(actual_counter))
    return None


def _csv_reconciliations(dw: Any, source_dir: Path) -> list[MetricMismatch]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from etl.raw_loader import CSV_SPECS

    mismatches: list[MetricMismatch] = []
    for spec in CSV_SPECS:
        table = spec.table
        path = source_dir / spec.filename
        if not path.is_file():
            mismatches.append(MetricMismatch(f"CSV file {spec.filename}", "present", "missing"))
            continue
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        try:
            reader = csv.reader(io.StringIO(content.decode("utf-8-sig"), newline=""), strict=True)
            header = tuple(next(reader))
            source_rows = [tuple(row) for row in reader]
        except (UnicodeDecodeError, StopIteration, csv.Error) as exc:
            raise ReconciliationError(f"invalid CSV source {spec.filename}") from exc
        if header != spec.columns:
            mismatches.append(MetricMismatch(f"CSV header {spec.filename}", spec.columns, header))
        source_normalized = _normalized_rows(source_rows, spec.columns)
        columns_sql = ", ".join(spec.columns + ("_etl_source_name", "_etl_source_sha256", "_etl_row_number"))
        raw_rows = _all(dw, f"SELECT {columns_sql} FROM raw.{table} ORDER BY _etl_row_number")
        raw_business = _normalized_rows((row[:len(spec.columns)] for row in raw_rows), spec.columns)
        mismatch = _compare_rows(f"CSV content {spec.filename}", source_normalized, raw_business)
        if mismatch:
            mismatches.append(mismatch)
        expected_metadata = [(spec.filename, digest, number) for number in range(2, len(source_rows) + 2)]
        actual_metadata = [(row[-3], row[-2], int(row[-1])) for row in raw_rows]
        mismatch = _compare_rows(f"CSV metadata {table}", expected_metadata, actual_metadata)
        if mismatch:
            mismatches.append(mismatch)
        if len(raw_rows) != len(source_rows):
            mismatches.append(MetricMismatch(f"CSV count {table}", len(source_rows), len(raw_rows)))
    return mismatches


def _fact_reconciliation(dw: Any) -> list[MetricMismatch]:
    detail_columns = OLTP_CONTRACTS["venta_detalle"]
    columns_sql = ", ".join(detail_columns)
    raw = _normalized_rows(_all(dw, f"SELECT {columns_sql} FROM raw.oltp_venta_detalle ORDER BY {columns_sql}"), detail_columns)
    fact = _normalized_rows(_all(dw, f"SELECT {columns_sql} FROM marts.fct_ventas_detalle ORDER BY {columns_sql}"), detail_columns)
    mismatches: list[MetricMismatch] = []
    ids = [row[0] for row in fact]
    if len(ids) != len(set(ids)):
        mismatches.append(MetricMismatch("fact id_detalle uniqueness", "unique", ids))
    if len(raw) != len(fact):
        mismatches.append(MetricMismatch("fact row count", len(raw), len(fact)))
    for index, label in ((3, "fact quantity sum"), (6, "fact subtotal sum")):
        expected = sum((row[index] for row in raw), Decimal("0"))
        actual = sum((row[index] for row in fact), Decimal("0"))
        if expected != actual:
            mismatches.append(MetricMismatch(label, expected, actual))
    mismatch = _compare_rows("fact detail multiset", raw, fact)
    if mismatch:
        mismatches.append(mismatch)
    return mismatches


def _check_fact_coverage(dw: Any) -> list[MetricMismatch]:
    """Separate dimension uniqueness, FK existence and join cardinality."""
    mismatches: list[MetricMismatch] = []
    fact_count = _count(dw, "marts.fct_ventas_detalle")
    for dimension, key in (("dim_producto", "id_producto"), ("dim_cliente", "id_cliente"), ("dim_sucursal", "id_sucursal")):
        duplicate = int(_one(dw, f"SELECT COUNT(*) FROM (SELECT {key} FROM marts.{dimension} GROUP BY {key} HAVING COUNT(*) > 1) AS duplicate_dimension_keys"))
        if duplicate:
            mismatches.append(MetricMismatch(f"dimension key uniqueness marts.{dimension}", 0, duplicate))
        missing = int(_one(dw, f"SELECT COUNT(*) FROM marts.fct_ventas_detalle AS fact LEFT JOIN marts.{dimension} AS dimension ON fact.{key} = dimension.{key} WHERE fact.{key} IS NULL OR dimension.{key} IS NULL"))
        if missing:
            mismatches.append(MetricMismatch(f"dimension FK existence {dimension}.{key}", 0, missing))
        joined = int(_one(dw, f"SELECT COUNT(*) FROM marts.fct_ventas_detalle AS fact JOIN marts.{dimension} AS dimension ON fact.{key} = dimension.{key}"))
        if joined != fact_count:
            mismatches.append(MetricMismatch(f"dimension join cardinality {dimension}", fact_count, joined))
    return mismatches


def _check_fact_enrichment(dw: Any) -> list[MetricMismatch]:
    """Ensure each fact row matches exactly one raw sale header."""
    mismatches: list[MetricMismatch] = []
    missing = int(_one(dw, "SELECT COUNT(*) FROM marts.fct_ventas_detalle AS fact LEFT JOIN raw.oltp_venta AS venta ON fact.id_venta = venta.id_venta WHERE venta.id_venta IS NULL"))
    if missing:
        mismatches.append(MetricMismatch("fact enrichment missing sale header", 0, missing))
    fanout = int(_one(dw, "SELECT COUNT(*) FROM (SELECT fact.id_detalle FROM marts.fct_ventas_detalle AS fact JOIN raw.oltp_venta AS venta ON fact.id_venta = venta.id_venta GROUP BY fact.id_detalle HAVING COUNT(*) > 1) AS sale_header_fanout"))
    if fanout:
        mismatches.append(MetricMismatch("fact enrichment sale-header fanout", 0, fanout))
    for column, label in (("id_cliente", "cliente"), ("id_sucursal", "sucursal"), ("fecha", "fecha")):
        different = int(_one(dw, f"SELECT COUNT(*) FROM marts.fct_ventas_detalle AS fact JOIN raw.oltp_venta AS venta ON fact.id_venta = venta.id_venta WHERE fact.{column} IS DISTINCT FROM venta.{column}"))
        if different:
            mismatches.append(MetricMismatch(f"fact enrichment {label}", 0, different))
    return mismatches


def _inventory_and_returns(dw: Any) -> list[MetricMismatch]:
    pairs = (
        ("csv_inventario_bodega", "intermediate.int_inventario_snapshot"),
        ("csv_devoluciones", "intermediate.int_devoluciones_enriquecida"),
    )
    mismatches: list[MetricMismatch] = []
    for table, modeled in pairs:
        columns = CSV_COLUMNS[table]
        columns_sql = ", ".join(columns)
        raw = _normalized_rows(_all(dw, f"SELECT {columns_sql} FROM raw.{table} ORDER BY {columns_sql}"), columns)
        modeled = _normalized_rows(_all(dw, f"SELECT {columns_sql} FROM {modeled} ORDER BY {columns_sql}"), columns)
        mismatch = _compare_rows(f"normalized preservation {table}", raw, modeled)
        if mismatch:
            mismatches.append(mismatch)
    return mismatches


def _cleanup_connections(connections: Iterable[Any]) -> list[Exception]:
    """Rollback and close every still-open connection, collecting failures."""
    cleanup_errors: list[Exception] = []
    connections = tuple(connection for connection in connections if connection is not None)
    for connection in connections:
        if not getattr(connection, "closed", False):
            try:
                connection.rollback()
            except Exception as exc:  # noqa: BLE001 - cleanup must continue.
                cleanup_errors.append(exc)
    for connection in connections:
        if not getattr(connection, "closed", False):
            try:
                connection.close()
            except Exception as exc:  # noqa: BLE001 - cleanup must continue.
                cleanup_errors.append(exc)
    return cleanup_errors


def reconcile(oltp_connection: Any, dw_connection: Any, source_dir: Path | str = "/opt/airflow/data") -> None:
    """Reconcile every source, raw, dimensional and modeled control.

    The connections are owned by this operation: their read-only transactions
    are rolled back and the connections are closed on both success and error.
    """
    source_dir = Path(source_dir)
    try:
        with oltp_connection.cursor() as oltp, dw_connection.cursor() as dw:
            oltp.execute("SET TRANSACTION READ ONLY")
            dw.execute("SET TRANSACTION READ ONLY")
            mismatches = _check_oltp_vs_raw(oltp, dw)
            mismatches.extend(_check_csv_and_keys(dw))
            mismatches.extend(_check_relationships(dw))
            mismatches.extend(_csv_reconciliations(dw, source_dir))
            mismatches.extend(_fact_reconciliation(dw))
            mismatches.extend(_check_fact_coverage(dw))
            mismatches.extend(_check_fact_enrichment(dw))
            mismatches.extend(_inventory_and_returns(dw))
            compare_metrics(mismatches)
    except Exception:
        _cleanup_connections((oltp_connection, dw_connection))
        raise
    else:
        cleanup_errors = _cleanup_connections((oltp_connection, dw_connection))
        if cleanup_errors:
            raise cleanup_errors[0]


def _precheck() -> None:
    if psycopg is None:
        raise ReconciliationError("database driver is unavailable")
    checks = (
        ("POSTGRES_OLTP", "sgfood_oltp", "sgfood_oltp_reader", "SGFOOD_OLTP_READER_PASSWORD"),
        ("POSTGRES_DW", "sgfood_dw", "sgfood_raw_loader", "SGFOOD_RAW_LOADER_PASSWORD"),
        ("POSTGRES_DW", "sgfood_dw", "sgfood_dbt_runner", "SGFOOD_DBT_RUNNER_PASSWORD"),
    )
    connections: list[Any] = []
    try:
        for prefix, expected_db, expected_user, password in checks:
            connection = psycopg.connect(**_connect_parameters(prefix, expected_user, password))
            connections.append(connection)
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database(), current_user")
                if cursor.fetchone() != (expected_db, expected_user):
                    raise ReconciliationError("database identity is invalid")
                cursor.execute("SELECT 1")
                if cursor.fetchone() != (1,):
                    raise ReconciliationError("database availability check failed")
    finally:
        cleanup_errors = _cleanup_connections(connections)
        if cleanup_errors and sys.exc_info()[0] is None:
            raise cleanup_errors[0]


def main(argv: Iterable[str] | None = None, connect: Callable[..., Any] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--precheck", action="store_true")
    parser.add_argument("--source-dir", type=Path, default=Path("/opt/airflow/data"))
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if args.precheck:
            _precheck()
            return 0
        if psycopg is None and connect is None:
            raise ReconciliationError("database driver is unavailable")
        connector = connect or psycopg.connect  # type: ignore[union-attr]
        oltp = dw = None
        reconcile_started = False
        try:
            oltp = connector(**_connect_parameters("POSTGRES_OLTP", "sgfood_oltp_reader", "SGFOOD_OLTP_READER_PASSWORD"))
            dw = connector(**_connect_parameters("POSTGRES_DW", "sgfood_dbt_runner", "SGFOOD_DBT_RUNNER_PASSWORD"))
            reconcile_started = True
            reconcile(oltp, dw, args.source_dir)
        finally:
            if not reconcile_started:
                cleanup_errors = _cleanup_connections((oltp, dw))
                if cleanup_errors:
                    raise cleanup_errors[0]
    except Exception as exc:  # noqa: BLE001 - CLI omits sensitive details.
        print(f"integrity reconciliation failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
