import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DBT = ROOT / "dbt"
MODEL = DBT / "models" / "marts" / "dim_sucursal.sql"
SCHEMA = DBT / "models" / "marts" / "schema.yml"
TESTS = DBT / "tests"

EXPECTED_COLUMNS = (
    "id_sucursal", "nombre", "ciudad", "departamento", "_etl_load_id",
    "_etl_loaded_at", "_etl_source_table", "_etl_extracted_at",
)
SINGULAR_TESTS = {
    "dim_sucursal_clave_unica.sql",
    "dim_sucursal_reconciliacion.sql",
    "dim_sucursal_integridad_origen.sql",
    "dim_sucursal_integridad_ventas.sql",
}


class DbtMartsBranchContractTest(unittest.TestCase):
    def setUp(self):
        self.project = (DBT / "dbt_project.yml").read_text()
        self.model = MODEL.read_text()
        self.schema = SCHEMA.read_text()
        self.dbt_tests = {
            path.name: path.read_text()
            for path in TESTS.glob("dim_sucursal_*.sql")
        }

    def test_model_exists_with_authorized_source_and_explicit_columns(self):
        self.assertTrue(MODEL.exists())
        refs = re.findall(r"\{\{\s*ref\('([^']+)'\)\s*\}\}", self.model)
        self.assertEqual(refs, ["stg_oltp_sucursal"])
        self.assertNotRegex(self.model, re.compile(r"select\s+\*", re.I))
        select_list = self.model.split("from", 1)[0]
        for column in EXPECTED_COLUMNS:
            self.assertRegex(select_list, rf"\b{re.escape(column)}\b")

    def test_model_preserves_grain_and_view_materialization(self):
        self.assertIn("materialized='view'", self.model)
        self.assertIn("schema='marts'", self.model)
        self.assertNotRegex(self.model, re.compile(r"\bjoin\b|\bwhere\b|\bgroup\s+by\b", re.I))
        self.assertNotRegex(self.model, re.compile(r"\bdistinct\b|\bsum\s*\(", re.I))
        self.assertNotRegex(self.model, re.compile(r"\b(coalesce|case|when|over)\b", re.I))

    def test_schema_documents_dimension_contract(self):
        self.assertIn("name: dim_sucursal", self.schema)
        dimension = self.schema.split("name: dim_sucursal", 1)[1]
        self.assertIn("stg_oltp_sucursal", dimension)
        self.assertIn("una fila por id_sucursal", dimension)
        self.assertIn("clave natural", dimension.lower())
        self.assertIn("hist", dimension.lower())
        self.assertRegex(dimension, r"name: id_sucursal[\s\S]*?tests: \[not_null, unique\]")
        for column in EXPECTED_COLUMNS:
            self.assertIn(f"name: {column}", dimension)

    def test_singular_tests_are_dynamic_and_present(self):
        self.assertEqual(set(self.dbt_tests), SINGULAR_TESTS)
        key_test = self.dbt_tests["dim_sucursal_clave_unica.sql"]
        self.assertIn("group by id_sucursal", key_test)
        self.assertIn("having count(*) > 1", key_test)
        reconciliation = self.dbt_tests["dim_sucursal_reconciliacion.sql"]
        self.assertIn("count(*)", reconciliation)
        self.assertIn("count(distinct id_sucursal)", reconciliation)
        self.assertIn("is distinct from", reconciliation)
        self.assertNotRegex(reconciliation, r"\b(?:6|8864)\b")

    def test_origin_integrity_is_explicit_and_bidirectional(self):
        sql = self.dbt_tests["dim_sucursal_integridad_origen.sql"]
        self.assertEqual(sql.lower().count("except all"), 2)
        self.assertNotIn("select *", sql.lower())
        for column in EXPECTED_COLUMNS:
            self.assertGreaterEqual(sql.count(column), 4)

    def test_sales_relationship_test_is_explicit_without_deduplication(self):
        sql = self.dbt_tests["dim_sucursal_integridad_ventas.sql"]
        self.assertIn("fct_ventas_detalle", sql)
        self.assertIn("dim_sucursal", sql)
        self.assertRegex(sql, re.compile(r"left\s+join", re.I))
        self.assertIn("where sucursal.id_sucursal is null", sql.lower())
        self.assertNotRegex(sql, re.compile(r"\bdistinct\b", re.I))

    def test_previous_first_mart_contract_is_preserved(self):
        fact = SCHEMA.read_text().split("- name: fct_ventas_detalle", 1)[1]
        for marker in (
            "id_detalle", "id_venta", "id_producto", "id_cliente", "id_sucursal",
            "cantidad", "precio_unitario", "descuento", "subtotal",
            "_etl_load_id", "_etl_loaded_at", "_etl_source_table", "_etl_extracted_at",
        ):
            self.assertIn(marker, fact.split("- name: dim_sucursal", 1)[0])
        self.assertEqual(
            len(list(TESTS.glob("fct_ventas_detalle_*.sql"))),
            3,
        )

    def test_no_invented_scd_rules(self):
        self.assertNotRegex(self.model, re.compile(r"scd|valid_from|valid_to|is_current|surrogate", re.I))
        dimension = self.schema.split("name: dim_sucursal", 1)[1]
        self.assertNotRegex(dimension, re.compile(r"name:\s*(valid_from|valid_to|is_current|surrogate_key)", re.I))


if __name__ == "__main__":
    unittest.main()
