# Matriz de requisitos y evidencias — estado actualizado

> El contenido histórico de la revisión inicial que sigue a esta sección queda supersedido por esta matriz actualizada. Estados: `VALIDADO`, `PARCIAL`, `PENDIENTE`.

## Requisitos obligatorios

| ID | Implementación real | Evidencia | Estado |
|---|---|---|---|
| R-01 | `etl/raw_loader.py` carga siete tablas OLTP y cinco CSV transaccionalmente. | `resultados/04`–`06`, `37`–`38`, `tests/test_raw_loader.py` | VALIDADO |
| R-02 | DAG secuencial de cinco tareas; dos ejecuciones manuales exitosas. | `dags/sgfood_elt_integral.py`, `tests/test_airflow_dag_contract.py`, `resultados/37`–`38` | VALIDADO |
| R-03 | Schemas separados, 12 tablas raw y modelo dimensional dbt con cuatro dimensiones y un hecho; las capas dbt son vistas, con claves lógicas, relaciones y pruebas de integridad. | `sql/03-create-raw.sql`, `sql/04-ddl-dw.sql`, `sql/06-ddl-dw-reproducible.sql`, `dbt/models/`, `dbt/tests/`, `resultados/37`–`40` | VALIDADO |
| R-04 | 21 modelos, 12 sources y 201 tests declarados; `dbt build` en ambas corridas. | `dbt/models/`, `dbt/tests/`, `resultados/37`–`38` | VALIDADO |
| R-05 | Tests dbt y reconciliación cubren claves, relaciones, preservación y fanout. | `etl/integrity_reconciliation.py`, `tests/test_integrity_reconciliation.py`, `resultados/37`–`38` | VALIDADO |
| R-06 | ELT documentado y validado; 12 bloques y 16 SELECT analíticos ejecutados en lectura. | `README.md`, `docs/01`–`17`, `sql/05-consultas-analiticas.sql`, `resultados/40-validacion-consultas-analiticas.txt` | VALIDADO |
| R-07 | Python, Airflow, PostgreSQL y dbt están configurados y conectados. | `compose.yaml`, `docker/airflow/Dockerfile`, `docker/airflow/requirements.txt` | VALIDADO |
| R-08 | Loader y raw integran OLTP y CSV con claves y hashes. | `etl/raw_loader.py`, `data/`, `sql/03-create-raw.sql` | VALIDADO |
| R-09 | Componentes, DDL contractual/exportado, consultas, documentación y evidencias están integrados en `Proyecto1` dentro de `main`, junto con los 18 commits de la integración y sus 171 archivos versionados. | Commit integrado `a8738061a92c6276e9ab6e6327be25e4bf5cfd8e`, árbol de `Proyecto1`, `README.md`, `sql/04-ddl-dw.sql`, `sql/05-consultas-analiticas.sql`, `sql/06-ddl-dw-reproducible.sql`, `docs/17-manual-implementacion.md` | VALIDADO |
| R-10 | Los dos integrantes aparecen sin cambios en README. | `README.md`, PDF académico | VALIDADO |

## Criterios de rúbrica

| ID | Criterio | Evidencia | Estado |
|---|---|---|---|
| Q-01 | Flujo Python + Airflow | Dos runs exitosos, cinco tareas por corrida y códigos 0 de raw/dbt/reconciliación. | VALIDADO |
| Q-02 | Documentación y manual | README y manual cubren instalación, configuración, PostgreSQL, raw, dbt, Airflow, pruebas, evidencias, parada segura y limitaciones; respaldados por ejecuciones previas. La repetición independiente por tercero no es requisito expreso del PDF. | VALIDADO |
| Q-03 | Entregables y repositorio | Componentes, DDL 04/06, consultas 05, documentación y evidencias quedaron integrados en `main` mediante los 18 commits de la integración, con 171 archivos versionados en `Proyecto1`. | VALIDADO |
| Q-04 | DW y modelos dbt | 21 modelos, 201 tests declarados; `PASS=222`, `WARN=0`, `ERROR=0`. | VALIDADO |
| Q-05 | Fuentes, pruebas y validación | Fuentes, raw, dbt, reconciliación, idempotencia observacional y `resultados/40` con 16 SELECT efectivos. | VALIDADO |

## Opcionales y trazabilidad

| ID | Elemento | Estado |
|---|---|---|
| O-01 | Programación y parametrización | PARCIAL: `schedule=None`; programación opcional/recomendada según el PDF; parametrización por `.env`. |
| O-02 | Validaciones adicionales | VALIDADO: reconciliación, pruebas y evidencias implementadas. |
| O-03 | Visualización | PENDIENTE: no implementada ni obligatoria. |

Las evidencias 37 y 38 registran dos DAG runs exitosos, cinco tareas exitosas por corrida, 21 modelos, 201 pruebas, `PASS=222`, `WARN=0`, `ERROR=0` y reconciliación con código 0. La evidencia 39 compara exactamente 17 objetos y sustenta idempotencia observacional solo de esas fotografías, no inmutabilidad global. La evidencia 40 registra 12 bloques y 16 SELECT efectivos, con 3,209 filas conservadas en el hecho y sin errores.

La integración de los 18 commits y los 171 archivos de `Proyecto1` en `main` elimina la pendiente de versionado que sustentaba los estados anteriores de R-09 y Q-03. El commit integrado es `a8738061a92c6276e9ab6e6327be25e4bf5cfd8`, confirmado en `main` y sincronizado con `origin/main`. Permanece pendiente la restauración del DDL exportado sobre una base limpia; el PDF no la exige expresamente. La ejecución independiente del manual por un tercero tampoco es requisito expreso. No se declara realizada la entrega UEDI.

## Archivo histórico de la matriz inicial — no autoritativo

El bloque que sigue conserva la trazabilidad del diseño inicial. Sus estados `PENDIENTE` corresponden a la revisión anterior y no son estados vigentes; la única matriz autoritativa es la sección actualizada al inicio de este archivo.

## Fuente de requisitos

- `insumos/798_Proyecto_1_2S2026.pdf`: enunciado, alcance, entregables, metodología y rúbrica.
- `insumos/Data-20260930.zip`: fuente OLTP y archivos delimitados revisados para diseñar la siguiente fase.

## Requisitos obligatorios

| ID | Requisito | Implementación esperada | Prueba requerida | Evidencia requerida | Estado |
|---|---|---|---|---|---|
| R-01 | Extraer y cargar datos con Python | Scripts parametrizados para OLTP y archivos CSV hacia `raw` | Ejecución repetible, conteos origen/destino y manejo de errores | Logs, parámetros no sensibles y consulta de conteos | PENDIENTE |
| R-02 | Orquestar el flujo con Airflow | DAG con extracción, carga, dbt y validaciones dependientes | Ejecución completa y reejecución controlada | Vista/log del DAG y estado de cada tarea | PENDIENTE |
| R-03 | Construir DW en PostgreSQL | Schemas separados y modelo dimensional con relaciones y claves | DDL ejecutado, integridad referencial y consultas de humo | DDL, catálogo de tablas y resultados SQL | PENDIENTE |
| R-04 | Implementar dbt en staging, intermediate y marts | `sources`, `refs`, modelos y materializaciones coherentes | `dbt build`/pruebas sobre PostgreSQL | Logs, manifest/docs y resultados de tests | PENDIENTE |
| R-05 | Probar calidad e integridad | Tests de unicidad, no nulidad, relaciones, dominios y reglas de negocio | Suite dbt/SQL sin fallos; excepciones explicadas | Resultados de pruebas y registro de anomalías | PENDIENTE |
| R-06 | Validar y documentar el flujo completo | Consultas analíticas y documentación técnica/manual | Comparación de conteos, totales y casos de aceptación | SQL, salidas fechadas y documentación actualizada | PENDIENTE |
| R-07 | Usar Python, Airflow, PostgreSQL y dbt Core | Componentes declarados y conectados en la solución | Verificación de versiones compatibles en entorno real | Configuración reproducible, sin secretos | PENDIENTE |
| R-08 | Integrar una base transaccional y CSV | Carga diferenciada OLTP/archivos, con linaje | Conteos y claves de cada fuente | Mapa de fuentes y logs de carga | PENDIENTE |
| R-09 | Entregar scripts, DAGs, dbt, SQL y documentación | Repositorio organizado en `Proyecto1` | Revisión de estructura y ejecución desde instrucciones | Árbol de archivos y manual | PENDIENTE |
| R-10 | Trabajo en parejas e integrantes identificados | Los dos integrantes ya se encuentran identificados en el README raíz | Revisión del README/documentación final | README raíz con ambos nombres y documentación final | PENDIENTE |

## Criterios de la rúbrica

| ID | Criterio | Implementación que debe existir | Prueba y evidencia mínima | Estado |
|---|---|---|---|---|
| Q-01 | Flujo Python + Airflow (20 pts) | Extracción, carga, dependencias, DAG funcional y manejo básico de errores | DAG ejecutado correctamente y logs de carga/validación | PENDIENTE |
| Q-02 | Documentación y manual (10 pts) | Pipeline, PostgreSQL, dbt, DAG, configuración, integrantes y pasos | Otra persona puede seguir el manual y repetir la ejecución | PENDIENTE |
| Q-03 | Entregables y repositorio (10 pts) | Scripts, DAGs, dbt, SQL, docs y evidencias organizados | Revisión de estructura y evidencia del trabajo en pareja | PENDIENTE |
| Q-04 | DW y modelos dbt (30 pts) | Sources, refs, materializaciones, dimensiones, hechos, relaciones y tests | `dbt build`/tests ejecutados sobre PostgreSQL | PENDIENTE |
| Q-05 | Fuentes, pruebas y validación (30 pts) | Todas las fuentes cargadas, raw, DAG y consultas analíticas | Conteos, integridad, calidad y resultados analíticos reproducibles | PENDIENTE |

## Opcional / recomendado

| ID | Recomendación | Posible evidencia | Estado |
|---|---|---|---|
| O-01 | Programar el DAG y parametrizar conexiones | Schedule documentado y configuración sin secretos | PENDIENTE |
| O-02 | Validaciones adicionales, errores y registros de ejecución | Alertas/logs y casos de error probados | PENDIENTE |
| O-03 | Conectar Power BI, Metabase o Superset | Consulta/dashboard reproducible | PENDIENTE |

No se debe tratar O-01–O-03 como requisitos obligatorios ni como registros operativos de las fuentes. Su implementación requiere decisión del equipo.

## Regla de cierre

Un requisito permanece `PENDIENTE` hasta que exista ejecución real, prueba correspondiente y evidencia identificable. Una recomendación arquitectónica de `docs/02-arquitectura-y-decisiones.md` no equivale a cumplimiento.

La identificación de los dos integrantes ya está disponible en el README raíz; el cierre de R-10 permanece `PENDIENTE` porque todavía falta la entrega documental final y su evidencia correspondiente.
