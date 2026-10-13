from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from etl import raw_loader


ROOT = Path(__file__).resolve().parents[1]


class FakeQuery:
    def __init__(self, text: str) -> None:
        self.text = text

    def __str__(self) -> str:
        return self.text

    def join(self, values) -> "FakeQuery":
        return FakeQuery(self.text.join(str(value) for value in values))

    def format(self, **values) -> "FakeQuery":
        result = self.text
        for key, value in values.items():
            result = result.replace("{" + key + "}", str(value))
        return FakeQuery(result)


class FakeSQL:
    SQL = staticmethod(FakeQuery)
    Identifier = staticmethod(lambda *parts: FakeQuery(".".join('"' + part + '"' for part in parts)))
    Placeholder = staticmethod(lambda: FakeQuery("%s"))


class FakeCursor:
    def __init__(self, connection: "FakeConnection") -> None:
        self.connection = connection
        self.statements: list[tuple[str, object]] = []
        self.one: list[tuple] = []
        self.many: list[tuple] = []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, statement, params=None) -> None:
        text = str(statement)
        self.statements.append((text, params))
        self.connection.statements.append((text, params))
        if self.connection.fail_on_execute:
            raise RuntimeError("controlled failure")
        if text.startswith("SELECT current_database"):
            self.one.append(self.connection.identity)
        elif "pg_catalog.pg_class" in text:
            self.many.append(self.connection.catalog(params[1]))
        elif text.startswith("SELECT COUNT(*)"):
            table = next(name for name in raw_loader._managed_tables() if f'"{name}"' in text)
            self.one.append((self.connection.counts.get(table, 0),))
        elif text.startswith("SELECT ") and " FROM " in text:
            table = next(name for name in raw_loader.OLTP_TABLES if f'"{name}"' in text)
            self.many.append(self.connection.oltp_rows.get(table, ()))

    def executemany(self, statement, params_seq) -> None:
        values = list(params_seq)
        self.connection.executemany_calls.append((str(statement), values))
        self.statements.append((str(statement), values))
        self.connection.statements.append((str(statement), values))

    def fetchone(self):
        return self.one.pop(0)

    def fetchall(self):
        return self.many.pop(0)


class FakeConnection:
    def __init__(self, rows=None, fail_on_execute: bool = False, *, identity=("sgfood_dw", "sgfood_raw_loader"),
                 oltp_rows=None, catalog_override=None, counts=None) -> None:
        self.rows = rows or []
        self.fail_on_execute = fail_on_execute
        self.identity = identity
        self.oltp_rows = oltp_rows or {}
        self.catalog_override = catalog_override or {}
        self.counts = counts or {}
        self.statements: list[tuple] = []
        self.executemany_calls: list[tuple] = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def catalog(self, table):
        if table in self.catalog_override:
            return self.catalog_override[table]
        return [("raw", table, "r", "sgfood_raw_loader", name, type_name, not nullable, index)
                for index, (name, type_name, nullable) in enumerate(raw_loader.RAW_CONTRACTS[table], start=1)]

    def cursor(self):
        self._cursor = FakeCursor(self)
        return self._cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class RawLoaderTests(unittest.TestCase):
    def setUp(self):
        self.sql_patch = patch.object(raw_loader, "sql", FakeSQL)
        self.sql_patch.start()
        self.addCleanup(self.sql_patch.stop)

    def test_exact_mapping_of_twelve_sources(self):
        self.assertEqual(
            raw_loader._managed_tables(),
            (
                "oltp_sucursal", "oltp_categoria", "oltp_marca", "oltp_producto",
                "oltp_cliente", "oltp_venta", "oltp_venta_detalle",
                "csv_inventario_bodega", "csv_devoluciones", "csv_metas_ventas",
                "csv_promociones", "csv_proveedores_precios",
            ),
        )
        self.assertEqual(len(raw_loader.CSV_SPECS), 5)

    def test_csv_bom_crlf_and_empty_values(self):
        spec = raw_loader.CSV_SPECS[1]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / spec.filename
            path.write_bytes(("\ufeff" + ",".join(spec.columns) + "\r\n"
                              "1,2026-01-01,10,1001,2,\r\n").encode("utf-8"))
            result = raw_loader.read_csv_source(Path(directory), spec)
        self.assertEqual(result.rows, (("1", "2026-01-01", "10", "1001", "2", ""),))
        self.assertEqual(len(result.sha256), 64)

    def test_csv_multiline_field_is_preserved_exactly(self):
        spec = raw_loader.CSV_SPECS[1]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / spec.filename
            path.write_bytes(("\ufeff" + ",".join(spec.columns) + "\r\n"
                              "1,2026-01-01,10,1001,2,\"motivo\r\ncontinuado\"\r\n").encode("utf-8"))
            result = raw_loader.read_csv_source(Path(directory), spec)
        self.assertEqual(result.rows[0][-1], "motivo\r\ncontinuado")

    def test_malformed_csv_is_rejected(self):
        spec = raw_loader.CSV_SPECS[0]
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / spec.filename).write_text(
                ",".join(spec.columns) + "\n\"unterminated\n", encoding="utf-8")
            with self.assertRaises(raw_loader.RawLoadError):
                raw_loader.read_csv_source(Path(directory), spec)

    def test_invalid_header_is_rejected(self):
        spec = raw_loader.CSV_SPECS[0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / spec.filename
            path.write_text("wrong\n", encoding="utf-8")
            with self.assertRaises(raw_loader.RawLoadError):
                raw_loader.read_csv_source(Path(directory), spec)

    def test_duplicate_natural_key_is_rejected(self):
        spec = raw_loader.CSV_SPECS[2]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / spec.filename
            header = ",".join(spec.columns)
            path.write_text(f"{header}\n2026-01,1,10,20\n2026-01,1,11,21\n", encoding="utf-8")
            with self.assertRaises(raw_loader.RawLoadError):
                raw_loader.read_csv_source(Path(directory), spec)

    def test_counts_and_rerun_truncate_managed_tables(self):
        oltp = FakeConnection(identity=("sgfood_oltp", "sgfood_oltp_reader"),
                               oltp_rows={table: () for table in raw_loader.OLTP_TABLES})
        with tempfile.TemporaryDirectory() as directory:
            source_dir = Path(directory)
            for spec in raw_loader.CSV_SPECS:
                (source_dir / spec.filename).write_text(
                    ",".join(spec.columns) + "\n" + ",".join("x" for _ in spec.columns) + "\n",
                    encoding="utf-8",
                )
            # The synthetic rows are unique for this test only where the key has one row.
            counts = {table: 0 for table in raw_loader._managed_tables()}
            counts.update({spec.table: 1 for spec in raw_loader.CSV_SPECS})
            dw = FakeConnection(counts=counts)
            first = raw_loader.load_raw(oltp, dw, source_dir)
            second = raw_loader.load_raw(oltp, dw, source_dir)
        self.assertEqual(first, second)
        self.assertEqual(dw.commits, 2)
        truncates = [statement for statement, _ in dw.statements if statement.startswith("TRUNCATE TABLE")]
        self.assertEqual(len(truncates), 2)
        self.assertNotIn("DROP", " ".join(statement for statement, _ in dw.statements))

    def test_failure_rolls_back_and_does_not_expose_secret(self):
        oltp = FakeConnection(identity=("sgfood_oltp", "sgfood_oltp_reader"),
                               oltp_rows={table: () for table in raw_loader.OLTP_TABLES})
        dw = FakeConnection(fail_on_execute=True)
        with tempfile.TemporaryDirectory() as directory:
            source_dir = Path(directory)
            for spec in raw_loader.CSV_SPECS:
                (source_dir / spec.filename).write_text(
                    ",".join(spec.columns) + "\n" + ",".join("x" for _ in spec.columns) + "\n",
                    encoding="utf-8",
                )
            with self.assertRaises(raw_loader.RawLoadError) as error:
                raw_loader.load_raw(oltp, dw, source_dir)
        self.assertEqual(dw.rollbacks, 1)
        self.assertNotIn("super-secret", str(error.exception))

    def test_cli_error_only_reports_exception_type(self):
        output = io.StringIO()
        with patch.object(raw_loader, "_connection_parameters", side_effect=raw_loader.RawLoadError("super-secret")):
            with contextlib.redirect_stderr(output):
                result = raw_loader.main([], connect=lambda **kwargs: FakeConnection())
        self.assertEqual(result, 1)
        self.assertNotIn("super-secret", output.getvalue())
        self.assertIn("RawLoadError", output.getvalue())

    def test_expected_count_check_is_observational(self):
        data = raw_loader.read_csv_sources(ROOT / "data")
        self.assertEqual(
            {item.spec.filename: len(item.rows) for item in data},
            {
                "inventario_bodega.csv": 3840,
                "devoluciones.csv": 80,
                "metas_ventas.csv": 48,
                "promociones.csv": 30,
                "proveedores_precios.csv": 103,
            },
        )

    def test_explicit_columns_are_used_for_select_and_insert(self):
        oltp = FakeConnection(identity=("sgfood_oltp", "sgfood_oltp_reader"),
                              oltp_rows={table: () for table in raw_loader.OLTP_TABLES})
        raw_loader._fetch_oltp(oltp)
        selects = [statement for statement, _ in oltp._cursor.statements if statement.startswith("SELECT ")]
        self.assertTrue(selects)
        self.assertTrue(all("*" not in statement for statement in selects))
        insert = str(raw_loader._insert_sql("oltp_sucursal", raw_loader.RAW_COLUMNS["oltp_sucursal"]))
        self.assertIn('"id_sucursal"', insert)
        self.assertIn('"_etl_extracted_at"', insert)

    def test_schema_and_owner_validation_happens_before_truncate(self):
        oltp = FakeConnection(identity=("sgfood_oltp", "sgfood_oltp_reader"),
                              oltp_rows={table: () for table in raw_loader.OLTP_TABLES})
        with tempfile.TemporaryDirectory() as directory:
            source_dir = Path(directory)
            for spec in raw_loader.CSV_SPECS:
                (source_dir / spec.filename).write_text(
                    ",".join(spec.columns) + "\n" + ",".join("x" for _ in spec.columns) + "\n", encoding="utf-8")
            base = FakeConnection().catalog("oltp_sucursal")
            for mutation in (("text", None), (None, "other_role")):
                rows = [list(row) for row in base]
                if mutation[0]:
                    rows[0][5] = mutation[0]
                else:
                    rows[0][3] = mutation[1]
                dw = FakeConnection(catalog_override={"oltp_sucursal": [tuple(row) for row in rows]})
                with self.assertRaises(raw_loader.RawLoadError):
                    raw_loader.load_raw(oltp, dw, source_dir)
                self.assertFalse(any(statement.startswith("TRUNCATE") for statement, _ in dw._cursor.statements))

    def test_reconciliation_failure_rolls_back_before_commit(self):
        oltp = FakeConnection(identity=("sgfood_oltp", "sgfood_oltp_reader"),
                              oltp_rows={table: () for table in raw_loader.OLTP_TABLES})
        with tempfile.TemporaryDirectory() as directory:
            source_dir = Path(directory)
            for spec in raw_loader.CSV_SPECS:
                (source_dir / spec.filename).write_text(
                    ",".join(spec.columns) + "\n" + ",".join("x" for _ in spec.columns) + "\n", encoding="utf-8")
            dw = FakeConnection(counts={})
            with self.assertRaises(raw_loader.RawLoadError):
                raw_loader.load_raw(oltp, dw, source_dir)
        self.assertEqual(dw.commits, 0)
        self.assertEqual(dw.rollbacks, 1)

    def test_all_twelve_tables_are_managed_and_second_connection_failure_closes_first(self):
        self.assertEqual(len(raw_loader._managed_tables()), 12)
        first = FakeConnection()
        calls = [first]

        def connect(**kwargs):
            if calls:
                return calls.pop(0)
            raise RuntimeError("second connection unavailable")

        with patch.object(raw_loader, "_connection_parameters", return_value={}), contextlib.redirect_stderr(io.StringIO()):
            result = raw_loader.main([], connect=connect)
        self.assertEqual(result, 1)
        self.assertTrue(first.closed)

    def test_raw_ddl_has_twelve_loader_owned_targets_and_no_destructive_sql(self):
        ddl = (ROOT / "sql" / "03-create-raw.sql").read_text(encoding="utf-8")
        for table in raw_loader._managed_tables():
            self.assertIn(f"CREATE TABLE IF NOT EXISTS raw.{table}", ddl)
        self.assertNotIn("DROP SCHEMA", ddl.upper())
        self.assertNotIn("CASCADE", ddl.upper())
        self.assertNotIn("ALTER OWNER", ddl.upper())


if __name__ == "__main__":
    unittest.main()
