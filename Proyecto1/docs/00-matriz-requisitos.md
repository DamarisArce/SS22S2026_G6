# Matriz de cumplimiento y trazabilidad

Esta matriz relaciona el alcance obligatorio y los criterios de evaluación del enunciado académico `798_Proyecto_1_2S2026.pdf` (material del curso, no incluido en el repositorio) con componentes y evidencias verificables de SG-Food. **`VALIDADO`** significa que existe evidencia técnica documentada para el alcance indicado; no equivale a una calificación asignada por el evaluador.

## Requisitos obligatorios

| ID | Requisito | Implementación y evidencia principal | Estado |
|---|---|---|---|
| R-01 | Extracción y carga Python | [`raw_loader.py`](../etl/raw_loader.py), 7 tablas OLTP y 5 CSV; [04–06](../resultados/04-primera-carga-raw.txt), [37–38](../resultados/37-airflow-3c3-primera-ejecucion.txt) | VALIDADO |
| R-02 | Orquestación Airflow | [DAG de cinco tareas](../dags/sgfood_elt_integral.py), dos ejecuciones exitosas [37](../resultados/37-airflow-3c3-primera-ejecucion.txt) y [38](../resultados/38-airflow-3c3-segunda-ejecucion.txt) | VALIDADO |
| R-03 | DW dimensional PostgreSQL | 4 esquemas; 12 tablas raw; 4 dimensiones y 1 hecho publicados mediante vistas dbt; [DDL](../sql/04-ddl-dw.sql), [exportación](../sql/06-ddl-dw-reproducible.sql), [pruebas](../dbt/tests/) | VALIDADO* |
| R-04 | Modelos dbt por capas | 12 staging, 4 intermediate, 5 marts; 12 sources y 201 pruebas; [proyecto dbt](../dbt/) y [37–38](../resultados/37-airflow-3c3-primera-ejecucion.txt) | VALIDADO |
| R-05 | Calidad e integridad | Tests dbt, reconciliación Python y pruebas de cardinalidad; [reconciliación](../etl/integrity_reconciliation.py) y [37–38](../resultados/37-airflow-3c3-primera-ejecucion.txt) | VALIDADO |
| R-06 | Validación y documentación | README, [manual](17-manual-implementacion.md), [SQL analítico](../sql/05-consultas-analiticas.sql) y [evidencia 40](../resultados/40-validacion-consultas-analiticas.txt) | VALIDADO |
| R-07 | Tecnologías exigidas | [Compose](../compose.yaml), [Dockerfile Airflow](../docker/airflow/Dockerfile), Python, Airflow, PostgreSQL, dbt Core | VALIDADO |
| R-08 | Fuente transaccional y CSV | [`data/`](../data/), [contrato de carga](05-carga-raw.md), metadatos/hashes raw | VALIDADO |
| R-09 | Archivos organizados en repositorio | Código, DAG, proyecto dbt, SQL, docs y evidencias en `Proyecto1/` de `main`; incorporación original en `a873806`, cierre documental en `150f83f` | VALIDADO |
| R-10 | Identificación de integrantes | Ambos integrantes identificados en el [README](../README.md) | VALIDADO |

**Nota sobre R-03:** los modelos dimensionales son vistas PostgreSQL administradas por dbt, con claves y relaciones **lógicas** comprobadas mediante tests. No se han creado PK/FK físicas en vistas. Se documenta como implementación validada de modelo dimensional; el enunciado también utiliza la expresión «tablas de hechos y dimensiones» en el entregable DDL, por lo que queda expresamente identificada esta diferencia de materialización para evaluación.

## Correspondencia con la rúbrica

| Criterio | Evidencia documentada | Estado |
|---|---|---|
| Q-01 · Python y Airflow | Extracción, carga, cinco tareas, dos ejecuciones completas, errores controlados | VALIDADO |
| Q-02 · Documentación y manual | Arquitectura, diseño, configuración, modelos, resultados, procedimientos de instalación y parada | VALIDADO |
| Q-03 · Entregables y repositorio | Carpeta `Proyecto1` versionada en `main` con fuentes, scripts, modelos, SQL y evidencias | VALIDADO |
| Q-04 · DW y dbt | 21 vistas dbt, 201 pruebas, `PASS=222`, `WARN=0`, `ERROR=0` | VALIDADO* |
| Q-05 · Integración y validación | 12 tablas raw, reconciliación exitosa, comparación de 17 objetos y 16 consultas SELECT | VALIDADO |

No se asigna puntuación: corresponde al docente valorar el alcance y las materializaciones.

## Evidencia consolidada

| Referencias | Cobertura |
|---|---|
| [`01`–`06`](../resultados/01-validacion-postgresql.txt) | Infraestructura, permisos, cargas iniciales, repetición y rollback |
| [`07`–`36`](../resultados/07-dbt-staging-run.txt) | Construcción, tests y validaciones independientes de modelos dbt |
| [`37`](../resultados/37-airflow-3c3-primera-ejecucion.txt) y [`38`](../resultados/38-airflow-3c3-segunda-ejecucion.txt) | Dos ejecuciones completas del DAG; dbt 21 modelos y 201 tests, todas las tareas `success` |
| [`39`](../resultados/39-airflow-3c3-idempotencia.txt) | Comparación de 17 objetos mediante conteos y SHA-256 de tres fotografías |
| [`40`](../resultados/40-validacion-consultas-analiticas.txt) | 12 bloques de validación, 16 SELECT, 3,209 filas preservadas en el hecho |

## Funciones opcionales y limitaciones de cobertura

- **Ejecución programada:** no habilitada; el DAG es manual. La programación es recomendación opcional en el enunciado.
- **Validaciones adicionales:** se implementaron reconciliaciones y pruebas más allá de la creación de vistas.
- **Herramienta de visualización BI:** no implementada; recomendación opcional.
- **DDL físico:** `sql/03` crea tablas raw; `sql/04` describe el contrato dimensional; `sql/06` exporta el esquema existente con tablas raw y vistas. La restauración de `sql/06` sobre una base vacía no fue ensayada.
- **Manual:** la ejecución integral se probó mediante Airflow, pero no se documentó la reproducción independiente del manual por un tercero.
- **Entrega:** la publicación en GitHub está comprobada; **no se afirma que la entrega UEDI esté registrada**.
