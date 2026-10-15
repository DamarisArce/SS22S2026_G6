# Proyecto 1 — SG-Food ELT

## Identificación

Proyecto académico de Seminario de Sistemas 2, USAC, para diseñar e implementar un flujo reproducible de extracción, carga, transformación, orquestación y validación para SG-Food.

## Integrantes

- Dámaris Magali Arce Guzmán — 202006636
- Nelson Emanuel Cún Bálan — 201222010

## Objetivo y problema

SG-Food necesita integrar una fuente transaccional y archivos operativos para disponer de datos analíticos trazables. El objetivo académico es construir un flujo ELT con Python, Apache Airflow, PostgreSQL y dbt Core que cargue datos raw, construya modelos analíticos y ejecute controles de calidad. El PDF exige extracción/carga Python, orquestación Airflow, DW PostgreSQL, modelos dbt y validación documentada.

## Arquitectura implementada

```text
PostgreSQL OLTP (oltp_sgfood) ─┐
                                ├─ etl/raw_loader.py ─> PostgreSQL DW.raw
CSV en data/ ───────────────────┘                         │
                                      Airflow             v
                              dbt: staging -> intermediate -> marts
                                      │                    │
                         reconciliación y pruebas     consultas/controles
```

`compose.yaml` define `sgfood-oltp-postgres`, `sgfood-dw-postgres`, `sgfood-airflow-postgres`, `airflow-init`, `airflow-scheduler`, `airflow-api-server` y `airflow-dag-processor`. Los tres PostgreSQL usan `postgres:16.15-bookworm`; Airflow usa `apache/airflow:3.1.0-python3.12`, `LocalExecutor` y un virtualenv separado para dbt y Psycopg. Las conexiones internas usan nombres de servicio y puerto 5432; los puertos publicados están limitados a localhost.

## Fuentes y pipeline

El OLTP `data/sgfood_oltp.sql` contiene el schema `oltp_sgfood` y siete tablas: `sucursal`, `categoria`, `marca`, `producto`, `cliente`, `venta` y `venta_detalle`. Los CSV operativos son `inventario_bodega.csv`, `devoluciones.csv`, `metas_ventas.csv`, `promociones.csv` y `proveedores_precios.csv`. El loader administra doce tablas raw: siete OLTP y cinco CSV; valida encabezados, claves naturales, identidades de conexión y contratos de tablas, y carga de forma transaccional.

El DAG `sgfood_elt_integral` tiene `schedule=None` (la programación es opcional/recomendada por el PDF) y ejecuta estrictamente: `precheck_config`, `raw_load`, `dbt_build_all`, `integrity_reconciliation` y `pipeline_success`. Las tareas tienen `retries=0`, `catchup=False` y `max_active_runs=1`.

## PostgreSQL, dbt y modelo dimensional

El DW separa `raw`, `staging`, `intermediate` y `marts`. `raw` contiene 12 tablas físicas; `staging`, `intermediate` y `marts` contienen las 21 vistas administradas por dbt. `marts` contiene `dim_cliente`, `dim_fecha`, `dim_producto`, `dim_sucursal` y `fct_ventas_detalle`. El proyecto dbt declara 12 sources y 201 tests en su inventario; los modelos usan `source()` y `ref()`. La imagen instala dbt Core 1.11.12, dbt-postgres 1.10.2 y Psycopg 3.3.6.

Los entregables DDL tienen alcances distintos: `sql/04-ddl-dw.sql` es el DDL contractual/documental y explica el catálogo sin recrear las vistas dbt; `sql/06-ddl-dw-reproducible.sql` es la exportación estática de esquema obtenida con `pg_dump`, con 12 tablas raw, 21 vistas y 13 constraints físicos raw. `sql/03-create-raw.sql` es el DDL ejecutable de las tablas raw. La exportación no fue restaurada sobre una base limpia en este bloque: `PENDIENTE`.

## Pruebas y validación

Hay contratos Python en `tests/`, tests SQL en `dbt/tests/`, validaciones de permisos y reconciliación independiente en `etl/integrity_reconciliation.py`. Las dos ejecuciones Airflow documentadas terminaron con las cinco tareas en `success`. En ambas, dbt ejecutó 21 modelos y 201 pruebas con `PASS=222`, `WARN=0`, `ERROR=0` y código 0; la reconciliación terminó con código 0.

La evidencia 3C3 comparó tres fotografías para 17 objetos, con igualdad exacta de conteos y SHA-256 por objeto. Esto sustenta idempotencia observacional de esos datos fotografiados; no demuestra inmutabilidad de toda la infraestructura ni de objetos fuera de las fotografías.

Las consultas de `sql/05-consultas-analiticas.sql` se validaron en `resultados/40-validacion-consultas-analiticas.txt`: 12 bloques, 16 SELECT efectivos, sin errores, con integridad referencial y conservación de las 3,209 filas del hecho. Son consultas de conteo, cobertura y valores registrados; no se inventan métricas comerciales.

## Configuración y seguridad

Copiar `.env.example` a `.env` y sustituir localmente sus placeholders por valores aleatorios y persistentes. No versionar `.env` ni imprimir secretos. Las contraseñas se leen desde variables de entorno y el perfil dbt usa `env_var('SGFOOD_DBT_RUNNER_PASSWORD')`.

## Inicio y documentación

Los pasos reproducibles están en [docs/17-manual-implementacion.md](docs/17-manual-implementacion.md). La arquitectura, permisos, carga raw, modelos y decisiones están en `docs/01` a `docs/15`; Airflow está en `docs/16-airflow-infraestructura.md`; la matriz en `docs/00-matriz-requisitos.md`. Entregables SQL: [04](sql/04-ddl-dw.sql), [05](sql/05-consultas-analiticas.sql) y [06](sql/06-ddl-dw-reproducible.sql). Evidencias: [37](resultados/37-airflow-3c3-primera-ejecucion.txt), [38](resultados/38-airflow-3c3-segunda-ejecucion.txt), [39](resultados/39-airflow-3c3-idempotencia.txt) y [40](resultados/40-validacion-consultas-analiticas.txt).

## Estructura actual

```text
Proyecto1/
├── compose.yaml  .env.example
├── dags/  etl/  data/  sql/  scripts/
├── dbt/{models,tests,macros}  docker/  tests/
├── docs/00...17-*.md  resultados/01...40-*.txt
├── sql/03-create-raw.sql  sql/04-ddl-dw.sql
│   sql/05-consultas-analiticas.sql  sql/06-ddl-dw-reproducible.sql
└── insumos/798_Proyecto_1_2S2026.pdf
```

## Limitaciones y pendientes

- El DDL contractual, la exportación reproducible y las consultas analíticas están entregados. R-03 está `VALIDADO` conforme a la interpretación del requisito oficial documentada en la matriz: los modelos dbt son vistas, no existen PK/FK físicas en dichas vistas y la integridad se verificó mediante pruebas dbt. La exportación no fue restaurada sobre una base limpia (`PENDIENTE`).
- La ejecución programada es opcional/recomendada y permanece manual (`schedule=None`).
- La idempotencia documentada se limita a los 17 objetos de las fotografías 3C3.
- La evidencia 40 valida 12 bloques y 16 SELECT efectivos sobre el DW verificado; sus resultados son agregados y no incluyen filas de negocio.
- No se declara dimensión de proveedor, atribución de promociones ni reglas SCD históricas sin decisión de negocio.
- La ejecución independiente de este manual por un tercero queda `PENDIENTE`.
