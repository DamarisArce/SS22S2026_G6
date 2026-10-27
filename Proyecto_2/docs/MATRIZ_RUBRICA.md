# Trazabilidad técnica de requisitos y evidencias

Relacionamos los componentes del alcance con sus resultados comprobados, archivos SQL y soportes disponibles. La matriz describe la ejecución del proyecto; no constituye una autoasignación de puntuación.

| Componente | Implementación y resultado | Evidencia o alcance |
|---|---|---|
| Fuente pública | Tabla NYC Yellow Taxi 2022; 36,256,539 registros | `sql/01_exploracion/01_calidad.sql`; registro de calidad |
| Consultas SQL exploratorias | Agregaciones, filtros temporales, análisis mensual, ubicación y hora | `sql/01_exploracion/` y gráficos de la página 1 |
| Transformación | Tablas analíticas estándar y optimizada de 35,526,984 viajes | `sql/02_transformaciones/` y prueba de equivalencia |
| Particionamiento y clustering | Partición por fecha; clustering por origen y destino | `sql/03_optimizacion/` y registros del benchmark |
| Comparación de rendimiento | Reducción de 90.83 % de bytes, mismo resultado | `docs/VALIDACION_BENCHMARK_20261026.md` |
| Dos modelos BigQuery ML | Regresión lineal y regresión logística finalizadas | `sql/04_bigquery_ml/`, metadatos y evaluaciones |
| Hiperparámetros y evaluación | Iteraciones, regularización, parada temprana y métricas externas | Una configuración exitosa por modelo; sin búsqueda comparativa exhaustiva |
| División y fuga de datos | `CUSTOM`, validación temporal y TEST noviembre independiente | `sql/04_bigquery_ml/02_verificar_splits.sql`; `DATA_SPLIT_EVAL_FRACTION` no se validó en modelo exitoso |
| Patrones y hallazgos | Meses, zonas, horas UTC, anomalías y limitación de diciembre | `docs/INFORME_TECNICO.md` y página exploratoria |
| Ingeniería de características | Distancia, pasajeros, fecha, proveedor, origen y destino | `docs/MODELADO.md`; interpretación a posteriori |
| Definición de objetivos | Tarifa en USD y etiqueta de tarifa elevada desde USD 20 | SQL y documentación del modelado |
| Visualización y predicciones | Tres páginas del dashboard, dos modelos y pronóstico rolling-origin | [Informe visual](https://datastudio.google.com/reporting/45e788e9-a2c3-4606-8721-4ba456c08a19) |
| Rolling Forecast | 23 pronósticos a un día y referencia histórica | `docs/RESULTADOS_ROLLING_FORECAST_20261027.md`; modelos fijos |

La evidencia disponible incluye consultas y logs ejecutados, así como capturas del dashboard. La captura de la tercera página incluida inicialmente corresponde al editor; el acceso desde una identidad distinta de la propietaria y las capturas de consola de BigQuery no constan como verificaciones independientes en los materiales disponibles. Estas ausencias son limitaciones del conjunto de evidencias, no resultados inventados.
