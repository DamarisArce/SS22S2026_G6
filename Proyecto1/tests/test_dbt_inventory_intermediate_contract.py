import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DBT = ROOT / "dbt"
MODEL = DBT / "models" / "intermediate" / "int_inventario_snapshot.sql"
SCHEMA = DBT / "models" / "intermediate" / "schema.yml"
TESTS = DBT / "tests"


class DbtInventoryIntermediateContractTest(unittest.TestCase):
    def setUp(self):
        self.model = MODEL.read_text()
        self.schema = SCHEMA.read_text()
        self.dbt_tests = {
            name: (TESTS / name).read_text()
            for name in (
                "int_inventario_snapshot_clave_unica.sql",
                "int_inventario_snapshot_reconciliacion.sql",
                "int_inventario_snapshot_integridad_origen.sql",
                "int_inventario_snapshot_vencimiento.sql",
            )
        }

    def test_preserves_composite_grain_and_uses_exactly_three_authorized_refs(self):
        refs = re.findall(r"\{\{\s*ref\('([^']+)'\)\s*\}\}", self.model)
        self.assertEqual(
            refs,
            [
                "stg_csv_inventario_bodega",
                "stg_oltp_producto",
                "stg_oltp_sucursal",
            ],
        )
        for column in ("fecha_corte", "id_sucursal", "id_producto", "lote"):
            self.assertRegex(self.model, rf"\binventario\.{column}\b")

    def test_uses_two_left_joins_without_fanout_sources(self):
        self.assertEqual(len(re.findall(r"\bleft join\b", self.model, re.I)), 2)
        self.assertNotRegex(self.model, re.compile(r"\b(?:where|distinct|group\s+by|having)\b", re.I))
        self.assertNotRegex(self.model, re.compile(r"select\s+\*", re.I))
        self.assertNotIn("stg_csv_", self.model.replace("stg_csv_inventario_bodega", ""))
        refs = re.findall(r"\{\{\s*ref\('([^']+)'\)\s*\}\}", self.model)
        self.assertEqual(len(refs), 3)

    def test_preserves_inventory_measures_and_technical_metadata(self):
        for column in (
            "stock_disponible",
            "stock_minimo",
            "stock_maximo",
            "fecha_vencimiento",
            "_etl_load_id",
            "_etl_loaded_at",
            "_etl_source_name",
            "_etl_source_sha256",
            "_etl_row_number",
        ):
            self.assertRegex(self.model, rf"\binventario\.{column}\b")

    def test_vencimiento_is_relative_to_cutoff_and_handles_nulls(self):
        self.assertIn("inventario.fecha_vencimiento < inventario.fecha_corte", self.model)
        self.assertIn("inventario.fecha_vencimiento - inventario.fecha_corte", self.model)
        self.assertRegex(
            self.model,
            r"when inventario\.fecha_vencimiento is null then null",
        )
        self.assertNotRegex(self.model, re.compile(r"\b(?:current_date|now)\s*\(", re.I))

    def test_schema_contract_documents_grain_relations_and_required_parent_attributes(self):
        self.assertIn("name: int_inventario_snapshot", self.schema)
        for column in ("fecha_corte", "id_sucursal", "id_producto", "lote"):
            self.assertRegex(
                self.schema,
                rf"name: {column}[\s\S]*?tests: \[not_null\]",
            )
        self.assertIn("to: ref('stg_oltp_sucursal')", self.schema)
        self.assertIn("to: ref('stg_oltp_producto')", self.schema)
        for column in ("sku", "nombre_producto", "nombre_sucursal"):
            self.assertRegex(
                self.schema,
                rf"name: {column}[\s\S]*?tests: \[not_null\]",
            )
        self.assertIn("es_vencido_en_corte", self.schema)
        self.assertIn("dias_para_vencer", self.schema)

    def test_all_four_singular_tests_are_present(self):
        self.assertEqual(
            sorted(self.dbt_tests),
            [
                "int_inventario_snapshot_clave_unica.sql",
                "int_inventario_snapshot_integridad_origen.sql",
                "int_inventario_snapshot_reconciliacion.sql",
                "int_inventario_snapshot_vencimiento.sql",
            ],
        )

    def test_key_test_checks_composite_duplicates(self):
        sql = self.dbt_tests["int_inventario_snapshot_clave_unica.sql"]
        self.assertIn("group by fecha_corte, id_sucursal, id_producto, lote", sql.lower())
        self.assertIn("having count(*) > 1", sql.lower())

    def test_reconciliation_is_dynamic_and_null_safe(self):
        sql = self.dbt_tests["int_inventario_snapshot_reconciliacion.sql"]
        for expression in (
            "count(*)",
            "sum(stock_disponible)",
            "sum(stock_minimo)",
            "sum(stock_maximo)",
            "is distinct from",
        ):
            self.assertIn(expression, sql.lower())
        self.assertNotIn("3840", sql)

    def test_origin_integrity_is_bidirectional_and_compares_source_fields(self):
        sql = self.dbt_tests["int_inventario_snapshot_integridad_origen.sql"]
        self.assertIn("full outer join", sql.lower())
        self.assertIn("is distinct from", sql.lower())
        for column in (
            "stock_disponible",
            "stock_minimo",
            "stock_maximo",
            "fecha_vencimiento",
            "_etl_load_id",
            "_etl_loaded_at",
            "_etl_source_name",
            "_etl_source_sha256",
            "_etl_row_number",
        ):
            self.assertIn(column, sql)

    def test_expiration_test_recalculates_null_and_same_day_cases(self):
        sql = self.dbt_tests["int_inventario_snapshot_vencimiento.sql"]
        self.assertIn("fecha_vencimiento is null", sql.lower())
        self.assertIn("fecha_vencimiento = fecha_corte", sql.lower())
        self.assertIn("fecha_vencimiento < fecha_corte", sql.lower())
        self.assertIn("fecha_vencimiento - fecha_corte", sql.lower())
        self.assertIn("is distinct from", sql.lower())
        self.assertNotRegex(sql, re.compile(r"\b(?:current_date|now)\s*\(", re.I))


if __name__ == "__main__":
    unittest.main()
