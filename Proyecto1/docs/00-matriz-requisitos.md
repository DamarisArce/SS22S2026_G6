# Matriz inicial de requisitos y evidencias

Estado de esta fase: **PENDIENTE**. Este documento organiza el enunciado y la rúbrica; no demuestra implementación ni cumplimiento. La evidencia solo podrá marcarse como obtenida después de ejecutar el componente correspondiente y conservar su salida reproducible.

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
