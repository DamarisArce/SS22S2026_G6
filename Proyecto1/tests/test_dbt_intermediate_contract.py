import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DBT = ROOT / "dbt"
MODEL = DBT / "models" / "intermediate" / "int_venta_detalle_enriquecida.sql"
SCHEMA = DBT / "models" / "intermediate" / "schema.yml"


class DbtIntermediateContractTest(unittest.TestCase):
    def setUp(self):
        self.project = (DBT / "dbt_project.yml").read_text()
        self.model = MODEL.read_text()
        self.schema = SCHEMA.read_text()
        self.dbt_tests = {
            path.name: path.read_text()
            for path in (DBT / "tests").glob("int_venta_detalle_*.sql")
        }
        self.intermediate_models = sorted(
            (DBT / "models" / "intermediate").glob("*.sql")
        )

    def test_has_exactly_the_two_intermediate_models(self):
        self.assertEqual(
            [path.name for path in self.intermediate_models],
            [
                "int_inventario_snapshot.sql",
                "int_venta_detalle_enriquecida.sql",
            ],
        )

    def test_model_uses_only_the_three_authorized_refs(self):
        refs = re.findall(r"\{\{\s*ref\('([^']+)'\)\s*\}\}", self.model)
        self.assertEqual(
            refs,
            [
                "stg_oltp_venta_detalle",
                "stg_oltp_venta",
                "stg_oltp_producto",
            ],
        )

    def test_model_has_no_fanout_sources_or_corrective_constructs(self):
        self.assertEqual(len(re.findall(r"\bleft join\b", self.model, re.I)), 2)
        self.assertNotIn("stg_csv_", self.model)
        self.assertNotRegex(self.model, r"ref\('stg_oltp_(?!venta_detalle|venta|producto)")
        self.assertNotRegex(self.model, re.compile(r"select\s+\*", re.I))
        self.assertNotRegex(self.model, re.compile(r"\bdistinct\b", re.I))
        self.assertNotRegex(self.model, re.compile(r"\bwhere\b", re.I))
        self.assertNotRegex(self.model, re.compile(r"\bgroup\s+by\b|\bhaving\b", re.I))

    def test_model_preserves_detail_measures_and_technical_fields(self):
        for column in (
            "id_detalle",
            "id_venta",
            "id_producto",
            "cantidad",
            "precio_unitario",
            "descuento",
            "subtotal",
            "_etl_load_id",
            "_etl_loaded_at",
            "_etl_source_table",
            "_etl_extracted_at",
        ):
            self.assertRegex(self.model, rf"\bdetalle\.{column}\b")
        self.assertRegex(self.model, r"\bproducto\.nombre\s+as\s+nombre_producto\b")
        self.assertNotRegex(self.model, re.compile(r"\b(?:sum|round|coalesce)\s*\(", re.I))

    def test_project_configures_only_intermediate_schema(self):
        self.assertIn("staging:\n      +schema: staging", self.project)
        self.assertIn("intermediate:\n      +materialized: view\n      +schema: intermediate", self.project)
        self.assertNotIn("marts:\n", self.project)

    def test_schema_declares_grain_relations_and_parent_presence(self):
        self.assertIn("name: int_venta_detalle_enriquecida", self.schema)
        self.assertRegex(self.schema, r"name: id_detalle[\s\S]*?tests: \[not_null, unique\]")
        self.assertIn("to: ref('stg_oltp_venta')", self.schema)
        self.assertIn("to: ref('stg_oltp_producto')", self.schema)
        for column in (
            "fecha",
            "canal",
            "metodo_pago",
            "estado",
            "sku",
            "nombre_producto",
            "id_categoria",
            "id_marca",
            "unidad_medida",
        ):
            self.assertRegex(
                self.schema,
                rf"name: {column}[\s\S]*?tests: \[not_null\]",
            )

    def test_reconciliation_test_is_dynamic_and_returns_only_violations(self):
        sql = self.dbt_tests["int_venta_detalle_reconciliacion.sql"]
        self.assertIn("count(*)", sql)
        self.assertIn("sum(cantidad)", sql)
        self.assertIn("sum(subtotal)", sql)
        self.assertNotIn("3209", sql)
        self.assertIn("where staging.line_count <> intermediate.line_count", sql)

    def test_origin_integrity_test_compares_both_directions_and_all_measures(self):
        sql = self.dbt_tests["int_venta_detalle_integridad_origen.sql"]
        self.assertIn("full outer join", sql.lower())
        self.assertIn("is distinct from", sql.lower())
        for column in (
            "id_detalle",
            "id_venta",
            "id_producto",
            "cantidad",
            "precio_unitario",
            "descuento",
            "subtotal",
        ):
            self.assertIn(column, sql)
        self.assertIn("staging.id_detalle is null", sql)
        self.assertIn("intermediate.id_detalle is null", sql)


if __name__ == "__main__":
    unittest.main()
