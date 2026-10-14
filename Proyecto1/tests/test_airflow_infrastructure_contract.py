import re
import shlex
import subprocess
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


class AirflowInfrastructureContractTest(unittest.TestCase):
    def setUp(self):
        self.compose = (ROOT / "compose.yaml").read_text()
        self.env = (ROOT / ".env.example").read_text()
        self.dockerfile = (ROOT / "docker/airflow/Dockerfile").read_text()
        self.requirements = (ROOT / "docker/airflow/requirements.txt").read_text()

    def test_required_files_and_fixed_image(self):
        for path in (ROOT / "compose.yaml", ROOT / "requirements-etl.txt",
                     ROOT / "requirements-dbt.txt", ROOT / "dbt/profiles.example.yml"):
            self.assertTrue(path.is_file(), path)
        self.assertIn("FROM apache/airflow:3.1.0-python3.12", self.dockerfile)
        self.assertNotIn(":latest", self.dockerfile + self.compose)

    def test_airflow_components_and_local_executor(self):
        for service in ("airflow-init:", "airflow-scheduler:", "airflow-api-server:",
                        "airflow-dag-processor:"):
            self.assertIn(service, self.compose)
        self.assertIn("AIRFLOW__CORE__EXECUTOR: LocalExecutor", self.compose)
        self.assertIn("command: airflow db migrate", self.compose)
        self.assertIn("service_completed_successfully", self.compose)
        self.assertNotRegex(self.compose, r"(?i)celeryexecutor|redis|privileged|docker\.sock")
        self.assertIn("x-airflow-common: &airflow-common", self.compose.split("services:", 1)[0])
        self.assertNotIn("  x-airflow-common:", self.compose.split("services:", 1)[1])
        self.assertIn("AIRFLOW__CORE__EXECUTION_API_SERVER_URL: http://airflow-api-server:8080/execution/", self.compose)
        self.assertIn("/api/v2/monitor/health", self.compose)
        self.assertIn("airflow", self.compose.split("airflow-scheduler:", 1)[1].split("airflow-api-server:", 1)[0])

    def test_networks_routes_and_isolated_metadata(self):
        for name in ("sgfood_elt_net", "sgfood_access_net", "sgfood-airflow-postgres"):
            self.assertIn(name, self.compose)
        for mount in ("./etl:/opt/airflow/etl:ro", "./data:/opt/airflow/data:ro",
                      "./sql:/opt/airflow/sql:ro", "./dbt:/opt/airflow/dbt:ro",
                      "./dags:/opt/airflow/dags:ro",
                      "sgfood_elt_airflow_logs:/opt/airflow/logs",
                      "sgfood_elt_dbt_artifacts:/opt/airflow/dbt-artifacts"):
            self.assertIn(mount, self.compose)
        self.assertIn("DBT_ENGINE_TARGET_PATH: /opt/airflow/dbt-artifacts/target", self.compose)
        self.assertIn("DBT_ENGINE_LOG_PATH: /opt/airflow/dbt-artifacts/logs", self.compose)
        self.assertIn('127.0.0.1:${AIRFLOW_HOST_PORT', self.compose)
        common = self.compose.split("services:", 1)[0]
        self.assertRegex(common, r"networks:\n\s+- sgfood_elt_net\n")
        self.assertNotIn("sgfood_access_net", common)
        metastore = self.compose.split("  sgfood-airflow-postgres:", 1)[1].split("  airflow-init:", 1)[0]
        self.assertNotIn("ports:", metastore)
        self.assertIn("    networks:\n      - sgfood_elt_net", metastore)
        self.assertNotIn("sgfood_access_net", metastore)
        airflow_services = {
            "airflow-init": self.compose.split("  airflow-init:", 1)[1].split("  airflow-scheduler:", 1)[0],
            "airflow-scheduler": self.compose.split("  airflow-scheduler:", 1)[1].split("  airflow-api-server:", 1)[0],
            "airflow-api-server": self.compose.split("  airflow-api-server:", 1)[1].split("  airflow-dag-processor:", 1)[0],
            "airflow-dag-processor": self.compose.split("  airflow-dag-processor:", 1)[1].split("\nnetworks:\n", 1)[0],
        }
        for service in ("airflow-init", "airflow-scheduler", "airflow-dag-processor"):
            self.assertNotIn("sgfood_access_net", airflow_services[service])
        self.assertRegex(
            airflow_services["airflow-api-server"],
            r"networks:\n\s+- sgfood_elt_net\n\s+- sgfood_access_net",
        )
        self.assertEqual(
            len(re.findall("sgfood_access_net", airflow_services["airflow-api-server"])), 1
        )
        self.assertIn("POSTGRES_OLTP_HOST: sgfood-oltp-postgres", self.compose)
        self.assertIn("POSTGRES_DW_HOST: sgfood-dw-postgres", self.compose)
        services = self.compose.split("services:", 1)[1].split("\nnetworks:\n", 1)[0]
        self.assertEqual(
            set(re.findall(r"^  ([a-z0-9-]+):$", services, re.MULTILINE)),
            {"sgfood-oltp-postgres", "sgfood-dw-postgres", "sgfood-airflow-postgres",
             "airflow-init", "airflow-scheduler", "airflow-api-server",
             "airflow-dag-processor"},
        )
        networks = self.compose.split("\nnetworks:\n", 1)[1].split("\nvolumes:\n", 1)[0]
        self.assertEqual(set(re.findall(r"^  ([a-z0-9_]+):$", networks, re.MULTILINE)),
                         {"sgfood_elt_net", "sgfood_access_net"})
        volumes = self.compose.split("\nvolumes:\n", 1)[1]
        self.assertEqual(
            set(re.findall(r"^  ([a-z0-9_]+):$", volumes, re.MULTILINE)),
            {"sgfood_elt_oltp_data", "sgfood_elt_dw_data", "sgfood_elt_airflow_data",
             "sgfood_elt_airflow_logs", "sgfood_elt_dbt_artifacts",
             "sgfood_elt_airflow_auth"},
        )

    def test_versions_and_secret_boundaries(self):
        for requirement in ("psycopg[binary]==3.3.6", "dbt-core==1.11.12",
                            "dbt-postgres==1.10.2", "dbt-adapters==1.22.10",
                            "dbt-common==1.37.5", "dbt-extractor==0.6.0",
                            "dbt-semantic-interfaces==0.9.0"):
            self.assertIn(requirement, self.requirements)
        self.assertIn("SGFOOD_DBT_RUNNER_PASSWORD", (ROOT / "dbt/profiles.example.yml").read_text())
        self.assertNotRegex(self.dockerfile + self.compose + self.env,
                            r"(?i)(airflow/airflow|password\s*[:=]\s*['\"]?(airflow|admin))")
        self.assertIn("REPLACE_WITH_LOCAL_AIRFLOW_SECRET", self.env)
        for variable in ("AIRFLOW__API_AUTH__JWT_SECRET", "AIRFLOW__API__SECRET_KEY",
                         "AIRFLOW__CORE__FERNET_KEY"):
            self.assertIn(variable, self.compose)
        for placeholder in ("AIRFLOW_JWT_SECRET=REPLACE_WITH_",
                            "AIRFLOW_API_SECRET_KEY=REPLACE_WITH_",
                            "AIRFLOW_FERNET_KEY=REPLACE_WITH_"):
            self.assertIn(placeholder, self.env)
        self.assertIn("AIRFLOW__DATABASE__SQL_ALCHEMY_CONN_CMD", self.compose)
        self.assertIn("quote(os.environ['POSTGRES_AIRFLOW_PASSWORD']", self.compose)
        self.assertNotIn("${POSTGRES_AIRFLOW_USER}:${POSTGRES_AIRFLOW_PASSWORD}@", self.compose)
        self.assertNotRegex(
            self.compose,
            r"(?im)^\s*AIRFLOW__(?:API_AUTH__JWT_SECRET|API__SECRET_KEY|CORE__FERNET_KEY):\s+(?!\$)",
        )

    def test_metastore_uri_generator_writes_exact_stdout(self):
        match = re.search(
            r"AIRFLOW__DATABASE__SQL_ALCHEMY_CONN_CMD:\s+>-\n\s+(.+)",
            self.compose,
        )
        self.assertIsNotNone(match)
        command = match.group(1)
        self.assertIn("import sys", command)
        self.assertIn("sys.stdout.write(", command)
        self.assertNotIn("print(", command)
        self.assertIn("quote(os.environ['POSTGRES_AIRFLOW_USER'], safe='')", command)
        self.assertIn("quote(os.environ['POSTGRES_AIRFLOW_PASSWORD'], safe='')", command)
        self.assertIn("quote(os.environ['POSTGRES_AIRFLOW_DB'], safe='')", command)

        source = {
            "POSTGRES_AIRFLOW_USER": "user@fake",
            "POSTGRES_AIRFLOW_PASSWORD": "p@ss:w/rd#%",
            "POSTGRES_AIRFLOW_DB": "airflow_db",
        }
        result = subprocess.run(
            shlex.split(command),
            check=True,
            capture_output=True,
            text=True,
            env=source,
        )
        self.assertEqual(result.stderr, "")
        self.assertNotRegex(result.stdout, r"[\r\n]$")
        self.assertEqual(
            unquote(urlsplit(result.stdout).path.lstrip("/")),
            source["POSTGRES_AIRFLOW_DB"],
        )
        self.assertEqual(
            result.stdout,
            "postgresql+psycopg2://user%40fake:p%40ss%3Aw%2Frd%23%25@"
            "sgfood-airflow-postgres:5432/airflow_db",
        )

    def test_airflow_and_sgfood_dependency_isolation(self):
        self.assertEqual(self.dockerfile.count("FROM apache/airflow:3.1.0-python3.12"), 1)
        self.assertIn("/opt/airflow/sgfood-venv", self.dockerfile)
        self.assertIn("python -m venv /opt/airflow/sgfood-venv", self.dockerfile)
        self.assertNotIn("--system-site-packages", self.dockerfile)
        self.assertIn(
            "/opt/airflow/sgfood-venv/bin/python -m pip install --no-cache-dir",
            self.dockerfile,
        )
        self.assertIn("-r /tmp/sgfood-airflow-requirements.txt", self.dockerfile)
        self.assertNotIn('"apache-airflow==${AIRFLOW_VERSION}"', self.dockerfile)
        self.assertNotIn("--constraint", self.dockerfile)
        self.assertIn('test "$(airflow version)" = "${AIRFLOW_VERSION}"', self.dockerfile)
        self.assertIn("python -m pip check", self.dockerfile)
        self.assertIn("/opt/airflow/sgfood-venv/bin/python -m pip check", self.dockerfile)
        self.assertIn("/opt/airflow/sgfood-venv/bin/dbt --version", self.dockerfile)
        self.assertIn("/opt/airflow/sgfood-venv/bin/python -c", self.dockerfile)
        self.assertIn("import psycopg", self.dockerfile)
        self.assertIn("USER airflow", self.dockerfile)
        self.assertIn("USER root", self.dockerfile)
        self.assertNotIn("chmod 777", self.dockerfile)
        for directory in (
            "/opt/airflow/dbt-artifacts",
            "/opt/airflow/dbt-artifacts/target",
            "/opt/airflow/dbt-artifacts/logs",
            "/opt/airflow/auth",
            "/opt/airflow/sgfood-venv",
        ):
            self.assertIn(directory, self.dockerfile)
        self.assertIn("chown -R airflow:0", self.dockerfile)
        self.assertIn("chmod -R g+rwX", self.dockerfile)
        self.assertLess(self.dockerfile.index("USER root"), self.dockerfile.index("python -m venv"))
        self.assertLess(
            self.dockerfile.index("USER airflow"),
            self.dockerfile.index("/opt/airflow/sgfood-venv/bin/python -m pip install"),
        )

    def test_dockerfile_does_not_change_networks_or_services(self):
        self.assertNotIn("network", self.dockerfile.lower())
        self.assertNotIn("services:", self.dockerfile.lower())
        self.assertNotRegex(self.dockerfile, r"(?i)(password|secret|token|private.key)")

    def test_db_assets_and_source_inventory_are_unchanged(self):
        self.assertEqual(len(list((ROOT / "dbt/models").glob("**/*.sql"))), 21)
        sources = re.findall(r"^      - name: ([a-z0-9_]+)$",
                             (ROOT / "dbt/models/sources.yml").read_text(), re.MULTILINE)
        self.assertEqual(len(sources), 12)
        self.assertEqual(len(list((ROOT / "dbt/tests").glob("*.sql"))), 42)


if __name__ == "__main__":
    unittest.main()
