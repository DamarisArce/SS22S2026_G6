import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DBT = ROOT / "dbt"
MODEL = DBT / "models" / "marts" / "fct_ventas_detalle.sql"
SCHEMA = DBT / "models" / "marts" / "schema.yml"


class DbtMartsSalesContractTest(unittest.TestCase):
    def setUp(self):
        self.project = (DBT / "dbt_project.yml").read_text()
        self.model = MODEL.read_text()
        self.schema = SCHEMA.read_text()
        self.dbt_tests = {
            path.name: path.read_text()
            for path in (DBT / "tests").glob("fct_ventas_detalle_*.sql")
        }

    def test_model_exists_with_one_authorized_ref_and_explicit_columns(self):
        self.assertTrue(MODEL.exists())
        refs = re.findall(r"\{\{\s*ref\('([^']+)'\)\s*\}\}", self.model)
        self.assertEqual(refs, ["int_venta_detalle_enriquecida"])
        self.assertNotRegex(self.model, r"select\s+\*", re.I)
        for column in (
            "id_detalle", "id_venta", "id_producto", "id_cliente",
            "id_sucursal", "fecha", "cantidad", "precio_unitario",
            "descuento", "subtotal", "_etl_load_id", "_etl_loaded_at",
            "_etl_source_table", "_etl_extracted_at",
        ):
            self.assertRegex(self.model, rf"\b{column}\b")

    def test_model_preserves_grain_and_has_no_transformations(self):
        self.assertIn("materialized='view'", self.model)
        self.assertIn("schema='marts'", self.model)
        self.assertNotRegex(self.model, r"\bjoin\b|\bwhere\b|\bgroup\s+by\b", re.I)
        self.assertNotRegex(self.model, r"\bdistinct\b|\bsum\s*\(|\bround\s*\(", re.I)
        self.assertNotRegex(self.model, r"\b(coalesce|case|when|over)\b", re.I)

    def test_schema_documents_grain_measures_limitations_and_relationships(self):
        self.assertIn("name: fct_ventas_detalle", self.schema)
        self.assertIn("id_detalle", self.schema)
        self.assertRegex(self.schema, r"name: id_detalle[\s\S]*?tests: \[not_null, unique\]")
        for parent in (
            "stg_oltp_venta", "stg_oltp_producto", "stg_oltp_cliente",
            "stg_oltp_sucursal",
        ):
            self.assertIn(f"to: ref('{parent}')", self.schema)
        for column in ("cantidad", "precio_unitario", "descuento", "subtotal"):
            self.assertIn(f"name: {column}", self.schema)
        self.assertIn("no aplica filtros comerciales", self.schema.lower())

    def test_singular_tests_are_present_and_dynamic(self):
        self.assertEqual(
            set(self.dbt_tests),
            {
                "fct_ventas_detalle_clave_unica.sql",
                "fct_ventas_detalle_reconciliacion.sql",
                "fct_ventas_detalle_integridad_origen.sql",
            },
        )
        key_test = self.dbt_tests["fct_ventas_detalle_clave_unica.sql"]
        self.assertIn("group by id_detalle", key_test)
        self.assertIn("having count(*) > 1", key_test)
        reconciliation = self.dbt_tests["fct_ventas_detalle_reconciliacion.sql"]
        for expression in ("count(*)", "count(distinct id_detalle)", "sum(cantidad)", "sum(subtotal)"):
            self.assertIn(expression, reconciliation)
        self.assertIn("is distinct from", reconciliation)
        self.assertNotIn("3209", reconciliation)

    def test_origin_integrity_is_explicit_and_bidirectional(self):
        sql = self.dbt_tests["fct_ventas_detalle_integridad_origen.sql"]
        self.assertEqual(sql.lower().count("except all"), 2)
        self.assertNotIn("select *", sql.lower())
        for column in (
            "id_detalle", "id_venta", "id_producto", "id_cliente",
            "id_sucursal", "fecha", "cantidad", "precio_unitario",
            "descuento", "subtotal", "_etl_load_id", "_etl_loaded_at",
            "_etl_source_table", "_etl_extracted_at",
        ):
            self.assertGreaterEqual(sql.count(column), 4)

    def test_previous_contracts_are_not_modified_by_this_contract(self):
        previous_models = sorted((DBT / "models" / "intermediate").glob("*.sql"))
        self.assertEqual(len(previous_models), 4)
        self.assertNotIn("marts:", self.project)


if __name__ == "__main__":
    unittest.main()
