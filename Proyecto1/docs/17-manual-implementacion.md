# Manual de implementación — SG-Food ELT

Este manual se deriva de compose.yaml, .env.example, los scripts, el DAG y la configuración dbt existentes. Los procedimientos no se ejecutaron durante este bloque; las ejecuciones reales citadas están en resultados/37–40.

## 1. Requisitos previos y preparación

Usar Docker Compose, Python 3.x y la raíz Proyecto1/. Confirmar data/, etl/, sql/, scripts/, dbt/, dags/, docker/, tests/, docs/ y resultados/. Preparar el archivo local:

```bash
cp .env.example .env
```

Editar .env y sustituir todos los placeholders REPLACE_WITH_* por valores locales aleatorios y persistentes. No versionar .env, no imprimir secretos ni pasarlos como argumentos. Las fuentes operativas son data/sgfood_oltp.sql y los cinco CSV: inventario_bodega.csv, devoluciones.csv, metas_ventas.csv, promociones.csv y proveedores_precios.csv.

## 2. Compose y PostgreSQL

Validar y construir sin iniciar el flujo:

```bash
docker compose --env-file .env config --quiet
docker compose --env-file .env build
```

Iniciar los servicios del proyecto:

```bash
docker compose --env-file .env up -d
```

airflow-init ejecuta airflow db migrate y los otros servicios Airflow dependen de su finalización. Verificar:

```bash
docker compose --env-file .env ps
```

El primer arranque aplica el SQL OLTP y el DDL inicial del DW mediante los montajes de Compose. No usar docker compose down -v ni borrar volúmenes.

## 3. Roles y permisos

Con .env configurado y las bases disponibles, ejecutar desde la raíz:

```bash
python scripts/provision_roles.py --env-file .env oltp
python scripts/provision_roles.py --env-file .env dw
python scripts/provision_roles.py --self-test
```

El script valida identidad, crea roles con privilegio mínimo y aplica cambios transaccionales. La validación funcional de ACL requiere una base iniciada y no se repitió en este bloque: PENDIENTE.

## 4. Loader Python

Ejecutar fuera de Airflow, con servicios activos:

```bash
python etl/raw_loader.py --source-dir data --env-file .env
```

El loader lee el OLTP con sgfood_oltp_reader, valida CSV y carga doce tablas raw con sgfood_raw_loader. La carga DW es transaccional y hace rollback ante error. Esta ejecución directa no se repitió en este bloque: PENDIENTE.

## 5. dbt

El perfil usa DBT_HOST, DBT_PORT y SGFOOD_DBT_RUNNER_PASSWORD. La ejecución equivalente dentro del contenedor es:

```bash
docker compose --env-file .env exec airflow-scheduler /opt/airflow/sgfood-venv/bin/dbt build --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt-profiles --target dev --target-path /opt/airflow/dbt-artifacts/target --log-path /opt/airflow/dbt-artifacts/logs
```

La validación real disponible es el dbt build ejecutado por el DAG.

## 6. Airflow

Después de que los servicios estén saludables, disparar manualmente el DAG:

```bash
docker compose --env-file .env exec airflow-scheduler airflow dags trigger sgfood_elt_integral
```

Consultar tareas para el RUN_ID real:

```bash
docker compose --env-file .env exec airflow-scheduler airflow tasks states-for-dag-run sgfood_elt_integral <RUN_ID>
```

Las cinco tareas esperadas en success son precheck_config, raw_load, dbt_build_all, integrity_reconciliation y pipeline_success. La política actual es retries=0.

## 7. Integridad, evidencias e idempotencia

La reconciliación manual equivalente es:

```bash
docker compose --env-file .env exec airflow-scheduler /opt/airflow/sgfood-venv/bin/python /opt/airflow/etl/integrity_reconciliation.py
```

Consultar [primera ejecución](../resultados/37-airflow-3c3-primera-ejecucion.txt), [segunda ejecución](../resultados/38-airflow-3c3-segunda-ejecucion.txt) e [idempotencia](../resultados/39-airflow-3c3-idempotencia.txt). Las evidencias registran dos DAG runs exitosos, cinco tareas exitosas por corrida, 21 modelos, 201 pruebas, PASS=222, WARN=0, ERROR=0 y reconciliación con código 0.

La evidencia 39 compara exactamente 17 objetos y solo sustenta idempotencia observacional de esas fotografías; no prueba inmutabilidad global.

## 8. Problemas frecuentes

- Si faltan variables, revisar .env y eliminar placeholders.
- Dentro de Compose usar nombres de servicio y puerto 5432; los puertos publicados son para el host.
- Si falla el precheck, revisar montajes, ejecutables del virtualenv y permisos de dbt-artifacts.
- Si falla raw, revisar UTF-8, encabezados, cantidad de campos y claves naturales.
- Si falla dbt, revisar logs de dbt sin publicar secretos.
- Si falla una tarea, revisar logs; no activar reintentos implícitos.

No borrar volúmenes ni ejecutar acciones globales para resolver fallos.

## 9. DDL y consultas analíticas

`sql/03-create-raw.sql` contiene el DDL ejecutable de las 12 tablas raw. `sql/04-ddl-dw.sql` es el DDL contractual del catálogo y distingue tablas físicas raw, vistas dbt y relaciones lógicas verificadas por pruebas. `sql/06-ddl-dw-reproducible.sql` es una exportación estática de PostgreSQL 16.15 con 12 tablas raw, 21 vistas y 13 constraints físicos raw. No se restauró sobre una base limpia durante este bloque: `PENDIENTE`.

`sql/05-consultas-analiticas.sql` contiene 12 bloques y 16 SELECT efectivos. Su ejecución documentada en [resultados/40](../resultados/40-validacion-consultas-analiticas.txt) fue de solo lectura y confirmó integridad referencial y conservación de 3,209 filas del hecho. No se repite aquí ni se declaran métricas comerciales no presentes en la fuente.

## 10. Parada segura y limitaciones

Detener solo este proyecto sin eliminar datos persistentes:

```bash
docker compose --env-file .env stop
```

Reanudarlo:

```bash
docker compose --env-file .env start
```

No usar docker compose down -v. Permanecen limitaciones: ejecución manual, retries deshabilitados, resúmenes de evidencia en lugar de logs completos, idempotencia limitada a 17 objetos, restauración del DDL exportado no probada y ejecución independiente del manual por un tercero pendiente.
