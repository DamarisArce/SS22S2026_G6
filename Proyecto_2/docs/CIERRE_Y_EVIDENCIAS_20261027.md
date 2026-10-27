# Registro de evidencias y verificabilidad

**Corte de documentación:** 27 de octubre de 2026.

## Alcance ejecutado

El desarrollo comprende exploración de la fuente pública, creación de tablas comparables, optimización mediante particiones y clustering, dos modelos BigQuery ML, evaluación sobre un conjunto temporal independiente, predicciones materializadas y un dashboard de tres páginas con Rolling Forecast retrospectivo.

## Registros técnicos disponibles

| Evidencia | Archivo o referencia | Resultado que sustenta |
|---|---|---|
| Control de calidad de la fuente | `evidencias/logs/20261026_135201_calidad.log` | Conteos y anomalías de origen |
| Exploración temporal | `evidencias/logs/20261026_135205_exploracion.log` | Distribución mensual y otros agregados |
| Equivalencia de tablas | `evidencias/logs/20261026_135946_igualdad.log` | Conteos y sumas consistentes |
| Benchmark | `evidencias/logs/20261026_145616_estadisticas.log` | Bytes, latencia, uso de caché y trabajos |
| División de datos | `evidencias/logs/20261026_152700_splits.log` | Entrenamiento, validación y prueba |
| Modelos | Logs `modelo_lineal` y `modelo_logistico` | Creación de dos modelos distintos |
| Evaluación | `evidencias/logs/metricas_modelos_resultado.json` | Métricas externas y modelos |
| Matriz de confusión | `evidencias/logs/matriz_confusion_resultado.json` | TN, FP, FN y TP de la logística |
| Predicciones | `evidencias/logs/recuperacion_predicciones_v2.log` | Cuatro tablas de resultados creadas |
| Fuentes del dashboard | `evidencias/logs/preparacion_dashboard.log` | Tabla agregada y vistas |
| Rolling Forecast | `evidencias/logs/rolling_forecast_20261027.log` | 23 pronósticos y errores observados |

## Informe visual

Las capturas `dashboard_01_exploracion.png` y `dashboard_02_modelos_bqml.png` documentan las dos primeras páginas. `dashboard_03_rolling_forecast_editor.png` documenta la tercera página durante la edición. Las capturas muestran series y tablas generadas desde las vistas BigQuery, pero no sustituyen el examen de los trabajos y esquemas de BigQuery.

**Informe publicado:** https://datastudio.google.com/reporting/45e788e9-a2c3-4606-8721-4ba456c08a19

## Límites del material disponible

En el expediente utilizado para consolidar esta documentación no figuran capturas independientes de consola que muestren el esquema completo de particiones, los trabajos de benchmark, los metadatos de ambos modelos y las evaluaciones. Tampoco hay constancia verificable de acceso al informe desde una cuenta distinta de la propietaria. Estos elementos se distinguen de las operaciones SQL, que sí cuentan con salidas registradas.

La evidencia de `DATA_SPLIT_EVAL_FRACTION` no corresponde a un entrenamiento finalizado. El ajuste de hiperparámetros está representado por configuraciones seleccionadas explícitamente, no por una búsqueda experimental exhaustiva. El pronóstico temporal representa un origen móvil con modelos fijos.
