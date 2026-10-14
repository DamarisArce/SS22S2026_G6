FROM apache/airflow:3.1.0-python3.12

ARG AIRFLOW_VERSION=3.1.0
ARG PYTHON_VERSION=3.12
ENV AIRFLOW_HOME=/opt/airflow

COPY docker/airflow/requirements.txt /tmp/sgfood-airflow-requirements.txt
COPY dbt/profiles.example.yml /opt/airflow/dbt-profiles/profiles.yml

USER root

RUN mkdir -p \
        /opt/airflow/dbt-artifacts \
        /opt/airflow/dbt-artifacts/target \
        /opt/airflow/dbt-artifacts/logs \
        /opt/airflow/auth \
        /opt/airflow/sgfood-venv \
    && python -m venv /opt/airflow/sgfood-venv \
    && chown -R airflow:0 \
        /opt/airflow/dbt-artifacts \
        /opt/airflow/auth \
        /opt/airflow/sgfood-venv \
    && chmod -R g+rwX \
        /opt/airflow/dbt-artifacts \
        /opt/airflow/auth \
        /opt/airflow/sgfood-venv

USER airflow

RUN /opt/airflow/sgfood-venv/bin/python -m pip install --no-cache-dir \
    -r /tmp/sgfood-airflow-requirements.txt

RUN test "$(airflow version)" = "${AIRFLOW_VERSION}" \
    && python -m pip check

RUN /opt/airflow/sgfood-venv/bin/python -m pip check \
    && /opt/airflow/sgfood-venv/bin/dbt --version \
    && /opt/airflow/sgfood-venv/bin/python -c \
        "import importlib.metadata as m; import psycopg; \
         assert m.version('dbt-core') == '1.11.12'; \
         assert m.version('dbt-postgres') == '1.10.2'; \
         assert m.version('psycopg') == '3.3.6'; \
         assert psycopg.__version__.startswith('3.3.6')"
