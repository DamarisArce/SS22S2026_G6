# Infraestructura y despliegue de SG-Food

## Topología de servicios

La solución se ejecuta mediante [`compose.yaml`](../compose.yaml), con nombre de proyecto `sgfood-ss2-g6-proyecto1`. Incluye tres servidores PostgreSQL (OLTP, Data Warehouse y metastore de Airflow) y cuatro servicios de Apache Airflow (`airflow-init`, `airflow-scheduler`, `airflow-api-server`, `airflow-dag-processor`). La imagen Airflow se construye desde [`docker/airflow/Dockerfile`](../docker/airflow/Dockerfile).

| Servicio | Función | Puerto interno | Acceso desde host |
|---|---|---|---|
| `sgfood-oltp-postgres` | Fuente transaccional | 5432 | `127.0.0.1:${POSTGRES_OLTP_HOST_PORT}` |
| `sgfood-dw-postgres` | Almacenamiento raw y modelos analíticos | 5432 | `127.0.0.1:${POSTGRES_DW_HOST_PORT}` |
| `sgfood-airflow-postgres` | Metadatos de Airflow | 5432 | No publicado |
| `airflow-api-server` | Interfaz/API Airflow | 8080 | `127.0.0.1:${AIRFLOW_HOST_PORT}` |
| `airflow-scheduler` | Planificación y ejecución | N/A | No publicado |
| `airflow-dag-processor` | Procesamiento de definiciones DAG | N/A | No publicado |
| `airflow-init` | Migración del metastore | N/A | No publicado |

Los valores de referencia en [`.env.example`](../.env.example) son `15433` para OLTP, `15434` para DW y `18080` para Airflow. Las conexiones entre contenedores usan nombres de servicio y el puerto interno PostgreSQL `5432`.

## Redes y persistencia

- `sgfood_elt_net`: red interna compartida por todos los servicios ELT, sin exposición directa externa.
- `sgfood_access_net`: puente para componentes con puertos publicados; el API server se conecta además a esta red.
- Volúmenes administrados: datos OLTP, DW, metastore Airflow, logs, artefactos dbt y autenticación Airflow. Los volúmenes protegen el estado entre reinicios de contenedor.
- Montajes de solo lectura: `data/`, `etl/`, `sql/`, `dbt/`, `dags/`. Los artefactos de ejecución se escriben en volúmenes dedicados.

Las instancias PostgreSQL usan `postgres:16.15-bookworm`. Airflow usa `apache/airflow:3.1.0-python3.12` con `LocalExecutor`; dbt se instala en `/opt/airflow/sgfood-venv`, separado del entorno Python de Airflow. Versiones declaradas: dbt Core `1.11.12`, dbt-postgres `1.10.2` y Psycopg `3.3.6`.

## Inicialización

En el primer arranque de volúmenes vacíos, el contenedor OLTP aplica `data/sgfood_oltp.sql` y el DW ejecuta `docker/postgres/dw/init/001-create-schemas.sql`. Airflow inicializa sus metadatos con `airflow db migrate`. Estos scripts de entrada de PostgreSQL **no se reejecutan automáticamente** al reiniciar contenedores con volúmenes ya inicializados.

El aprovisionamiento de roles se ejecuta expresamente mediante `scripts/provision_roles.py`. La carga raw y las transformaciones se ejecutan con el DAG o mediante comandos de mantenimiento controlados, no en el arranque por sí solo.

## Configuración y operación básica

Desde la raíz `Proyecto1/`:

```bash
cp .env.example .env
# Sustituir todos los placeholders con secretos distintos y seguros.
docker compose --env-file .env config --quiet
docker compose --env-file .env build
docker compose --env-file .env up -d
docker compose --env-file .env ps
```

La credencial `.env` es local y no se versiona. Verificar disponibilidad de servicios antes de iniciar el DAG. Para operación y resolución de problemas, seguir el [manual](17-manual-implementacion.md).

## Seguridad y límites operativos

Los puertos publicados se enlazan a localhost, el metastore no publica puerto y los contenedores Airflow utilizan `no-new-privileges:true`. El control de acceso a las bases se aplica mediante los [roles](04-permisos.md). Las políticas de CPU y memoria declaradas en Compose limitan los contenedores PostgreSQL, pero no constituyen una prueba de rendimiento.

La configuración está diseñada para una ejecución académica local, no para una plataforma HA/productiva. No se realizaron pruebas documentadas de recuperación desde copia de seguridad, restauración del DDL exportado sobre una base limpia ni carga de rendimiento. Para detener sin perder datos: `docker compose --env-file .env stop`. **No usar `down -v`**, porque elimina volúmenes persistentes.
