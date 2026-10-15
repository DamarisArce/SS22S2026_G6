"""Manual, strictly sequential SG-Food ELT orchestration."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.python import PythonOperator
from airflow.sdk import DAG


REQUIRED_ENV = (
    "POSTGRES_OLTP_DB", "POSTGRES_OLTP_HOST", "POSTGRES_OLTP_HOST_PORT",
    "POSTGRES_DW_DB", "POSTGRES_DW_HOST", "POSTGRES_DW_HOST_PORT",
    "SGFOOD_OLTP_READER_PASSWORD", "SGFOOD_RAW_LOADER_PASSWORD",
    "SGFOOD_DBT_RUNNER_PASSWORD", "DBT_PROFILES_DIR",
)
CODE_PATHS = (
    Path("/opt/airflow/etl/raw_loader.py"),
    Path("/opt/airflow/etl/integrity_reconciliation.py"),
    Path("/opt/airflow/dbt/dbt_project.yml"),
    Path("/opt/airflow/dbt-profiles/profiles.yml"),
    Path("/opt/airflow/data"),
)
EXECUTABLES = (
    Path("/opt/airflow/sgfood-venv/bin/python"),
    Path("/opt/airflow/sgfood-venv/bin/dbt"),
)
WRITABLE_PATHS = (
    Path("/opt/airflow/dbt-artifacts/target"),
    Path("/opt/airflow/dbt-artifacts/logs"),
)


def _database_parameters(prefix: str, user: str, password_variable: str) -> dict[str, str]:
    return {
        "host": os.environ[f"{prefix}_HOST"],
        "port": os.environ[f"{prefix}_HOST_PORT"],
        "dbname": os.environ[f"{prefix}_DB"],
        "user": user,
        "password": os.environ[password_variable],
    }


def precheck_config() -> None:
    """Validate configuration and database access in the ETL virtualenv."""
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        raise RuntimeError("missing required Airflow configuration")
    if any(any(marker in os.environ[name].upper() for marker in ("REPLACE_WITH", "CHANGE_ME", "TODO")) for name in REQUIRED_ENV):
        raise RuntimeError("placeholder configuration is not allowed")
    if os.environ["DBT_PROFILES_DIR"] != "/opt/airflow/dbt-profiles":
        raise RuntimeError("unexpected dbt profiles path")
    if any(not path.exists() for path in CODE_PATHS):
        raise RuntimeError("required code or data path is unavailable")
    if any(not path.is_file() or not os.access(path, os.X_OK) for path in EXECUTABLES):
        raise RuntimeError("required executable is unavailable")
    for path in WRITABLE_PATHS:
        if not path.is_dir() or not os.access(path, os.W_OK):
            raise RuntimeError("dbt artifact path is not writable")
        with tempfile.NamedTemporaryFile(dir=path, prefix=".precheck-", delete=True):
            pass

    subprocess.run(
        [
            "/opt/airflow/sgfood-venv/bin/python",
            "/opt/airflow/etl/integrity_reconciliation.py",
            "--precheck",
        ],
        check=True,
    )


def pipeline_success() -> None:
    """Terminal marker; Airflow only schedules it after every upstream task."""
    return None


with DAG(
    dag_id="sgfood_elt_integral",
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 0},
    tags=["sgfood", "elt"],
) as dag:
    precheck = PythonOperator(
        task_id="precheck_config",
        python_callable=precheck_config,
        retries=0,
        do_xcom_push=False,
    )
    raw_load = BashOperator(
        task_id="raw_load",
        bash_command=(
            "/opt/airflow/sgfood-venv/bin/python "
            "/opt/airflow/etl/raw_loader.py "
            "--source-dir /opt/airflow/data "
            "--env-file /dev/null"
        ),
        retries=0,
        do_xcom_push=False,
    )
    dbt_build_all = BashOperator(
        task_id="dbt_build_all",
        bash_command=(
            "/opt/airflow/sgfood-venv/bin/dbt "
            "build "
            "--project-dir /opt/airflow/dbt "
            "--profiles-dir /opt/airflow/dbt-profiles "
            "--target dev "
            "--target-path /opt/airflow/dbt-artifacts/target "
            "--log-path /opt/airflow/dbt-artifacts/logs"
        ),
        retries=0,
        do_xcom_push=False,
    )
    integrity_reconciliation = BashOperator(
        task_id="integrity_reconciliation",
        bash_command=(
            "/opt/airflow/sgfood-venv/bin/python "
            "/opt/airflow/etl/integrity_reconciliation.py"
        ),
        retries=0,
        do_xcom_push=False,
    )
    success = PythonOperator(
        task_id="pipeline_success",
        python_callable=pipeline_success,
        retries=0,
        do_xcom_push=False,
    )

    precheck >> raw_load >> dbt_build_all >> integrity_reconciliation >> success
