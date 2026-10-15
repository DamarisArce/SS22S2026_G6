# SG-Food — Plataforma de integración y análisis de datos

**Universidad de San Carlos de Guatemala · Facultad de Ingeniería · Seminario de Sistemas 2 · Proyecto 1**

**Integrantes:** Dámaris Magali Arce Guzmán (202006636) y Nelson Emanuel Cún Bálan (201222010).

## Resumen ejecutivo

SG-Food integra información transaccional de ventas y archivos operativos mediante un pipeline **ELT (Extract, Load, Transform)**. Python extrae siete tablas de PostgreSQL OLTP y procesa cinco archivos CSV; carga sus datos en el esquema `raw` de un Data Warehouse PostgreSQL. **Apache Airflow** coordina la ejecución; **dbt Core** transforma los datos en las capas `staging`, `intermediate` y `marts`, construye dimensiones y un hecho de ventas y ejecuta pruebas de calidad. Una reconciliación independiente y consultas SQL verifican la integridad de los resultados.

El proyecto está implementado y cuenta con dos ejecuciones integrales exitosas registradas. Las verificaciones reportadas en este documento corresponden al conjunto de datos académico utilizado; no representan disponibilidad permanente de un servicio productivo.

![Arquitectura ELT de SG-Food](docs/diagramas/SG-Food%20·%20Arquitectura%20ELT.drawio.png)

[Editar arquitectura en draw.io](docs/diagramas/01-arquitectura-elt.drawio) · [Descripción técnica completa](docs/02-arquitectura-y-decisiones.md)

## Alcance funcional

| Componente | Implementación |
|---|---|
| Fuentes | PostgreSQL `sgfood_oltp` (7 tablas) y 5 CSV operativos |
| Extracción/carga | `etl/raw_loader.py`; 12 tablas físicas en `raw`, carga transaccional y metadatos de procedencia |
| Orquestación | DAG `sgfood_elt_integral`: 5 tareas secuenciales, ejecución manual |
| Transformación | dbt Core: 12 vistas `staging`, 4 `intermediate` y 5 `marts` |
| Modelo dimensional | `dim_cliente`, `dim_fecha`, `dim_producto`, `dim_sucursal`, `fct_ventas_detalle` |
| Seguridad | Roles separados para lectura OLTP, carga raw y ejecución dbt; contraseñas locales por entorno |
| Verificación | Pruebas dbt, reconciliación Python, consultas SQL y comprobaciones de idempotencia |

## Arquitectura y modelo de datos

Los cuatro esquemas del DW tienen funciones diferenciadas: `raw` conserva las fuentes y su linaje; `staging` normaliza tipos y estructura; `intermediate` integra entidades y prepara agregaciones; `marts` expone el modelo dimensional para consultas. Los **21 modelos de dbt son vistas PostgreSQL**; las relaciones de estas vistas se verifican mediante pruebas y reconciliación, no mediante claves foráneas físicas sobre las vistas.

![Modelo dimensional](docs/diagramas/SG-Food%20·%20Modelo%20dimensional%20de%20ventas.drawio.png)

[Editar modelo en draw.io](docs/diagramas/03-modelo-dimensional.drawio) · [Documentación de marts](docs/11-dbt-marts-ventas-detalle.md)

## Resultados de validación

| Control | Resultado documentado | Evidencia |
|---|---|---|
| DAG de Airflow | 2 ejecuciones exitosas; 5 tareas `success` en cada una | [37](resultados/37-airflow-3c3-primera-ejecucion.txt), [38](resultados/38-airflow-3c3-segunda-ejecucion.txt) |
| `dbt build` | 21 modelos + 201 pruebas = 222 operaciones; `PASS=222`, `WARN=0`, `ERROR=0` | [37](resultados/37-airflow-3c3-primera-ejecucion.txt), [38](resultados/38-airflow-3c3-segunda-ejecucion.txt) |
| Reconciliación | Finalizada con código 0 en ambas ejecuciones | [37](resultados/37-airflow-3c3-primera-ejecucion.txt), [38](resultados/38-airflow-3c3-segunda-ejecucion.txt) |
| Idempotencia observacional | 17 objetos con conteos y SHA-256 coincidentes en tres fotografías | [39](resultados/39-airflow-3c3-idempotencia.txt) |
| Consultas analíticas | 12 bloques y 16 `SELECT` ejecutados en lectura sin errores; hecho con 3,209 filas | [40](resultados/40-validacion-consultas-analiticas.txt) |

Las huellas de idempotencia demuestran igualdad de los **17 objetos fotografiados**, no identidad de todo el entorno ni una prueba general de cambios incrementales.

## Instalación y ejecución

**Requisitos:** Docker Engine con Compose, Python 3 y recursos suficientes para los contenedores. Trabajar desde `Proyecto1/`.

```bash
cp .env.example .env
# Editar .env y sustituir todos los placeholders por secretos locales

docker compose --env-file .env config --quiet
docker compose --env-file .env build
docker compose --env-file .env up -d

python scripts/provision_roles.py --env-file .env oltp
python scripts/provision_roles.py --env-file .env dw

docker compose --env-file .env exec airflow-scheduler airflow dags trigger sgfood_elt_integral
```

Se debe verificar el estado de las cinco tareas en Airflow. La inicialización de roles y los procedimientos detallados, alternativas de ejecución y parada segura se describen en el **[manual de implementación](docs/17-manual-implementacion.md)**. No versionar `.env` ni utilizar `docker compose down -v`.

## Guía de documentación

| Documento | Descripción |
|---|---|
| [Matriz de cumplimiento](docs/00-matriz-requisitos.md) | Correspondencia con requisitos, pruebas y entregables |
| [Catálogo de fuentes](docs/01-catalogo-fuentes.md) | Datos de entrada, claves, granularidades y anomalías observadas |
| [Arquitectura](docs/02-arquitectura-y-decisiones.md) | Componentes, flujos, decisiones y diagramas |
| [Infraestructura](docs/03-infraestructura.md) · [Seguridad](docs/04-permisos.md) | Despliegue lógico, redes, persistencia y privilegios |
| [Carga raw](docs/05-carga-raw.md) | Contratos de extracción/carga e idempotencia |
| [Staging](docs/06-dbt-staging.md) · [Intermediate](docs/07-dbt-intermediate.md) | Transformaciones y linaje |
| [Inventario](docs/08-dbt-inventario-snapshot.md) · [Devoluciones](docs/09-dbt-devoluciones.md) · [Ventas mensuales](docs/10-dbt-ventas-mensuales.md) | Modelos intermedios de apoyo |
| [Hecho](docs/11-dbt-marts-ventas-detalle.md) · [Sucursal](docs/12-dbt-marts-dim-sucursal.md) · [Producto](docs/13-dbt-marts-dim-producto.md) · [Fecha](docs/14-dbt-marts-dim-fecha.md) · [Cliente](docs/15-dbt-marts-dim-cliente.md) | Modelo dimensional de consumo |
| [Airflow](docs/16-airflow-infraestructura.md) · [Manual](docs/17-manual-implementacion.md) | Orquestación y procedimientos |

**Scripts SQL:** [DDL de raw](sql/03-create-raw.sql), [DDL descriptivo DW](sql/04-ddl-dw.sql), [consultas analíticas](sql/05-consultas-analiticas.sql), [exportación de esquema](sql/06-ddl-dw-reproducible.sql). Las evidencias de pruebas se conservan sin alteración en [`resultados/`](resultados/).

## Límites del diseño verificado

- Los marts y demás modelos dbt son **vistas** con claves y relaciones lógicas; no tienen PK/FK físicas. Las 12 tablas raw sí disponen de restricciones físicas documentadas.
- El DAG tiene `schedule=None`, `retries=0`, `catchup=False` y `max_active_runs=1`; la ejecución periódica no está configurada.
- La exportación DDL está disponible, pero no se realizó una restauración independiente sobre una base limpia.
- Los resultados de Airflow conservados son resúmenes de ejecución; no sustituyen el conjunto completo de logs de operación.
- No se implementaron SCD tipo 2, atribución de promociones a ventas ni dashboard; no se definieron reglas comerciales suficientes para justificarlos.
- La ejecución independiente del manual por otra persona no se ha documentado; la presentación en UEDI es un acto de entrega separado del desarrollo.
