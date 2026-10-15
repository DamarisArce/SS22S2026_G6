import ast
import contextlib
import hashlib
import importlib.util
import io
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("integrity_reconciliation", ROOT / "etl/integrity_reconciliation.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeCursor:
    def __init__(self, rows, fail=False, error=None):
        self.rows = rows
        self.fail = fail
        self.error = error
        self.query_log = []
        self.current = ""

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, query, params=()):
        if self.fail:
            raise self.error or OSError("simulated connection failure")
        self.current = str(query)
        self.query_log.append(self.current)

    def fetchall(self):
        query = self.current
        if "FROM oltp_sgfood." in query:
            table = query.split("FROM oltp_sgfood.", 1)[1].split()[0]
            return list(self.rows.get(f"oltp_sgfood.{table}", ()))
        if "FROM raw." in query:
            table = query.split("FROM raw.", 1)[1].split()[0]
            return list(self.rows.get(f"raw.{table}", ()))
        if "FROM marts." in query:
            table = query.split("FROM marts.", 1)[1].split()[0]
            if table == "fct_ventas_detalle" and query.startswith("SELECT id_producto"):
                return [(100, 1, 1)]
            return list(self.rows.get(f"marts.{table}", ()))
        if "FROM intermediate." in query:
            table = query.split("FROM intermediate.", 1)[1].split()[0]
            return list(self.rows.get(f"intermediate.{table}", ()))
        raise AssertionError(f"unhandled fetchall query: {query}")

    def fetchone(self):
        query = self.current
        if "COUNT(*), COUNT(DISTINCT _etl_source_sha256)" in query:
            table = query.split("FROM raw.", 1)[1].split()[0]
            rows = self.rows.get(f"raw.{table}", ())
            return (len(rows), 1 if rows else 0)
        if query.startswith("SELECT COUNT(*) FROM marts.fct_ventas_detalle") and " JOIN " not in query and "LEFT JOIN" not in query:
            return (len(self.rows.get("marts.fct_ventas_detalle", ())),)
        if "duplicate natural keys" in query or "HAVING COUNT(*) > 1" in query:
            return (0,)
        if "fact enrichment" in query or "raw.oltp_venta AS venta" in query:
            return (0,)
        if "LEFT JOIN" in query or "raw.oltp_venta AS venta" in query:
            return (0,)
        if " JOIN " in query:
            return (len(self.rows.get("marts.fct_ventas_detalle", ())),)
        if query.startswith("SELECT COUNT(*) FROM "):
            relation = query.split("FROM ", 1)[1].split()[0]
            return (len(self.rows.get(relation, ())),)
        raise AssertionError(f"unhandled fetchone query: {query}")


class FakeConnection:
    def __init__(self, cursor, rollback_error=None, close_error=None):
        self.fake_cursor = cursor
        self.rollback_error = rollback_error
        self.close_error = close_error
        self.commits = 0
        self.rollbacks = 0
        self.closed = False
        self.calls = []

    def cursor(self):
        return self.fake_cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.calls.append("rollback")
        self.rollbacks += 1
        if self.rollback_error:
            raise self.rollback_error

    def close(self):
        self.calls.append("close")
        if self.close_error:
            raise self.close_error
        self.closed = True


class IntegrityReconciliationTest(unittest.TestCase):
    def _reconcile_without_controls(self, first, second):
        controls = (
            "_check_oltp_vs_raw", "_check_csv_and_keys", "_check_relationships",
            "_csv_reconciliations", "_fact_reconciliation", "_check_fact_coverage",
            "_check_fact_enrichment", "_inventory_and_returns",
        )
        with contextlib.ExitStack() as stack:
            for name in controls:
                stack.enter_context(mock.patch.object(MODULE, name, return_value=[]))
            MODULE.reconcile(first, second, tempfile.gettempdir())

    def _dataset(self, fact=None, inventory=None, returns=None):
        detail = [(1, 10, 100, 2, "5.00", "0.10", "9.00")]
        oltp = {f"oltp_sgfood.{table}": [] for table in MODULE.OLTP_CONTRACTS}
        raw = {f"raw.oltp_{table}": [] for table in MODULE.OLTP_CONTRACTS}
        oltp["oltp_sgfood.venta_detalle"] = detail
        raw["raw.oltp_venta_detalle"] = detail
        csv_rows = {
            "csv_inventario_bodega": [("2026-01-01", "1", "100", "2", "1", "5", "L1", "")],
            "csv_devoluciones": [("7", "2026-01-02", "10", "100", "1", "daño")],
            "csv_metas_ventas": [], "csv_promociones": [], "csv_proveedores_precios": [],
        }
        for table, rows in csv_rows.items():
            raw[f"raw.{table}"] = [tuple(row) + ("file.csv", "hash", number) for number, row in enumerate(rows, 2)]
        return {**oltp, **raw,
                "marts.fct_ventas_detalle": fact if fact is not None else detail,
                "marts.dim_producto": [(100,)],
                "marts.dim_cliente": [(1,)],
                "marts.dim_sucursal": [(1,)],
                "intermediate.int_inventario_snapshot": inventory if inventory is not None else csv_rows["csv_inventario_bodega"],
                "intermediate.int_devoluciones_enriquecida": returns if returns is not None else csv_rows["csv_devoluciones"]}

    def _source_dir(self, changed=False):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name)
        for spec in MODULE.CSV_COLUMNS:
            filename = MODULE.CSV_FILES[spec]
            rows = {
                "inventario_bodega.csv": [("2026-01-01", "1", "100", "2", "1", "5", "L1", "")],
                "devoluciones.csv": [("7", "2026-01-02", "10", "100", "1", "daño")],
                "metas_ventas.csv": [], "promociones.csv": [], "proveedores_precios.csv": [],
            }[filename]
            if changed and filename == "devoluciones.csv":
                rows = [("7", "2026-01-02", "10", "100", "9", "daño")]
            columns = MODULE.CSV_COLUMNS[spec]
            (path / filename).write_text(",".join(columns) + "\n" + "\n".join(",".join(row) for row in rows) + ("\n" if rows else ""), encoding="utf-8")
        return directory, path

    def _aligned(self, data, source):
        for table, filename in MODULE.CSV_FILES.items():
            digest = hashlib.sha256((source / filename).read_bytes()).hexdigest()
            data[f"raw.{table}"] = [tuple(row[:-3]) + (filename, digest, row[-1]) for row in data[f"raw.{table}"]]
        return data

    def test_correct_case_rolls_back_read_only_transactions(self):
        directory, source = self._source_dir()
        try:
            data = self._aligned(self._dataset(), source)
            oltp_cursor = FakeCursor(data)
            dw_cursor = FakeCursor(data)
            oltp, dw = FakeConnection(oltp_cursor), FakeConnection(dw_cursor)
            MODULE.reconcile(oltp, dw, source)
            self.assertEqual((oltp.commits, dw.commits), (0, 0))
            self.assertEqual((oltp.rollbacks, dw.rollbacks), (1, 1))
            self.assertTrue(oltp.closed and dw.closed)
            self.assertTrue(all("SET TRANSACTION READ ONLY" in cursor.query_log for cursor in (oltp_cursor, dw_cursor)))
            self.assertTrue(all(not any(word in query.upper() for word in ("INSERT", "UPDATE", "DELETE", "TRUNCATE", "DROP", "ALTER")) for cursor in (oltp_cursor, dw_cursor) for query in cursor.query_log))
        finally:
            directory.cleanup()

    def test_ast_has_one_definition_per_top_level_function(self):
        tree = ast.parse((ROOT / "etl/integrity_reconciliation.py").read_text())
        definitions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
        self.assertEqual(len(definitions), len(set(definitions)))
        self.assertEqual(definitions.count("reconcile"), 1)
        self.assertNotIn("_check_fact_and_coverage", definitions)
        defined = set(definitions)
        invoked = {
            node.func.id for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertNotIn("_check_fact_and_coverage", invoked)
        required = {
            "_check_oltp_vs_raw", "_check_csv_and_keys", "_check_relationships",
            "_csv_reconciliations", "_fact_reconciliation", "_check_fact_coverage",
            "_check_fact_enrichment", "_inventory_and_returns",
        }
        self.assertTrue(required <= defined)
        self.assertTrue(required <= invoked)

    def test_reconcile_invokes_every_required_control(self):
        directory, source = self._source_dir()
        try:
            data = self._aligned(self._dataset(), source)
            controls = (
                "_check_oltp_vs_raw", "_check_csv_and_keys", "_check_relationships",
                "_csv_reconciliations", "_fact_reconciliation", "_check_fact_coverage",
                "_check_fact_enrichment", "_inventory_and_returns",
            )
            calls = []

            def wrapper(name):
                def invoke(*args):
                    calls.append(name)
                    return []
                return invoke

            patches = [mock.patch.object(MODULE, name, side_effect=wrapper(name)) for name in controls]
            with contextlib.ExitStack() as stack:
                for patcher in patches:
                    stack.enter_context(patcher)
                MODULE.reconcile(FakeConnection(FakeCursor(data)), FakeConnection(FakeCursor(data)), source)
            self.assertEqual(calls, list(controls))
        finally:
            directory.cleanup()

    def test_reconcile_sql_exception_rolls_back_and_closes_both_connections(self):
        first = FakeConnection(FakeCursor({}, fail=True))
        second = FakeConnection(FakeCursor({}))
        with self.assertRaises(OSError):
            MODULE.reconcile(first, second, tempfile.gettempdir())
        self.assertEqual((first.rollbacks, second.rollbacks), (1, 1))
        self.assertTrue(first.closed and second.closed)

    def test_rollback_failure_on_oltp_still_cleans_dw(self):
        first = FakeConnection(FakeCursor({}), rollback_error=OSError("oltp rollback"))
        second = FakeConnection(FakeCursor({}))
        with self.assertRaisesRegex(OSError, "oltp rollback"):
            self._reconcile_without_controls(first, second)
        self.assertEqual(first.calls, ["rollback", "close"])
        self.assertEqual(second.calls, ["rollback", "close"])

    def test_close_failure_on_oltp_still_closes_dw(self):
        first = FakeConnection(FakeCursor({}), close_error=OSError("oltp close"))
        second = FakeConnection(FakeCursor({}))
        with self.assertRaisesRegex(OSError, "oltp close"):
            self._reconcile_without_controls(first, second)
        self.assertEqual(first.calls, ["rollback", "close"])
        self.assertEqual(second.calls, ["rollback", "close"])
        self.assertTrue(second.closed)

    def test_rollback_failure_on_dw_still_closes_oltp_and_dw(self):
        first = FakeConnection(FakeCursor({}))
        second = FakeConnection(FakeCursor({}), rollback_error=OSError("dw rollback"))
        with self.assertRaisesRegex(OSError, "dw rollback"):
            self._reconcile_without_controls(first, second)
        self.assertEqual(first.calls, ["rollback", "close"])
        self.assertEqual(second.calls, ["rollback", "close"])
        self.assertTrue(first.closed)

    def test_sql_error_has_priority_over_cleanup_error(self):
        sql_error = OSError("SQL failure")
        first = FakeConnection(FakeCursor({}, fail=True, error=sql_error), rollback_error=OSError("rollback failure"))
        second = FakeConnection(FakeCursor({}))
        with self.assertRaises(OSError) as raised:
            MODULE.reconcile(first, second, tempfile.gettempdir())
        self.assertIs(raised.exception, sql_error)
        self.assertEqual(first.calls, ["rollback", "close"])
        self.assertEqual(second.calls, ["rollback", "close"])

    def test_cleanup_error_without_sql_error_is_not_reported_as_success(self):
        first = FakeConnection(FakeCursor({}), rollback_error=OSError("cleanup failure"))
        second = FakeConnection(FakeCursor({}))
        with self.assertRaisesRegex(OSError, "cleanup failure"):
            self._reconcile_without_controls(first, second)
        self.assertEqual(second.calls, ["rollback", "close"])

    def test_fact_duplicate_fanout_and_replacement_are_failures(self):
        directory, source = self._source_dir()
        try:
            duplicate = [(1, 10, 100, 2, "5.00", "0.10", "9.00"), (1, 10, 100, 2, "5.00", "0.10", "9.00")]
            base = self._aligned(self._dataset(), source)
            duplicate_data = self._aligned(self._dataset(fact=duplicate), source)
            with self.assertRaises(MODULE.ReconciliationError):
                MODULE.reconcile(FakeConnection(FakeCursor(base)), FakeConnection(FakeCursor(duplicate_data)), source)
            replaced = [(1, 10, 100, 1, "5.00", "0.10", "9.00")]
            replaced_data = self._aligned(self._dataset(fact=replaced), source)
            with self.assertRaises(MODULE.ReconciliationError):
                MODULE.reconcile(FakeConnection(FakeCursor(base)), FakeConnection(FakeCursor(replaced_data)), source)
        finally:
            directory.cleanup()

    def test_csv_hash_and_content_with_same_declared_hash_are_failures(self):
        directory, source = self._source_dir(changed=True)
        try:
            data = self._dataset()
            data["raw.csv_devoluciones"] = [("7", "2026-01-02", "10", "100", "1", "daño", "devoluciones.csv", "declared", 2)]
            with self.assertRaises(MODULE.ReconciliationError):
                MODULE.reconcile(FakeConnection(FakeCursor(data)), FakeConnection(FakeCursor(data)), source)
        finally:
            directory.cleanup()

    def test_inventory_multiple_dates_and_normalization_are_compared_as_rows(self):
        directory, source = self._source_dir()
        try:
            inventory = [("2026-01-01", "1", "100", "2", "1", "5", "L1", None), ("2026-02-01", "1", "100", "3", "1", "5", "L1", "")]
            data = self._dataset(inventory=inventory)
            data["raw.csv_inventario_bodega"] = [tuple(row) + ("inventario_bodega.csv", "x", n) for n, row in enumerate(inventory, 2)]
            with self.assertRaises(MODULE.ReconciliationError):
                MODULE.reconcile(FakeConnection(FakeCursor(data)), FakeConnection(FakeCursor(data)), source)
        finally:
            directory.cleanup()

    def test_partial_connection_error_rolls_back_both_and_closes_in_main(self):
        first = FakeConnection(FakeCursor({}, fail=True))
        calls = iter((first, OSError("second unavailable")))
        def connect(**_):
            value = next(calls)
            if isinstance(value, Exception):
                raise value
            return value
        original = MODULE._connect_parameters
        MODULE._connect_parameters = lambda *_: {}
        try:
            self.assertEqual(MODULE.main([], connect=connect), 1)
        finally:
            MODULE._connect_parameters = original
        self.assertTrue(first.closed)
        self.assertGreaterEqual(first.rollbacks, 1)

    def test_cli_precheck_without_real_connections(self):
        original = MODULE.psycopg
        class Driver:
            def connect(self, **_):
                raise AssertionError("real connection attempted")
        MODULE.psycopg = Driver()
        try:
            self.assertEqual(MODULE.main(["--precheck"]), 1)
        finally:
            MODULE.psycopg = original

    def test_fecha_vencimiento_normalizes_text_date_and_blank(self):
        self.assertEqual(MODULE._normalized("2026-11-11", "fecha_vencimiento"), MODULE.date(2026, 11, 11))
        self.assertEqual(MODULE._normalized(MODULE.date(2026, 11, 11), "fecha_vencimiento"), MODULE.date(2026, 11, 11))
        self.assertIsNone(MODULE._normalized("", "fecha_vencimiento"))
        with self.assertRaises(MODULE.ReconciliationError):
            MODULE._normalized("2026-99-99", "fecha_vencimiento")

    def test_multiple_lots_same_cutoff_preserve_distinct_expiry_dates(self):
        columns = MODULE.CSV_COLUMNS["csv_inventario_bodega"]
        rows = [
            ("2026-11-01", "1", "100", "2", "1", "5", "L1", "2026-11-11"),
            ("2026-11-01", "1", "100", "3", "1", "5", "L2", "2026-12-11"),
        ]
        normalized = MODULE._normalized_rows(rows, columns)
        self.assertEqual(normalized[0][0], normalized[1][0])
        self.assertNotEqual(normalized[0][3], normalized[1][3])
        self.assertNotEqual(normalized[0][-1], normalized[1][-1])

    def test_many_to_one_coverage_is_not_counter_subtraction(self):
        class CoverageCursor:
            def __init__(self): self.query = ""
            def execute(self, query, params=()): self.query = query
            def fetchone(self):
                if "COUNT(*) FROM marts.fct_ventas_detalle" in self.query and "JOIN" not in self.query:
                    return (2,)
                if "HAVING COUNT(*)" in self.query or "LEFT JOIN" in self.query:
                    return (0,)
                return (2,)
        mismatches = MODULE._check_fact_coverage(CoverageCursor())
        self.assertEqual(mismatches, [])

    def test_negative_fk_duplicate_dimension_and_enrichment_cases_are_identified(self):
        class ScenarioCursor:
            def __init__(self, scenario): self.scenario, self.query = scenario, ""
            def execute(self, query, params=()): self.query = query
            def fetchone(self):
                if self.scenario == "fk" and "LEFT JOIN" in self.query: return (1,)
                if self.scenario == "dimension" and "HAVING COUNT(*)" in self.query: return (1,)
                if self.scenario == "fanout" and "JOIN" in self.query and "LEFT JOIN" not in self.query: return (2,)
                if self.scenario == "enrichment" and "IS DISTINCT FROM" in self.query: return (1,)
                if self.scenario == "missing-header" and "venta.id_venta IS NULL" in self.query: return (1,)
                if "COUNT(*) FROM marts.fct_ventas_detalle" in self.query and "JOIN" not in self.query: return (1,)
                return (0,)
        self.assertTrue(MODULE._check_fact_coverage(ScenarioCursor("fk")))
        self.assertTrue(MODULE._check_fact_coverage(ScenarioCursor("dimension")))
        self.assertTrue(MODULE._check_fact_coverage(ScenarioCursor("fanout")))
        self.assertTrue(MODULE._check_fact_enrichment(ScenarioCursor("enrichment")))
        self.assertTrue(MODULE._check_fact_enrichment(ScenarioCursor("missing-header")))

    def test_relationship_orphan_is_identified(self):
        class RelationshipCursor:
            def execute(self, query, params=()): self.query = query
            def fetchone(self): return (1,)
        mismatches = MODULE._check_relationships(RelationshipCursor())
        self.assertEqual(len(mismatches), 6)

    def test_oltp_raw_difference_is_identified(self):
        class SourceRawCursor:
            def execute(self, query, params=()): self.query = query
            def fetchall(self):
                return [(1,)] if "oltp_sgfood" in self.query else []
        mismatches = MODULE._check_oltp_vs_raw(SourceRawCursor(), SourceRawCursor())
        self.assertTrue(any("content oltp" in item.name for item in mismatches))

    def test_duplicate_natural_key_is_identified(self):
        class DuplicateCursor:
            def execute(self, query, params=()): self.query = query
            def fetchone(self):
                if "HAVING COUNT(*)" in self.query: return (1,)
                return (0, 0)
        mismatches = MODULE._check_csv_and_keys(DuplicateCursor())
        self.assertTrue(any("duplicate natural keys" in item.name for item in mismatches))


if __name__ == "__main__":
    unittest.main()
