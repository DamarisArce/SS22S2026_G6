# Proyecto 2 — Procesamiento y análisis de NYC Taxi Trips 2022

**Seminario de Sistemas 2 · Segundo semestre de 2026 · Grupo 6**

**Universidad de San Carlos de Guatemala — Facultad de Ingeniería**

**Integrantes:** Nelson Emanuel Cún Bálan (201222010) y Dámaris Magali Arce Guzmán (202006636).

## Resumen del proyecto

Desarrollamos un proceso de análisis de datos masivos sobre los viajes de taxis amarillos de Nueva York registrados en 2022. Utilizamos Google BigQuery para explorar y depurar los datos, optimizamos las consultas con particionamiento y clustering, entrenamos dos modelos predictivos en BigQuery ML y presentamos los hallazgos en un informe interactivo de Data Studio (Looker Studio).

**[Consultar el informe visual — NYC Taxi Trips 2022, Grupo 6](https://datastudio.google.com/reporting/45e788e9-a2c3-4606-8721-4ba456c08a19)**

El informe está organizado en tres secciones: análisis exploratorio, evaluación de modelos BigQuery ML y pronóstico temporal con origen móvil (*Rolling Forecast*). El acceso depende de los permisos otorgados al informe y a sus fuentes.

## Datos y preparación

La fuente fue `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022`, alojada en BigQuery. Identificamos **36,256,539 registros** en la tabla pública y obtuvimos **35,526,984 viajes** en cada una de las tablas de análisis `viajes_base` y `viajes_optimizada`. La depuración consideró coherencia temporal, distancias y valores monetarios. Detectamos, entre otras anomalías, 511,442 distancias no positivas y 241,621 tarifas no positivas; las categorías pueden superponerse.

El análisis temporal abarca principalmente de enero a noviembre de 2022. La fuente presentó cobertura insuficiente de diciembre bajo las reglas de exploración, por lo que no interpretamos ese mes como representativo.

## Optimización de consultas

La tabla `viajes_optimizada` se particionó por `pickup_date` y se organizó mediante clustering por `pickup_location_id` y `dropoff_location_id`. Comparamos consultas equivalentes con caché desactivada y resultados idénticos:

| Indicador | Tabla estándar | Tabla optimizada |
|---|---:|---:|
| Bytes procesados | 1,024,262,123 | 93,941,224 |
| Duración observada | 321 ms | 305 ms |
| Slot-ms | 5,166 | 257 |
| Registros del resultado | 138,162 | 138,162 |

La optimización redujo **90.83 % de los bytes procesados**. El resultado demuestra principalmente un menor volumen de lectura, no una reducción proporcional en el tiempo de respuesta. La evidencia detallada se presenta en [Validación de benchmark](docs/VALIDACION_BENCHMARK_20261026.md).

## Modelos predictivos

A partir de una muestra materializada de **70,753 viajes**, establecimos una división temporal: enero-agosto para entrenamiento, septiembre-octubre para validación y noviembre para prueba independiente (**6,449 viajes**). Ambos modelos exitosos emplean `DATA_SPLIT_METHOD='CUSTOM'`; la prueba de noviembre no participó en el ajuste.

- **Regresión lineal (`LINEAR_REG`):** estima la tarifa monetaria. MAE de **USD 4.9459**, RMSE de **USD 7.3220** y R² de **0.6920**.
- **Regresión logística (`LOGISTIC_REG`):** identifica viajes con tarifa de al menos USD 20. Accuracy de **91.25 %**, F1 de **75.15 %** y ROC-AUC de **0.9062**.

Para comparar ambos algoritmos sobre una tarea común, transformamos la estimación lineal en una clase binaria con el mismo umbral. La clasificación logística logró F1 de **75.15 %**, frente a **73.07 %** de la lineal discretizada.

Este modelado utiliza distancia recorrida y destino observados; su interpretación es la **evaluación de viajes concluidos**, no la predicción anticipada del precio antes de realizar el recorrido. La metodología y las limitaciones se detallan en [Modelado BigQuery ML](docs/MODELADO.md).

## Rolling Forecast

Implementamos una evaluación retrospectiva con origen móvil para pronosticar la proporción diaria de viajes con tarifa de al menos USD 20. Se utilizaron **siete días históricos**, un horizonte de **un día** y **23 pronósticos** entre el 8 y el 30 de noviembre. El pronóstico de cada fecha se calculó exclusivamente con información de días anteriores; los modelos BigQuery ML permanecieron fijos.

| Método | MAE (puntos porcentuales) | RMSE (puntos porcentuales) |
|---|---:|---:|
| Referencia histórica | **2.2079** | **2.5633** |
| Logística | 5.2465 | 5.7875 |
| Lineal | 5.9523 | 6.4231 |

El método histórico superó a los pronósticos construidos a partir de las clasificaciones ML. Esto pone de manifiesto que la calidad de una clasificación individual no garantiza precisión al pronosticar proporciones agregadas. La evaluación corresponde a la muestra de prueba y no implica reentrenamiento diario. Véanse la [metodología de origen móvil](docs/ROLLING_FORECAST_ORIGEN_MOVIL_20261027.md) y sus [resultados](docs/RESULTADOS_ROLLING_FORECAST_20261027.md).

## Informe visual y organización del repositorio

El tablero reúne las distribuciones mensuales, las zonas de origen y los patrones horarios (UTC); las estimaciones y métricas de ML; y el pronóstico temporal con su referencia histórica. Su estructura y fuentes se describen en [Informe visual](docs/DASHBOARD.md).

| Ubicación | Contenido |
|---|---|
| `sql/01_exploracion/` | Consultas de calidad y exploración estadística |
| `sql/02_transformaciones/` | Depuración y tabla analítica estándar |
| `sql/03_optimizacion/` | Tabla particionada, clustering y consultas de comparación |
| `sql/04_bigquery_ml/` | Muestreo, división temporal, modelos, evaluación y predicciones |
| `sql/05_dashboard/` | Agregados y vistas para el informe interactivo |
| `docs/` | Informe técnico, metodología, resultados y trazabilidad |
| `evidencias/` | Capturas disponibles y registros de ejecución |

El [informe técnico completo](docs/INFORME_TECNICO.md) integra la metodología, decisiones, análisis y conclusiones. La [trazabilidad de requisitos](docs/MATRIZ_RUBRICA.md) identifica evidencia disponible y limitaciones comprobadas.

## Alcance de los resultados

La evaluación externa de los modelos se realizó sobre la muestra de noviembre. El proceso no incluyó una búsqueda experimental de varias configuraciones de hiperparámetros exitosamente entrenadas. Un intento alternativo con Boosted Tree se interrumpió por límites de bytes facturables, por lo que sus resultados no se utilizan como evidencia de un tercer modelo. El dashboard presenta un *Rolling Forecast* retrospectivo con origen móvil y modelos fijos; no representa pronósticos operativos sobre viajes futuros desconocidos.
