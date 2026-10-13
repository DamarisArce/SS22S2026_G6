import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DBT = ROOT / "dbt"

SOURCE_NAMES = [
    "oltp_sucursal",
    "oltp_categoria",
    "oltp_marca",
    "oltp_producto",
    "oltp_cliente",
    "oltp_venta",
    "oltp_venta_detalle",
    "csv_inventario_bodega",
    "csv_devoluciones",
    "csv_metas_ventas",
    "csv_promociones",
    "csv_proveedores_precios",
]


class DbtStagingContractTest(unittest.TestCase):
    def setUp(self):
        self.sources = (DBT / "models" / "sources.yml").read_text()
        self.project = (DBT / "dbt_project.yml").read_text()
        self.profiles = (DBT / "profiles.example.yml").read_text()
        self.period_model = (DBT / "models" / "staging" / "stg_csv_metas_ventas.sql").read_text()
        self.schema = (DBT / "models" / "staging" / "schema.yml").read_text()
        self.docs = (ROOT / "docs" / "06-dbt-staging.md").read_text()
        self.dbt_tests = {
            path.name: path.read_text()
            for path in (DBT / "tests").glob("*.sql")
        }
        self.sql_models = sorted((DBT / "models" / "staging").glob("stg_*.sql"))
        self.sql_text = "\n".join(path.read_text() for path in self.sql_models)

    def test_declares_exactly_the_twelve_raw_sources(self):
        declared = re.findall(r"^      - name: ([a-z0-9_]+)$", self.sources, re.MULTILINE)
        self.assertEqual(declared, SOURCE_NAMES)

    def test_has_one_staging_model_per_source(self):
        expected = {f"stg_{name}.sql" for name in SOURCE_NAMES}
        self.assertEqual({path.name for path in self.sql_models}, expected)

    def test_each_model_uses_source_and_no_select_star(self):
        for path in self.sql_models:
            text = path.read_text()
            self.assertRegex(text, r"\{\{\s*source\('raw',\s*'[a-z0-9_]+'\)\s*\}\}")
            self.assertNotRegex(text, r"select\s+\*", msg=path.name)

    def test_no_model_writes_to_raw_or_reserved_schemas(self):
        forbidden = re.compile(r"\b(insert|update|delete|truncate|drop|create)\b.*\braw\b", re.I | re.S)
        self.assertNotRegex(self.sql_text, forbidden)
        self.assertNotIn("intermediate/", self.project)
        self.assertNotIn("marts/", self.project)

    def test_profiles_use_runner_and_environment_secret(self):
        self.assertIn("user: sgfood_dbt_runner", self.profiles)
        self.assertIn("password: \"{{ env_var('SGFOOD_DBT_RUNNER_PASSWORD') }}\"", self.profiles)
        self.assertIn("host: \"{{ env_var('DBT_HOST', '127.0.0.1') }}\"", self.profiles)
        self.assertIn("dbname: sgfood_dw", self.profiles)
        self.assertIn("schema: staging", self.profiles)
        password_lines = [
            line.strip() for line in self.profiles.splitlines()
            if line.strip().startswith("password:")
        ]
        self.assertTrue(password_lines)
        self.assertTrue(all("env_var(" in line for line in password_lines))
        self.assertNotIn("admin", self.profiles.lower())
        self.assertIn("Proyecto1/.env", self.docs)
        self.assertIn("sin imprimir ni versionar contraseñas", self.docs)

    def test_profiles_have_only_local_dev_and_integer_port(self):
        self.assertIn("target: dev", self.profiles)
        self.assertIn("    dev:", self.profiles)
        self.assertNotIn("    prod:", self.profiles)
        self.assertRegex(self.profiles, r"port: \"\{\{ env_var\('DBT_PORT', '15434'\) \| int \}\}\"")

    def test_month_period_is_explicitly_normalized_to_day_one(self):
        self.assertIn("when nullif(btrim(periodo), '') is null then null", self.period_model)
        self.assertIn("(btrim(periodo) || '-01')::date", self.period_model)
        self.assertIn("YYYY-MM", self.schema)
        self.assertIn("primer día", self.schema)
        self.assertIn("stg_csv_metas_ventas_periodo_format.sql", self.docs)

    def test_period_format_test_rejects_invalid_months(self):
        sql = self.dbt_tests["stg_csv_metas_ventas_periodo_format.sql"]
        self.assertIn("!~", sql)
        self.assertIn("0[1-9]|1[0-2]", sql)
        self.assertIn("^[0-9]{4}-", sql)

    def test_composite_key_tests_cover_nulls_and_duplicates(self):
        keys = {
            "stg_csv_inventario_bodega": ("fecha_corte", "id_sucursal", "id_producto", "lote"),
            "stg_csv_metas_ventas": ("periodo", "id_sucursal"),
            "stg_csv_proveedores_precios": ("id_proveedor", "id_producto", "fecha_vigencia"),
        }
        for model, columns in keys.items():
            not_null = self.dbt_tests[f"{model}_key_not_null.sql"]
            unique = self.dbt_tests[f"{model}_key_unique.sql"]
            for column in columns:
                self.assertIn(f"{column} is null", not_null)
                self.assertIn(column, unique)
            self.assertIn("group by " + ", ".join(columns), unique)
            self.assertIn("having count(*) > 1", unique)

    def test_academic_snapshot_is_optional_and_dynamic_reconciliation_active(self):
        snapshot = self.dbt_tests["source_and_staging_counts.sql"]
        dynamic = self.dbt_tests["staging_row_counts.sql"]
        self.assertIn("config(enabled=var('enable_academic_snapshot', false))", snapshot)
        self.assertNotIn("enable_academic_snapshot", dynamic)
        self.assertIn("8,864", self.docs)
        self.assertIn("deshabilitada por defecto", self.docs)
        self.assertIn("enable_academic_snapshot", self.docs)

    def test_schema_configuration_is_allowlisted_and_exact(self):
        self.assertIn("+schema: staging", self.project)
        macro = (DBT / "macros" / "generate_schema_name.sql").read_text()
        for schema in ("staging", "intermediate", "marts"):
            self.assertIn(f"'{schema}'", macro)
        self.assertNotIn("_staging", macro)


if __name__ == "__main__":
    unittest.main()
