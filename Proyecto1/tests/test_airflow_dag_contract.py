import ast
import shlex
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DAG_PATH = ROOT / "dags/sgfood_elt_integral.py"


class AirflowDagContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = DAG_PATH.read_text()
        cls.tree = ast.parse(cls.source)

    def test_configuration_and_exact_task_contract(self):
        for value in (
            'dag_id="sgfood_elt_integral"', 'schedule=None', 'catchup=False',
            'max_active_runs=1',
        ):
            self.assertIn(value, self.source)
        task_ids = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"PythonOperator", "BashOperator"}:
                for keyword in node.keywords:
                    if keyword.arg == "task_id" and isinstance(keyword.value, ast.Constant):
                        task_ids.add(keyword.value.value)
        self.assertEqual(task_ids, {"precheck_config", "raw_load", "dbt_build_all", "integrity_reconciliation", "pipeline_success"})

    def test_linear_dependencies_and_commands_are_explicit(self):
        self.assertIn("precheck >> raw_load >> dbt_build_all >> integrity_reconciliation >> success", self.source)
        self.assertIn("/opt/airflow/sgfood-venv/bin/python ", self.source)
        self.assertIn("/opt/airflow/etl/raw_loader.py", self.source)
        self.assertIn("--source-dir /opt/airflow/data", self.source)
        self.assertIn("--env-file /dev/null", self.source)
        self.assertIn("/opt/airflow/sgfood-venv/bin/dbt", self.source)
        self.assertIn("--project-dir /opt/airflow/dbt", self.source)
        self.assertIn("--profiles-dir /opt/airflow/dbt-profiles", self.source)
        self.assertIn("--target-path /opt/airflow/dbt-artifacts/target", self.source)
        self.assertIn("--log-path /opt/airflow/dbt-artifacts/logs", self.source)
        self.assertIn("build ", self.source)
        self.assertIn("--target dev", self.source)
        self.assertIn("/opt/airflow/etl/integrity_reconciliation.py", self.source)

    def test_dbt_build_command_uses_cli_argument_order_and_expected_options(self):
        command = None
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "BashOperator":
                continue
            task_id = next(
                (keyword.value.value for keyword in node.keywords
                 if keyword.arg == "task_id" and isinstance(keyword.value, ast.Constant)),
                None,
            )
            if task_id != "dbt_build_all":
                continue
            command_node = next(keyword.value for keyword in node.keywords if keyword.arg == "bash_command")
            command = ast.literal_eval(command_node)
            break

        self.assertIsNotNone(command)
        tokens = shlex.split(command)
        self.assertEqual(tokens[0], "/opt/airflow/sgfood-venv/bin/dbt")
        self.assertEqual(tokens[1], "build")
        self.assertEqual(tokens[2:], [
            "--project-dir", "/opt/airflow/dbt",
            "--profiles-dir", "/opt/airflow/dbt-profiles",
            "--target", "dev",
            "--target-path", "/opt/airflow/dbt-artifacts/target",
            "--log-path", "/opt/airflow/dbt-artifacts/logs",
        ])
        self.assertFalse(any(token == "--select" or token.startswith("--select=") for token in tokens))
        self.assertFalse(any("password" in token.lower() or "credential" in token.lower() for token in tokens))

    def test_import_has_no_pipeline_execution_or_sensitive_literals(self):
        self.assertNotIn("airflow dags trigger", self.source)
        self.assertNotIn("raw_loader.main(", self.source)
        self.assertNotIn("integrity_reconciliation.main(", self.source)
        self.assertNotIn("docker.sock", self.source)
        self.assertNotIn("REPLACE_WITH_", self.source)
        self.assertNotIn("SGFOOD_OLTP_READER_PASSWORD=", self.source)


if __name__ == "__main__":
    unittest.main()
