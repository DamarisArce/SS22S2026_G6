# Evaluación de optimización de consultas en BigQuery

**Fecha de medición:** 26 de octubre de 2026. **Región:** US. **Dataset:** `ss2_proyecto2_g6`.

## Diseño experimental

Comparamos una tabla analítica estándar (`viajes_base`) contra una versión particionada por fecha y clusterizada por ubicación (`viajes_optimizada`). Ambas tablas contenían 35,526,984 registros y coincidieron en los conteos y sumas comprobados. Se aplicaron consultas analíticas equivalentes, con caché deshabilitada para reducir su influencia en la comparación.

## Resultados observados

| Indicador | Estándar | Optimizada |
|---|---:|---:|
| Identificador de trabajo | `bqjob_r58c2a24881982a4b_000001a179ffeecd_1` | `bqjob_r9bdf5031031d141_000001a179fffd56_1` |
| Bytes procesados | 1,024,262,123 | 93,941,224 |
| Bytes facturables reportados | 1,024,458,752 | 94,371,840 |
| Duración | 321 ms | 305 ms |
| Slot-ms | 5,166 | 257 |
| Uso de caché | No | No |
| Viajes en el resultado | 138,162 | 138,162 |
| Suma de tarifas | 1,722,680.9 | 1,722,680.9 |

La reducción de bytes procesados fue de **90.83 %**. La latencia disminuyó aproximadamente un 4.98 %, diferencia mucho menor que la reducción de lectura. La disminución de slot-ms también fue sustancial en estos dos trabajos, aunque no se interpreta como una promesa de ahorro idéntico para cualquier consulta.

## Interpretación

El filtrado por fecha es coherente con el particionamiento y la consulta por origen y destino aprovecha el esquema de clustering. En el caso observado, esta organización permitió obtener el mismo resultado analítico con menor volumen de datos leídos. El número de bytes facturables no expresa por sí mismo un importe monetario cobrado: el cargo real depende del modelo de precios y de las condiciones de facturación de la cuenta.

## Trazabilidad

Los registros disponibles incluyen `evidencias/logs/20261026_145616_estadisticas.log` y las consultas `sql/03_optimizacion/03_benchmark_base.sql` y `04_benchmark_optimizada.sql`. Los identificadores de trabajo permiten relacionar las mediciones con sus respectivas ejecuciones en BigQuery.
