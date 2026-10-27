# Evidencias visuales de BigQuery y del modelado predictivo

**Seminario de Sistemas 2 · Proyecto 2 · Grupo 6 · 27 de octubre de 2026**

## Alcance de la evidencia

Registramos la configuración de las tablas analíticas, las opciones de entrenamiento de BigQuery ML, las métricas de evaluación y la existencia de las predicciones del conjunto de prueba. Las capturas corresponden a la consola del proyecto `ss2-p2-g6-2026-nc-1026`, dataset `ss2_proyecto2_g6`, y se conservan sin alteraciones de contenido.

## Transformaciones y optimización

La captura [Particionamiento y clustering](../evidencias/capturas/bigquery_tabla_particiones_clustering_20261027.png) muestra `viajes_optimizada`, particionada por día sobre `pickup_date`, con agrupamiento por `pickup_location_id` y `dropoff_location_id` y filtro de partición obligatorio.

Recuperamos los trabajos originales del 26 de octubre de 2026, ejecutados sobre datos equivalentes con caché desactivada:

| Indicador | Consulta estándar | Consulta optimizada |
|---|---:|---:|
| Bytes procesados, valor exacto de los trabajos | 1,024,262,123 | 93,941,224 |
| Bytes facturables, valor exacto de los trabajos | 1,024,458,752 | 94,371,840 |
| Duración | 321 ms | 305 ms |
| Slot-ms | 5,166 | 257 |
| ID de trabajo | `bqjob_r58c2a24881982a4b_000001a179ffeecd_1` | `bqjob_r9bdf5031031d141_000001a179fffd56_1` |

La disminución de bytes procesados fue **90.83 %**. La consola presenta volúmenes redondeados de **976.81 MB** y **89.59 MB**, respectivamente, cuya escala visual corresponde a los bytes exactos anteriores expresados en unidades binarias. La latencia observada cambió de 321 a 305 ms; interpretamos el principal beneficio como una reducción de lectura y trabajo de cómputo.

- [Captura del trabajo estándar](../evidencias/capturas/bigquery_benchmark_estandar_20261027.png).
- [Captura del trabajo optimizado](../evidencias/capturas/bigquery_benchmark_optimizada_20261027.png).

## Modelos y evaluación

Las capturas del conjunto de datos evidencian los modelos `modelo_lineal`, `modelo_logistico`, `modelo_lineal_custom_l2_1` y `modelo_lineal_seq_eval20`, además del recurso `modelo_arbol`, que **no se utiliza como resultado válido** porque su entrenamiento no finalizó satisfactoriamente.

- [Esquema y explorador de modelos](../evidencias/capturas/bigquery_esquema_y_modelos_20261027.png).
- [Modelo lineal con evaluación secuencial de 20 % y regularización L2 de 0.1](../evidencias/capturas/bigquery_modelo_seq_eval20_20261027.png).
- [Modelo lineal con split personalizado y regularización L2 de 1.0](../evidencias/capturas/bigquery_modelo_custom_l2_1_20261027.png).
- [Métricas de los dos modelos principales](../evidencias/capturas/bigquery_metricas_modelos_20261027.png).

Sobre los mismos 6,449 viajes externos de noviembre, la comparación adicional de los tres modelos lineales produjo:

| Variante | MAE (USD) | RMSE (USD) | R² |
|---|---:|---:|---:|
| Original, CUSTOM, L2=0.1 | 4.94586 | 7.32200 | 0.69204 |
| CUSTOM, L2=1.0 | 4.95013 | 7.31267 | 0.69282 |
| SEQ, evaluación 20 %, L2=0.1 | 4.94262 | 7.32104 | 0.69212 |

La variante secuencial obtuvo menor MAE; el modelo CUSTOM con L2=1.0 obtuvo menor RMSE y mayor R². Las diferencias observadas son pequeñas y no establecemos significancia estadística con esta única evaluación.

## Predicciones fuera de muestra

La tabla `predicciones_comparadas` registra **6,449 filas** de noviembre de 2022, con el valor monetario real, la predicción lineal, las clases comparadas y la probabilidad de tarifa elevada.

- [Metadatos y cantidad de registros](../evidencias/capturas/bigquery_predicciones_comparadas_detalles_20261027.png).
- [Vista previa de las predicciones](../evidencias/capturas/bigquery_predicciones_comparadas_vista_previa_20261027.png).

La evaluación detallada, la estrategia temporal, las limitaciones de disponibilidad de variables y la interpretación de métricas se encuentran en el informe técnico y en el informe de experimentos.
