# Manual de instalación, configuración y ejecución

## 1. Alcance y requisitos

Este manual describe la operación local del pipeline SG-Food a partir de la estructura versionada en `Proyecto1/`. **No elimina datos de las bases ni reconstruye volúmenes existentes**. Requiere Docker Engine con Docker Compose y Python 3. Los procedimientos se cotejaron con los scripts y `compose.yaml`; no se afirma que un tercero haya realizado una instalación independiente desde cero.

Trabajar desde la carpeta `Proyecto1`, con las carpetas `data/`, `dbt/`, `dags/`, `docker/`, `etl/`, `scripts/`, `sql/`, `docs/`, `tests/` y `resultados/` presentes.

## 2. Preparar configuración local

```bash
cp .env.example .env
```

Editar `.env` y sustituir **todos** los valores `REPLACE_WITH_*` por secretos diferentes y persistentes. Mantener las claves fuera de Git, chats y logs. Los puertos de referencia son `15433` (OLTP), `15434` (DW) y `18080` (interfaz Airflow), publicados solo sobre localhost. Comprobar que estén disponibles en el equipo.

En [`compose.yaml`](../compose.yaml) las conexiones internas usan `sgfood-oltp-postgres`, `sgfood-dw-postgres` y puerto `5432`. Los valores de `DBT_HOST` y `DBT_PORT` para el contenedor se inyectan por Compose; para ejecuciones locales de dbt pueden requerir el host/puerto publicados. No usar contraseñas de administrador como credenciales de los procesos de carga.

## 3. Validar e iniciar contenedores

```bash
docker compose --env-file .env config --quiet
docker compose --env-file .env build
docker compose --env-file .env up -d
docker compose --env-file .env ps
```

El primer arranque con volúmenes vacíos inicializa el OLTP con `data/sgfood_oltp.sql`, crea los esquemas iniciales del DW con `docker/postgres/dw/init/001-create-schemas.sql` y migra el metastore de Airflow mediante `airflow-init`. La ejecución repetida de `up` sobre volúmenes existentes no recrea automáticamente esas bases. Verificar contenedores saludables antes de continuar.

## 4. Aprovisionar roles

Los permisos de lectura transaccional, carga raw y construcción dbt son independientes. Desde el host:

```bash
python scripts/provision_roles.py --env-file .env oltp
python scripts/provision_roles.py --env-file .env dw
python scripts/provision_roles.py --self-test
```

El script implementa validaciones de identidad, esquemas y membresías. Las pruebas históricas de acceso permitido y denegado se recogen en [`resultados/02`](../resultados/02-validacion-permisos-dw.txt) y [`03`](../resultados/03-validacion-permisos-oltp.txt); véase [seguridad](04-permisos.md). No repetir un aprovisionamiento sobre un ambiente ajeno sin verificar propietarios y credenciales.

## 5. Ejecutar el pipeline integral

La **ruta principal de ejecución** es el DAG de Airflow:

```bash
docker compose --env-file .env exec airflow-scheduler airflow dags trigger sgfood_elt_integral
```

Airflow procesa, en orden: `precheck_config` → `raw_load` → `dbt_build_all` → `integrity_reconciliation` → `pipeline_success`.

Comprobar en la UI de Airflow (por defecto `http://127.0.0.1:18080`, según `.env`) que las cinco tareas estén `success`. Alternativamente, sustituir el marcador por un **RUN_ID real**, sin incluir los símbolos de menor/mayor que:

```bash
docker compose --env-file .env exec airflow-scheduler   airflow tasks states-for-dag-run sgfood_elt_integral RUN_ID_REAL
```

El DAG es manual (`schedule=None`) y no tiene reintentos automáticos. No considerar terminada la ejecución únicamente porque el comando `trigger` retornó sin error; verificar el estado final del run.

## 6. Ejecuciones independientes de mantenimiento

Son alternativas, **no pasos que deban repetirse después de cada DAG exitoso**:

```bash
# Carga raw directa (host, con Python y dependencias instaladas)
python etl/raw_loader.py --source-dir data --env-file .env

# Construcción y pruebas dbt dentro del entorno Airflow
docker compose --env-file .env exec airflow-scheduler   /opt/airflow/sgfood-venv/bin/dbt build   --project-dir /opt/airflow/dbt   --profiles-dir /opt/airflow/dbt-profiles   --target dev   --target-path /opt/airflow/dbt-artifacts/target   --log-path /opt/airflow/dbt-artifacts/logs

# Reconciliación independiente
docker compose --env-file .env exec airflow-scheduler   /opt/airflow/sgfood-venv/bin/python   /opt/airflow/etl/integrity_reconciliation.py
```

Para la ejecución directa desde el host, las dependencias se indican en [`requirements-etl.txt`](../requirements-etl.txt); la construcción de Airflow ya instala su entorno aislado. No ejecutar estos comandos sobre bases ajenas sin confirmar el contexto.

## 7. Verificar resultados

| Resultado esperado en el conjunto académico | Dónde verificar |
|---|---|
| Cinco tareas del DAG finalizadas con éxito | [Run 37](../resultados/37-airflow-3c3-primera-ejecucion.txt), [run 38](../resultados/38-airflow-3c3-segunda-ejecucion.txt) |
| dbt: 21 modelos y 201 pruebas sin errores | [Run 37](../resultados/37-airflow-3c3-primera-ejecucion.txt), [run 38](../resultados/38-airflow-3c3-segunda-ejecucion.txt) |
| Reconciliación completa, código 0 | [Run 37](../resultados/37-airflow-3c3-primera-ejecucion.txt) y [38](../resultados/38-airflow-3c3-segunda-ejecucion.txt) |
| Comparación idempotente de 17 objetos fotografiados | [Resultado 39](../resultados/39-airflow-3c3-idempotencia.txt) |
| 12 bloques y 16 SELECT analíticos, sin errores | [Resultado 40](../resultados/40-validacion-consultas-analiticas.txt) |

Para consultas de apoyo, utilizar [`sql/05-consultas-analiticas.sql`](../sql/05-consultas-analiticas.sql). Las consultas se ejecutaron sobre el DW en modo lectura, con control de tiempo y rollback; no ejecutar DDL o SQL destructivo como parte de la revisión.

## 8. Definiciones SQL y modelo de datos

- [`sql/03-create-raw.sql`](../sql/03-create-raw.sql): DDL ejecutable de doce tablas físicas raw.
- [`sql/04-ddl-dw.sql`](../sql/04-ddl-dw.sql): DDL/contrato documental del modelo implementado, incluidas vistas y relaciones lógicas.
- [`sql/06-ddl-dw-reproducible.sql`](../sql/06-ddl-dw-reproducible.sql): exportación estática de esquema PostgreSQL 16.15 con doce tablas raw, 21 vistas y 13 constraints físicos en raw. **No se ensayó su restauración sobre una base limpia**; no debe ejecutarse indiscriminadamente sobre una base existente.
- [`dbt/models/`](../dbt/models/): definición que administra las 21 vistas; [`dbt/tests/`](../dbt/tests/): pruebas singulares SQL.

Los marts son vistas, sin PK/FK físicas sobre ellas. Su integridad se comprueba mediante tests dbt y reconciliación independiente.

## 9. Diagnóstico de incidencias

| Síntoma | Revisión no destructiva |
|---|---|
| Falta variable o aparece placeholder | Revisar `.env` sin copiar sus secretos a evidencias |
| El servicio PostgreSQL no está saludable | Consultar `docker compose --env-file .env ps` y logs del servicio afectado |
| Falla `precheck_config` | Revisar montajes, permisos de `/opt/airflow/dbt-artifacts`, conexión y entorno virtual |
| Falla `raw_load` | Revisar fuente SQL/CSV, formato UTF-8, cabeceras y claves naturales; comprobar rollback |
| Falla `dbt_build_all` | Consultar errores de modelos y tests del run, manteniendo secretos ocultos |
| Falla `integrity_reconciliation` | Revisar diferencias de conteos, relaciones y cobertura sin alterar los datos |
| El DAG no aparece | Verificar scheduler, dag-processor y errores de importación de DAG |

No crear un segundo pipeline paralelo, no desactivar controles y no eliminar volúmenes para resolver errores de arranque.

## 10. Parada segura y alcance de reproducibilidad

```bash
docker compose --env-file .env stop
# Para reanudar con los mismos volúmenes:
docker compose --env-file .env start
```

**No usar `docker compose down -v`**. Los resultados entregados corresponden al ambiente académico verificado: dos ejecuciones integrales exitosas y evidencias numéricas. No existe prueba documentada de instalación independiente por tercero, recuperación ante desastre, restauración limpia del DDL ni rendimiento de producción. La publicación en GitHub no constituye por sí sola el registro de entrega en UEDI.
