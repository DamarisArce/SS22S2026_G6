import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DBT = ROOT / "dbt"
MODEL = DBT / "models" / "marts" / "dim_fecha.sql"
SCHEMA = DBT / "models" / "marts" / "schema.yml"
TESTS = DBT / "tests"

EXPECTED_COLUMNS = (
    "fecha", "anio", "anio_iso", "trimestre", "mes", "dia_mes",
    "dia_semana", "numero_semana", "inicio_mes", "fin_mes",
    "inicio_trimestre", "inicio_anio", "es_fin_semana",
)
EXPECTED_TESTS = {
    "dim_fecha_clave_unica.sql", "dim_fecha_rango_fuentes.sql",
    "dim_fecha_continuidad.sql", "dim_fecha_atributos.sql",
    "dim_fecha_integridad_ventas.sql", "dim_fecha_integridad_periodos.sql",
    "dim_fecha_iso_bisiesto.sql",
}


class DbtMartsDateContractTest(unittest.TestCase):
    def setUp(self):
        self.model = MODEL.read_text()
        self.schema = SCHEMA.read_text()
        self.dbt_tests = {
            path.name: path.read_text()
            for path in TESTS.glob("dim_fecha_*.sql")
        }

    def test_model_exists_with_view_schema_and_exact_refs(self):
        self.assertTrue(MODEL.exists())
        self.assertIn("materialized='view'", self.model)
        self.assertIn("schema='marts'", self.model)
        refs = re.findall(r"\{\{\s*ref\('([^']+)'\)\s*\}\}", self.model)
        self.assertEqual(refs, ["stg_oltp_venta", "int_ventas_mensuales_sucursal"])

    def test_model_has_explicit_columns_and_deterministic_generation(self):
        self.assertNotRegex(self.model, re.compile(r"select\s+\*", re.I))
        self.assertIn("generate_series", self.model)
        self.assertIn("timestamp without time zone", self.model)
        self.assertIn("::date", self.model)
        self.assertIn("union all", self.model.lower())
        for column in EXPECTED_COLUMNS:
            self.assertRegex(self.model, rf"\b{re.escape(column)}\b")
        self.assertNotRegex(
            self.model,
            re.compile(r"\b(current_date|now\s*\(|temporary|recursive)\b", re.I),
        )
        self.assertNotIn("fct_ventas_detalle", self.model)

    def test_model_uses_explicit_types_and_iso_conventions(self):
        for expression in (
            "extract(year", "extract(isoyear", "extract(quarter", "extract(month",
            "extract(day", "extract(isodow", "extract(week", "::integer",
            "::smallint", "::boolean", "date_trunc('month'",
            "date_trunc('quarter'", "date_trunc('year'",
        ):
            self.assertIn(expression, self.model.lower())
        self.assertRegex(
            self.model,
            re.compile(r"extract\(isodow[\s\S]*in\s*\(6,\s*7\)", re.I),
        )

    def test_no_unauthorized_sources_or_business_dates(self):
        self.assertNotRegex(
            self.model,
            re.compile(r"ref\('(?!stg_oltp_venta|int_ventas_mensuales_sucursal)[^']+'\)", re.I),
        )
        self.assertNotRegex(
            self.model,
            re.compile(r"\b(source\s*\(|current_date|now\s*\(|etl|2026)\b", re.I),
        )
        self.assertNotRegex(self.model, re.compile(r"\b(fiscal|holiday|feriado)\b", re.I))

    def test_schema_documents_date_contract_and_thirteen_not_nulls(self):
        self.assertIn("name: dim_fecha", self.schema)
        dimension = self.schema.split("name: dim_fecha", 1)[1]
        self.assertIn("stg_oltp_venta", dimension)
        self.assertIn("int_ventas_mensuales_sucursal", dimension)
        self.assertIn("una fila por día calendario", dimension.lower())
        self.assertIn("gregor", dimension.lower())
        self.assertIn("iso", dimension.lower())
        self.assertIn("fuentes no tienen fechas válidas", dimension.lower())
        self.assertRegex(dimension, r"name: fecha[\s\S]*?tests: \[not_null, unique\]")
        for column in EXPECTED_COLUMNS[1:]:
            self.assertRegex(dimension, rf"name: {re.escape(column)}[\s\S]*?tests: \[not_null\]")

    def test_singular_tests_are_exactly_seven_and_dynamic(self):
        self.assertEqual(set(self.dbt_tests), EXPECTED_TESTS)
        for name, sql in self.dbt_tests.items():
            if name != "dim_fecha_iso_bisiesto.sql":
                self.assertNotRegex(sql, re.compile(r"\b(?:8864|3209|2026)\b", re.I))
                self.assertIn("ref('dim_fecha')", sql)
        self.assertIn("min(fecha)", self.dbt_tests["dim_fecha_rango_fuentes.sql"])
        self.assertIn("max(fecha)", self.dbt_tests["dim_fecha_rango_fuentes.sql"])
        self.assertIn("lead(fecha)", self.dbt_tests["dim_fecha_continuidad.sql"])
        self.assertIn("is distinct from", self.dbt_tests["dim_fecha_atributos.sql"])
        self.assertIn("fct_ventas_detalle", self.dbt_tests["dim_fecha_integridad_ventas.sql"])
        self.assertIn("int_ventas_mensuales_sucursal", self.dbt_tests["dim_fecha_integridad_periodos.sql"])

    def test_integrity_tests_do_not_hide_violations(self):
        sales = self.dbt_tests["dim_fecha_integridad_ventas.sql"]
        self.assertNotRegex(sales, re.compile(r"\bdistinct\b|\bgroup\s+by\b", re.I))
        self.assertIn("left join", sales.lower())
        periods = self.dbt_tests["dim_fecha_integridad_periodos.sql"]
        self.assertIn("date_trunc('month'", periods)
        self.assertNotRegex(periods, re.compile(r"\bgroup\s+by\b", re.I))

    def test_iso_leap_year_fixture_is_deterministic(self):
        sql = self.dbt_tests["dim_fecha_iso_bisiesto.sql"]
        self.assertIn("2021-01-01", sql)
        self.assertIn("2024-02-29", sql)
        self.assertIn("2020::integer", sql)
        self.assertIn("53::smallint", sql)
        self.assertIn("9::smallint as semana_esperada", sql)
        self.assertNotIn("extract(week from date '2024-02-29')", sql)

    def test_previous_marts_are_preserved(self):
        for model_name in ("fct_ventas_detalle", "dim_sucursal", "dim_producto"):
            self.assertRegex(self.schema, rf"name: {model_name}\b")
        self.assertEqual(len(list((DBT / "models" / "marts").glob("*.sql"))), 4)
        self.assertNotRegex(
            self.schema.split("name: dim_fecha", 1)[1],
            re.compile(r"fiscal|feriado|hábil", re.I),
        )


if __name__ == "__main__":
    unittest.main()
