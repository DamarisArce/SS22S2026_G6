import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DBT = ROOT / "dbt"
MODEL = DBT / "models" / "intermediate" / "int_devoluciones_enriquecida.sql"
SCHEMA = DBT / "models" / "intermediate" / "schema.yml"
TESTS = DBT / "tests"


class DbtReturnsIntermediateContractTest(unittest.TestCase):
    def setUp(self):
        self.model = MODEL.read_text()
        self.schema = SCHEMA.read_text()
        self.dbt_tests = {
            name: (TESTS / name).read_text()
            for name in (
                "int_devoluciones_reconciliacion.sql",
                "int_devoluciones_integridad_origen.sql",
                "int_devoluciones_integridad_enriquecimiento.sql",
            )
        }

    def test_model_has_exactly_three_authorized_refs_and_two_left_joins(self):
        refs = re.findall(r"\{\{\s*ref\('([^']+)'\)\s*\}\}", self.model)
        self.assertEqual(
            refs,
            [
                "stg_csv_devoluciones",
                "stg_oltp_venta",
                "stg_oltp_producto",
            ],
        )
        self.assertEqual(len(re.findall(r"\bleft join\b", self.model, re.I)), 2)

    def test_model_preserves_return_grain_original_fields_and_metadata(self):
        for column in (
            "id_devolucion",
            "fecha",
            "id_venta",
            "id_producto",
            "cantidad",
            "motivo",
            "_etl_load_id",
            "_etl_loaded_at",
            "_etl_source_name",
            "_etl_source_sha256",
            "_etl_row_number",
        ):
            self.assertRegex(self.model, rf"\bdevolucion\.{column}\b")
        self.assertRegex(self.model, r"\bventa\.fecha\s+as\s+fecha_venta\b")
        self.assertRegex(self.model, r"\bdevolucion\.fecha\b")
        self.assertRegex(self.model, r"\bproducto\.nombre\s+as\s+nombre_producto\b")

    def test_model_has_no_forbidden_sources_or_derivations(self):
        self.assertNotIn("venta_detalle", self.model)
        self.assertNotRegex(self.model, re.compile(r"\b(?:importe|reembolso|venta_neta|neto|porcentaje)\b", re.I))
        self.assertNotRegex(self.model, re.compile(r"select\s+\*", re.I))
        self.assertNotRegex(self.model, re.compile(r"\bdistinct\b|\bgroup\s+by\b|\bhaving\b", re.I))
        self.assertNotRegex(self.model, re.compile(r"\bwhere\b|\b(?:current_date|now)\s*\(", re.I))

    def test_schema_declares_grain_relations_and_required_attributes(self):
        self.assertIn("name: int_devoluciones_enriquecida", self.schema)
        self.assertRegex(self.schema, r"name: id_devolucion[\s\S]*?tests: \[not_null, unique\]")
        self.assertIn("to: ref('stg_oltp_venta')", self.schema)
        self.assertIn("to: ref('stg_oltp_producto')", self.schema)
        for column in (
            "fecha",
            "id_venta",
            "id_producto",
            "cantidad",
            "motivo",
            "fecha_venta",
            "id_cliente",
            "id_sucursal",
            "canal",
            "metodo_pago",
            "estado",
            "sku",
            "nombre_producto",
            "id_categoria",
            "id_marca",
            "unidad_medida",
        ):
            self.assertRegex(self.schema, rf"name: {column}[\s\S]*?tests: \[not_null\]")

    def test_all_three_singular_tests_are_present(self):
        self.assertEqual(
            sorted(self.dbt_tests),
            [
                "int_devoluciones_integridad_enriquecimiento.sql",
                "int_devoluciones_integridad_origen.sql",
                "int_devoluciones_reconciliacion.sql",
            ],
        )

    def test_reconciliation_is_dynamic_and_null_safe(self):
        sql = self.dbt_tests["int_devoluciones_reconciliacion.sql"]
        self.assertIn("count(*)", sql.lower())
        self.assertIn("sum(cantidad)", sql.lower())
        self.assertIn("is distinct from", sql.lower())
        self.assertNotIn("80", sql)

    def test_origin_integrity_is_bidirectional_and_compares_all_original_fields(self):
        sql = self.dbt_tests["int_devoluciones_integridad_origen.sql"]
        self.assertGreaterEqual(sql.lower().count("except all"), 2)
        for column in (
            "id_devolucion",
            "fecha",
            "id_venta",
            "id_producto",
            "cantidad",
            "motivo",
            "_etl_load_id",
            "_etl_loaded_at",
            "_etl_source_name",
            "_etl_source_sha256",
            "_etl_row_number",
        ):
            self.assertIn(column, sql)

    def test_enrichment_integrity_is_parent_based_and_null_safe(self):
        sql = self.dbt_tests["int_devoluciones_integridad_enriquecimiento.sql"]
        self.assertIn("stg_csv_devoluciones", sql)
        self.assertIn("stg_oltp_venta", sql)
        self.assertIn("stg_oltp_producto", sql)
        self.assertIn("full outer join", sql.lower())
        self.assertIn("is distinct from", sql.lower())
        self.assertIn("select count(*) from expected", sql.lower())
        self.assertIn("select count(*) from actual", sql.lower())
        self.assertIn("select count(*) from {{ ref('stg_csv_devoluciones') }}", sql.lower())
        for column in (
            "fecha_venta",
            "id_cliente",
            "id_sucursal",
            "canal",
            "metodo_pago",
            "estado",
            "sku",
            "nombre_producto",
            "id_categoria",
            "id_marca",
            "unidad_medida",
        ):
            self.assertIn(column, sql)


if __name__ == "__main__":
    unittest.main()
