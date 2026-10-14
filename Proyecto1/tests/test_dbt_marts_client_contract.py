import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DBT = ROOT / "dbt"
MODEL = DBT / "models" / "marts" / "dim_cliente.sql"
SCHEMA = DBT / "models" / "marts" / "schema.yml"
TESTS = DBT / "tests"


COLUMNS = [
    "id_cliente",
    "nit",
    "nombre",
    "tipo_cliente",
    "municipio",
    "departamento",
    "fecha_alta",
    "_etl_load_id",
    "_etl_loaded_at",
    "_etl_source_table",
    "_etl_extracted_at",
]
ETL_COLUMNS = ["_etl_load_id", "_etl_loaded_at", "_etl_source_table", "_etl_extracted_at"]
SINGULARS = [
    "dim_cliente_integridad_origen.sql",
    "dim_cliente_integridad_ventas.sql",
    "dim_cliente_cobertura_sin_ventas.sql",
]


class DbtMartsClientContractTest(unittest.TestCase):
    def setUp(self):
        self.model = MODEL.read_text()
        self.schema = SCHEMA.read_text()
        self.mart_models = sorted((DBT / "models" / "marts").glob("*.sql"))
        self.singulars = {name: (TESTS / name).read_text() for name in SINGULARS}
        match = re.search(r"(?ms)^  - name: dim_cliente\n(.*?)(?=^  - name:|\Z)", self.schema)
        self.client_schema = match.group(1) if match else ""

    def test_model_exists_and_uses_exact_view_contract(self):
        self.assertTrue(MODEL.is_file())
        self.assertIn("{{ config(materialized='view', schema='marts') }}", self.model)
        self.assertEqual(re.findall(r"\{\{\s*ref\('([^']+)'\)\s*\}\}", self.model), ["stg_oltp_cliente"])

    def test_model_projects_only_the_eleven_explicit_columns(self):
        projection = self.model.split("from", 1)[0]
        for column in COLUMNS:
            self.assertRegex(projection, rf"\b{re.escape(column)}\b")
        self.assertNotRegex(self.model, re.compile(r"select\s+\*", re.I))
        self.assertNotRegex(self.model, re.compile(r"\b(join|group\s+by|distinct|where|having)\b", re.I))

    def test_model_preserves_nullable_attributes_and_etl_metadata(self):
        for column in COLUMNS:
            self.assertIn(column, self.model)
        self.assertNotRegex(self.model, re.compile(r"\bcoalesce\s*\(", re.I))
        self.assertNotRegex(self.model, re.compile(r"\b(scd|surrogate|hash|vigencia|version)\b", re.I))

    def test_schema_has_exact_client_tests_and_no_nit_or_nullable_tests(self):
        self.assertTrue(self.client_schema)
        self.assertEqual(len(re.findall(r"not_null", self.client_schema)), 9)
        self.assertRegex(self.client_schema, r"name: id_cliente[\s\S]*?tests: \[not_null, unique\]")
        self.assertNotRegex(re.search(r"name: nit\n(.*?)(?=\n      - name:|\Z)", self.client_schema, re.S).group(1), r"unique")
        for nullable in ("municipio", "departamento"):
            block = re.search(rf"name: {nullable}\n(.*?)(?=\n      - name:|\Z)", self.client_schema, re.S).group(1)
            self.assertNotIn("tests:", block)

    def test_schema_documents_contract_and_access_limits(self):
        for phrase in ("grano", "fuente", "fecha_alta", "SCD2", "NULL", "ventas", "anonimizadas"):
            self.assertIn(phrase, self.client_schema)
        self.assertNotRegex(self.client_schema, re.compile(r"\bgrant\b|\brole\b|\bprivilege\b", re.I))

    def test_singular_tests_exist_and_are_dynamic(self):
        for sql in self.singulars.values():
            self.assertIn("ref('dim_cliente')", sql)
            self.assertNotIn("250", sql)
            self.assertNotIn("3209", sql)
        origin = self.singulars[SINGULARS[0]]
        self.assertIn("except all", origin.lower())
        self.assertEqual(origin.lower().count("except all"), 2)
        self.assertNotRegex(origin, re.compile(r"\bdistinct\b", re.I))
        self.assertIn("staging_minus_dimension", origin)
        self.assertIn("dimension_minus_staging", origin)
        self.assertIn("staging_vs_dimension", origin)
        self.assertIn("dimension_vs_staging", origin)
        for column in COLUMNS:
            self.assertIn(column, origin)

    def test_sales_test_checks_keys_fanout_and_measures(self):
        sql = self.singulars["dim_cliente_integridad_ventas.sql"]
        for token in ("fct_ventas_detalle", "id_cliente", "id_detalle", "count(*)", "sum(cantidad)", "sum(subtotal)", "dimension_matches"):
            self.assertIn(token, sql)
        self.assertIn("left join", sql.lower())
        self.assertNotIn("3209", sql)

    def test_coverage_test_is_dynamic_and_distinguishes_sales_headers(self):
        sql = self.singulars["dim_cliente_cobertura_sin_ventas.sql"]
        self.assertIn("stg_oltp_cliente", sql)
        self.assertIn("stg_oltp_venta", sql)
        self.assertIn("not exists", sql.lower())
        self.assertGreaterEqual(sql.lower().count("except all"), 2)
        self.assertNotIn("fct_ventas_detalle", sql)
        self.assertNotRegex(sql, r"id_cliente\s*=\s*250")

    def test_previous_four_marts_are_preserved_and_no_access_expansion_is_added(self):
        required_marts = {
            "dim_cliente.sql",
            "dim_fecha.sql",
            "dim_producto.sql",
            "dim_sucursal.sql",
            "fct_ventas_detalle.sql",
        }
        actual_marts = {path.name for path in self.mart_models}
        self.assertTrue(required_marts.issubset(actual_marts))
        for path in self.mart_models:
            if path.name != "dim_cliente.sql":
                self.assertTrue(path.is_file())
        changed_text = "\n".join([self.model, self.client_schema, *self.singulars.values()])
        self.assertNotRegex(changed_text, re.compile(r"\bgrant\b|\bcreate\s+(role|user)\b", re.I))


if __name__ == "__main__":
    unittest.main()
