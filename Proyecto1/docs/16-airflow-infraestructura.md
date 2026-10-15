# Orquestación y validación con Apache Airflow

## Implementación

SG-Food utiliza **Apache Airflow 3.1.0**, `LocalExecutor` y el DAG [`sgfood_elt_integral`](../dags/sgfood_elt_integral.py) para coordinar carga raw, construcción dbt y reconciliación. El servicio `airflow-scheduler` ejecuta tareas; `airflow-dag-processor` procesa definiciones, `airflow-api-server` expone la interfaz y `airflow-init` realiza la migración inicial del metastore PostgreSQL.

La imagen dedicada se define en [`docker/airflow/Dockerfile`](../docker/airflow/Dockerfile) con un entorno virtual para dbt Core `1.11.12`, dbt-postgres `1.10.2` y Psycopg `3.3.6`, aislado del entorno Python de Airflow.

## Flujo del DAG

![Secuencia operativa del DAG](diagramas/02-dag-airflow.svg)

[Editar diagrama en draw.io](diagramas/02-dag-airflow.drawio)

| Orden | Tarea | Función | Condición de éxito |
|---:|---|---|---|
| 1 | `precheck_config` | Verifica variables obligatorias, rutas, ejecutables, directorios de artefactos y acceso a bases | Configuración y conexión válidas |
| 2 | `raw_load` | Ejecuta `etl/raw_loader.py` sobre OLTP y CSV | Carga transaccional completada |
| 3 | `dbt_build_all` | Ejecuta `dbt build` sobre todo el proyecto | Modelos y tests sin error |
| 4 | `integrity_reconciliation` | Contrasta fuentes, raw, relaciones y marts | Sin diferencias que invaliden integridad |
| 5 | `pipeline_success` | Marca el fin satisfactorio de la cadena | Todas las tareas previas correctas |

La dependencia es estrictamente lineal. El DAG define `schedule=None`, `catchup=False`, `max_active_runs=1` y `retries=0`; **no se ejecuta periódicamente ni reintenta fallos automáticamente**.

## Configuración de ejecución

La imagen recibe valores de `.env` a través de Compose, monta `data/`, `etl/`, `sql/`, `dbt/` y `dags/` en solo lectura y mantiene logs y artefactos dbt en volúmenes separados. Para la base de datos se emplean `sgfood_oltp_reader`, `sgfood_raw_loader` y `sgfood_dbt_runner` según el alcance de la tarea; no se versionan secretos. El perfil de dbt reside en `/opt/airflow/dbt-profiles/profiles.yml` y su salida se dirige a `/opt/airflow/dbt-artifacts/`.

Ejecutar desde `Proyecto1/`, con servicios disponibles:

```bash
docker compose --env-file .env exec airflow-scheduler airflow dags trigger sgfood_elt_integral
```

Comprobar los estados mediante la UI local configurada en `AIRFLOW_HOST_PORT` o, con un `RUN_ID` auténtico, el comando indicado en el [manual](17-manual-implementacion.md).

## Evidencias y resultados

Las evidencias [37](../resultados/37-airflow-3c3-primera-ejecucion.txt) y [38](../resultados/38-airflow-3c3-segunda-ejecucion.txt) documentan **dos ejecuciones exitosas**, cada una con las cinco tareas en `success`. dbt construyó **21 modelos** y ejecutó **201 pruebas** en cada corrida: `PASS=222`, `WARN=0`, `ERROR=0`, `SKIP=0`. La reconciliación terminó con código 0.

La [evidencia 39](../resultados/39-airflow-3c3-idempotencia.txt) compara conteos y hashes SHA-256 de **17 objetos** de las fotografías inicial, posterior a la primera y posterior a la segunda ejecución. Esa prueba cubre únicamente los objetos fotografiados. La [evidencia 40](../resultados/40-validacion-consultas-analiticas.txt) reúne las consultas SQL analíticas ejecutadas independientemente.

## Observabilidad y límites

- Las evidencias publicadas son resúmenes de ejecuciones y no una exportación íntegra de los logs de Airflow.
- Los reintentos automáticos y la programación quedan desactivados intencionalmente; es necesario disparar el DAG cuando corresponda.
- Una tarea fallida impide ejecutar las siguientes por dependencia; el análisis de errores se realiza sobre registros del servicio y de dbt.
- No se hicieron pruebas formales de rendimiento, alta disponibilidad ni recuperación ante desastres.
- La reconciliación es de solo lectura y no altera datos para «reparar» discrepancias.
