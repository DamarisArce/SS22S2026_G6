# SG-Food — infraestructura y ejecución Airflow (estado actualizado)

## Estado vigente

La infraestructura y el DAG integral están implementados y validados. Esta sección supersede las afirmaciones históricas de 3B2 que indiquen que el DAG no existía.

Compose define `sgfood-airflow-postgres`, `airflow-init`, `airflow-scheduler`, `airflow-api-server` y `airflow-dag-processor`, con `LocalExecutor`, la imagen `sgfood-airflow:3.1.0-python3.12` y PostgreSQL 16.15 para el metastore. `airflow-init` ejecuta `airflow db migrate`; los demás servicios dependen de su finalización. Solo el API server publica `127.0.0.1:${AIRFLOW_HOST_PORT}:8080`. El código y datos se montan de solo lectura; logs, artefactos dbt y autenticación usan volúmenes separados.

El DAG `sgfood_elt_integral` usa `schedule=None`, `catchup=False`, `max_active_runs=1` y `retries=0`. La programación es opcional/recomendada por el PDF, por lo que `schedule=None` no es incumplimiento obligatorio. Sus cinco tareas y dependencias son:

```text
precheck_config >> raw_load >> dbt_build_all >> integrity_reconciliation >> pipeline_success
```

`precheck_config` valida configuración, rutas, ejecutables, artefactos y conexiones; `raw_load` ejecuta `etl/raw_loader.py`; `dbt_build_all` ejecuta `dbt build` con el proyecto y perfil montados; `integrity_reconciliation` ejecuta la reconciliación; `pipeline_success` es el marcador terminal.

La imagen instala dbt Core 1.11.12, dbt-postgres 1.10.2 y Psycopg 3.3.6 en `/opt/airflow/sgfood-venv`. Las conexiones usan `.env`, perfiles dbt y los roles `sgfood_oltp_reader`, `sgfood_raw_loader` y `sgfood_dbt_runner`; no se registran secretos.

## Evidencias 3C3

`resultados/37-airflow-3c3-primera-ejecucion.txt` y `resultados/38-airflow-3c3-segunda-ejecucion.txt` documentan dos DAG runs exitosos. Cada ejecución tiene las cinco tareas en `success`; dbt ejecuta 21 modelos y 201 pruebas con `PASS=222`, `WARN=0`, `ERROR=0`, `SKIP=0`, `NO-OP=0`, `TOTAL=222`, código 0; la reconciliación termina con código 0.

`resultados/39-airflow-3c3-idempotencia.txt` compara baseline, primera y segunda fotografía para exactamente 17 objetos. Los conteos y SHA-256 son iguales. Esto sustenta idempotencia observacional de esos datos fotografiados; no demuestra inmutabilidad de toda la infraestructura, volúmenes ni objetos fuera de las fotografías.

## Riesgos y limitaciones vigentes

La ejecución es manual y los retries están deshabilitados. Las evidencias son resúmenes y no logs completos. Las consultas analíticas se validaron en `resultados/40` con 12 bloques y 16 SELECT efectivos. La reconciliación es de solo lectura y cubre contenido OLTP/raw/CSV, claves, relaciones, hechos, cobertura dimensional, enriquecimiento e inventario/devoluciones. El DDL exportado no fue restaurado sobre una base limpia; la exportación fue validada estáticamente.

Registro histórico del cierre 3B2. La construcción de la imagen, la inicialización del metastore y la operación básica quedaron aprobadas en ese bloque; el estado vigente del DAG y las ejecuciones está documentado en las secciones anteriores.

Imagen validada: `sgfood-airflow:3.1.0-python3.12`.

## Contexto previo 3B1

La construcción anterior intentó instalar Airflow y SG-Food en el mismo
Python. El primer conflicto confirmado fue de `click`: `dbt-core==1.11.12`
requiere `click>=8.3.0,<9.0`, mientras los constraints de Airflow 3.1.0 para
Python 3.12 fijan `click==8.2.1`.

## Corrección controlada 3B2 — aislamiento de dependencias

El segundo intento confirmó además dos incompatibilidades en el entorno
compartido: `opentelemetry-exporter-prometheus==0.48b0` requiere
`opentelemetry-sdk~=1.27.0`, pero quedó instalado `opentelemetry-sdk==1.45.1`;
y `snowflake-snowpark-python==1.39.0` requiere `protobuf>=3.20,<6.32`, pero
quedó instalado `protobuf==6.33.6`. Estos conflictos aparecieron después de
instalar dbt junto con las dependencias de Apache Airflow.

**Decisión:** se abandona la instalación compartida. La separación definitiva
crea `/opt/airflow/sgfood-venv` con `python -m venv`, sin
`--system-site-packages`, y deja allí exclusivamente `psycopg[binary]`, dbt y
sus dependencias fijadas en `docker/airflow/requirements.txt`. El Python
principal conserva la instalación de la imagen oficial de Airflow y sus
dependencias originales; no se instala `apache-airflow` dentro del virtualenv.

La preparación conserva propietario `airflow`, grupo `0` y permisos de grupo
compatibles con el UID configurable. Las rutas que deberá usar el DAG futuro
son:

- Loader: `/opt/airflow/sgfood-venv/bin/python`
- dbt: `/opt/airflow/sgfood-venv/bin/dbt`

El DAG no formaba parte del alcance de ese bloque histórico. Los checks de `pip` son separados para
el entorno principal y SG-Food, y el Dockerfile usa rutas absolutas para todas
las comprobaciones del virtualenv.

**Comprobado:** el tercer intento produjo un build exitoso, ambos entornos
superaron `pip check` y la verificación aislada de la imagen fue aprobada.

## Evidencia operativa recibida para 3B2

El tercer build fue exitoso con Airflow 3.1.0, Python 3.12, dbt-core 1.11.12,
dbt-postgres 1.10.2 y psycopg 3.3.6. `pip check` quedó aprobado tanto en el
entorno principal como en el virtualenv aislado de SG-Food.

Los dos builds anteriores fallaron primero por el conflicto de `click`, y
después por conflictos de OpenTelemetry y protobuf en el entorno compartido.

El metastore PostgreSQL 16.15 quedó migrado correctamente: hay 50 tablas en
`public`, `alembic_version` está presente con una fila de versión y
`airflow db check-migrations` fue aprobado.

La primera prueba de Airflow falló porque `print()` dejó un salto de línea al
final de la URI. La corrección cambió esa escritura por `sys.stdout.write()`.
Después quedaron aprobados `SELECT 1` mediante SQLAlchemy y `airflow db check`.

La corrección aplicada conserva la URI, el driver, el host, el puerto, la base
de datos y la codificación `quote(..., safe='')`, y cambia únicamente la
escritura a stdout por `sys.stdout.write(...)`, sin agregar un salto explícito.
La URI se genera sin registrar credenciales ni contenidos sensibles.

**Comprobado:** el precheck confirmó la rama `feature/proyecto1-sgfood-elt`,
HEAD `f7ee83b5bf8f42b97fca494c2a3f41ba0fd4c112`, exactamente dos archivos
modificados y cinco nuevos, sin cambios preparados. La extensión
`x-airflow-common` ahora es superior
a `services`; los tres PostgreSQL conservan su configuración funcional.

**Comprobado:** el Dockerfile instala los requirements únicamente con
`/opt/airflow/sgfood-venv/bin/python`, después de `USER airflow`, y ejecuta
checks separados: `python -m pip check` para Airflow y
`/opt/airflow/sgfood-venv/bin/python -m pip check` para SG-Food. La ejecución
de ambos checks quedó aprobada en el build del tercer intento. También deja
preparados `dbt-artifacts`, `target`, `logs`, `auth` y el virtualenv con
propietario `airflow`, grupo `0` y permisos de grupo de lectura, escritura y
ejecución.

**Comprobado:** `airflow-api-server` pertenece a `sgfood_elt_net` y
`sgfood_access_net`; los otros tres servicios Airflow solo pertenecen a
`sgfood_elt_net`. El metastore no publica puerto ni pertenece a
`sgfood_access_net`. La interfaz conserva el puerto parametrizado en
`127.0.0.1`.

**Comprobado:** la configuración común fija
`AIRFLOW__CORE__EXECUTION_API_SERVER_URL` en
`http://airflow-api-server:8080/execution/`, comparte
`AIRFLOW__API_AUTH__JWT_SECRET`, `AIRFLOW__API__SECRET_KEY` y una
`AIRFLOW__CORE__FERNET_KEY`, y define las rutas dbt bajo
`/opt/airflow/dbt-artifacts/`. El montaje `./dbt` sigue siendo de solo lectura.
Los healthchecks usan `/api/v2/monitor/health` para el API server y
`airflow jobs check --job-type SchedulerJob --local` para scheduler.

**Comprobado:** el metastore usa `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN_CMD` y
`urllib.parse.quote` para codificar usuario, contraseña y base de datos. Esto
evita que `@`, `:`, `/`, `#` o `%` rompan la URI sin exponer secretos.

**Comprobado:** `.env.example` contiene únicamente placeholders para
JWT, API secret y Fernet; deben sustituirse localmente por valores aleatorios
y persistentes, iguales entre componentes. El DAG y sus archivos de soporte se
montan desde `./dags`.

**Comprobado:** el API server, scheduler, DAG processor y PostgreSQL del
metastore quedaron saludables; el DAG processor mostró heartbeat `healthy` y
`localhost:18080` respondió HTTP 200. El heartbeat no se interpreta como un
healthcheck Docker adicional.

**Comprobado:** `etl`, `data`, `sql`, `dbt` y `dags` fueron verificados en solo
lectura; `logs`, `dbt-artifacts`, `target`, logs de dbt y autenticación fueron
verificados como escribibles. Simple Auth Manager quedó configurado, con
archivo de contraseñas `0600`, directorio `0700` y permisos persistentes tras
reiniciar el API server.

**Comprobado en 3B2:** el directorio `dags` fue creado y el baseline de errores de importación fue 0. El DAG integral se implementó posteriormente y está validado en las evidencias 37 y 38.

**Fuentes oficiales:** [configuración Airflow
3.1.0](https://airflow.apache.org/docs/apache-airflow/3.1.0/configurations-ref.html)
y [healthchecks Airflow](https://airflow.apache.org/docs/apache-airflow/3.1.2/administration-and-deployment/logging-monitoring/check-health.html).

## Precheck

Comprobado en la revisión: rama `feature/proyecto1-sgfood-elt`, HEAD
`f7ee83b5bf8f42b97fca494c2a3f41ba0fd4c112`, estado Git con los cambios
preexistentes del bloque y sin archivos preparados,
`compose.yaml`, `requirements-etl.txt`, `requirements-dbt.txt` y
`dbt/profiles.example.yml` existentes. No había servicios Airflow de
aplicación previos; ya existía el metastore `sgfood-airflow-postgres`, que se
reutiliza sin cambiar su configuración.

## Versiones y compatibilidad investigada

La propuesta fija Python 3.12, Apache Airflow 3.1.0 y la imagen oficial
`apache/airflow:3.1.0-python3.12`. Durante la investigación se consultó el
constraint oficial
`https://raw.githubusercontent.com/apache/airflow/constraints-3.1.0/constraints-3.12.txt`,
pero ese archivo no se aplica en el Dockerfile definitivo: Airflow 3.1.0
procede de la imagen oficial, mientras dbt y Psycopg se instalan en
`/opt/airflow/sgfood-venv`.
Airflow 3.1 documenta scheduler, DAG processor, web/API server y metastore
como componentes requeridos, y confirma que LocalExecutor es apropiado para
una instalación básica. PostgreSQL 16 está dentro de las versiones soportadas.

Las versiones del proyecto quedan fijadas: `dbt-core==1.11.12`,
`dbt-postgres==1.10.2`, `psycopg[binary]==3.3.6` y sus dependencias directas
existentes. Los metadatos publicados indican Python mínimo 3.10 para estos
paquetes y rangos de dependencias compatibles entre dbt-core y dbt-postgres.
Esto fue una auditoría de metadatos; la resolución e instalación conjunta quedó
validada en el build exitoso del tercer intento.

Fuentes oficiales revisadas: [Airflow 3.1 architecture](https://airflow.apache.org/docs/apache-airflow/3.1.0/core-concepts/overview.html),
[Airflow constraints](https://raw.githubusercontent.com/apache/airflow/constraints-3.1.0/constraints-3.12.txt),
[Airflow Docker images](https://airflow.apache.org/docs/docker-stack/build.html),
[Airflow database setup](https://airflow.apache.org/docs/apache-airflow/3.1.0/howto/set-up-database.html),
[dbt-core 1.11.12 metadata](https://pypi.org/pypi/dbt-core/1.11.12/json),
[dbt-postgres 1.10.2 metadata](https://pypi.org/pypi/dbt-postgres/1.10.2/json) y
[psycopg 3.3.6 metadata](https://pypi.org/project/psycopg/3.3.6/).

## Arquitectura y redes

Se añaden `airflow-init`, `airflow-scheduler`, `airflow-api-server` y
`airflow-dag-processor`, todos sobre la imagen personalizada y
`LocalExecutor`. `airflow-init` espera el healthcheck del metastore y ejecuta
`airflow db migrate`; los demás esperan su finalización exitosa. No se añaden
CeleryExecutor, Redis, workers, Kubernetes ni Docker socket.

Los servicios Airflow usan `sgfood_elt_net`; únicamente `airflow-api-server`
se conecta además a `sgfood_access_net` y es el único servicio AIRFLOW que
publica un puerto al host, en `127.0.0.1:${AIRFLOW_HOST_PORT}`. OLTP y DW
conservan sus publicaciones existentes en localhost, además de sus nombres,
redes, volúmenes, healthchecks y límites. Las conexiones internas usan DNS
Docker y puerto 5432; el metastore no tiene puerto publicado.

## Rutas, dbt y secretos

El código `etl/`, datos `data/`, SQL `sql/`, proyecto `dbt/` y DAGs se montan
de solo lectura. Logs Airflow, artefactos dbt y el archivo de autenticación se
persisten en volúmenes separados. La imagen copia
`dbt/profiles.example.yml` como `profiles.yml`; la contraseña continúa siendo
`env_var('SGFOOD_DBT_RUNNER_PASSWORD')` y no se versiona.

Variables necesarias: las variables PostgreSQL existentes, los tres
secretos de roles ELT existentes, `AIRFLOW_HOST_PORT`, `AIRFLOW_UI_USER` y
opcionalmente `AIRFLOW_UID`, más placeholders locales para secretos Airflow.
No se agregan valores reales. El Simple Auth Manager genera la contraseña de
interfaz en ejecución y la guarda en el volumen de autenticación; no se crea un
usuario con contraseña hardcodeada ni se usa `airflow/airflow`. En la revisión
operativa actual, el archivo de autenticación conserva permisos `0600`, el
directorio conserva permisos `0700` y ambos estados persistieron después de
reiniciar el API server. La regeneración del archivo o del volumen todavía no
fue comprobada.

## Preservación dbt y loader

La inspección conserva 21 modelos SQL, 12 fuentes y 42 tests SQL singulares;
la línea base del proyecto declara 201 tests dbt. Los tres esquemas analíticos,
el macro `generate_schema_name` y el rol `sgfood_dbt_runner` no se modifican.
`target/` y `logs/` no se escriben sobre el montaje de código fuente.

`raw_loader.py` no fue modificado. Su entrada es `etl/raw_loader.py`; acepta
configuración del entorno y opcionalmente un `--env-file`, devuelve error sin
detalles sensibles si falta configuración y resuelve por defecto `data/` y
`sql/` desde la raíz del proyecto. El contenedor suministra los hosts Docker
por entorno, por lo que no depende de `.env` real ni de `127.0.0.1` para bases
internas.

## Cierre, riesgos y límites

La construcción de la imagen, la inicialización del metastore y la operación básica quedaron aprobadas en 3B2. El pipeline ELT se validó posteriormente mediante Airflow en las evidencias 37 y 38. Las consultas analíticas asociadas se validaron de forma independiente en [resultados/40](../resultados/40-validacion-consultas-analiticas.txt), sin volver a ejecutar el DAG.

No se ha probado recrear el volumen de autenticación ni regenerar su archivo. Tampoco se ha restaurado `sql/06-ddl-dw-reproducible.sql` sobre una base limpia; la exportación está validada estáticamente. `sql/04-ddl-dw.sql` es contractual y las vistas de staging, intermediate y marts siguen siendo propiedad operativa de dbt, no tablas físicas con constraints PostgreSQL.
Las pruebas de rendimiento y recuperación operativa quedan fuera de 3B2; las dos ejecuciones consecutivas del DAG están documentadas en las evidencias 37 y 38.

El heartbeat `healthy` del DAG processor no se documenta como un healthcheck
Docker si no está configurado como tal. No se documentan contraseñas, tokens,
JWT, Fernet ni contenidos sensibles de logs.
