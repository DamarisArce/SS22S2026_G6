import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DBT = ROOT / "dbt"
MODEL = DBT / "models" / "intermediate" / "int_ventas_mensuales_sucursal.sql"
SCHEMA = DBT / "models" / "intermediate" / "schema.yml"
TESTS = DBT / "tests"


class DbtSalesMonthlyContractTest(unittest.TestCase):
    def setUp(self):
        self.model = MODEL.read_text()
        self.schema = SCHEMA.read_text()
        self.dbt_tests = {
            name: (TESTS / name).read_text()
            for name in (
                "int_ventas_mensuales_sucursal_clave_unica.sql",
                "int_ventas_mensuales_sucursal_reconciliacion.sql",
                "int_ventas_mensuales_sucursal_periodo.sql",
            )
        }

    def test_model_exists_and_uses_exactly_the_authorized_ref(self):
        self.assertTrue(MODEL.is_file())
        refs = re.findall(r"\{\{\s*ref\('([^']+)'\)\s*\}\}", self.model)
        self.assertEqual(refs, ["int_venta_detalle_enriquecida"])

    def test_model_has_month_branch_grain_and_measures(self):
        self.assertRegex(
            self.model,
            r"date_trunc\('month',\s*fecha\)::date\s+as\s+periodo",
        )
        self.assertRegex(self.model, r"group\s+by\s+periodo\s*,\s*id_sucursal")
        for expression in (
            "count(*) as lineas_registradas",
            "count(distinct id_venta) as ventas_distintas_registradas",
            "sum(cantidad) as cantidad_registrada",
            "sum(subtotal) as subtotal_registrado",
        ):
            self.assertIn(expression, self.model.lower())

    def test_distinct_venta_is_only_the_distinct_measure(self):
        self.assertEqual(
            len(re.findall(r"count\s*\(\s*distinct\s+id_venta\s*\)", self.model, re.I)),
            1,
        )
        self.assertNotRegex(self.model, re.compile(r"select\s+distinct|\bdistinct\s+on", re.I))

    def test_model_has_no_joins_or_commercial_filters(self):
        self.assertNotRegex(self.model, re.compile(r"\bjoin\b|\bwhere\b|\bhaving\b", re.I))
        self.assertNotRegex(
            self.model,
            re.compile(
                r"metas|promociones|proveedores|devoluciones|descuento|costo|"
                r"venta\s*neta|netas|margen|cumplimiento|porcentaje",
                re.I,
            ),
        )
        self.assertNotRegex(self.model, re.compile(r"\b(?:current_date|now)\s*\(", re.I))

    def test_schema_adds_new_grain_measures_and_relationship(self):
        self.assertIn("name: int_ventas_mensuales_sucursal", self.schema)
        for column in (
            "periodo",
            "id_sucursal",
            "lineas_registradas",
            "ventas_distintas_registradas",
            "cantidad_registrada",
            "subtotal_registrado",
        ):
            self.assertRegex(
                self.schema,
                rf"name: {column}[\s\S]*?tests: \[not_null\]",
            )
        self.assertIn("to: ref('stg_oltp_sucursal')", self.schema)
        for model_name in (
            "int_venta_detalle_enriquecida",
            "int_inventario_snapshot",
            "int_devoluciones_enriquecida",
        ):
            self.assertIn(f"name: {model_name}", self.schema)

    def test_singular_tests_are_declared(self):
        self.assertEqual(
            sorted(self.dbt_tests),
            [
                "int_ventas_mensuales_sucursal_clave_unica.sql",
                "int_ventas_mensuales_sucursal_periodo.sql",
                "int_ventas_mensuales_sucursal_reconciliacion.sql",
            ],
        )

    def test_key_and_period_tests_enforce_dynamic_grain(self):
        key_test = self.dbt_tests["int_ventas_mensuales_sucursal_clave_unica.sql"]
        self.assertIn("group by periodo, id_sucursal", key_test.lower())
        self.assertIn("having count(*) > 1", key_test.lower())

        period_test = self.dbt_tests["int_ventas_mensuales_sucursal_periodo.sql"]
        self.assertIn("date_trunc('month', periodo)::date", period_test.lower())
        self.assertIn("full outer join", period_test.lower())
        self.assertNotRegex(period_test, re.compile(r"\b(?:8|6|48)\b"))

    def test_reconciliation_is_bidirectional_dynamic_and_null_safe(self):
        sql = self.dbt_tests["int_ventas_mensuales_sucursal_reconciliacion.sql"]
        self.assertGreaterEqual(sql.lower().count("full outer join"), 1)
        for expression in (
            "count(*)",
            "count(distinct id_venta)",
            "sum(cantidad)",
            "sum(subtotal)",
            "is distinct from",
        ):
            self.assertIn(expression, sql.lower())
        self.assertNotIn("3209", sql)
        self.assertNotRegex(sql, re.compile(r"\b(?:8|6|48)\b"))


if __name__ == "__main__":
    unittest.main()
