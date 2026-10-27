# Experimentos de separación temporal y regularización en BigQuery ML

**Seminario de Sistemas 2 — Proyecto 2 — Grupo 6**
**Fecha de ejecución y evaluación:** 27 de octubre de 2026.

## Propósito y metodología

Como ampliación del modelado predictivo de tarifas de taxis amarillos de Nueva York en 2022, comparamos tres regresiones lineales entrenadas mediante BigQuery ML. Mantuvimos constantes los predictores, la variable objetivo (`tarifa`, en USD), el límite de 30 iteraciones y los filtros de entrenamiento. Para analizar la regularización, modificamos únicamente `L2_REG` entre los dos modelos con split `CUSTOM`. Para analizar la estrategia de partición, contrastamos el modelo original con una variante de split secuencial `SEQ` que conservó `L2_REG=0.1` y empleó `DATA_SPLIT_EVAL_FRACTION=0.20`.

Todos los entrenamientos utilizaron observaciones anteriores al 1 de noviembre de 2022. La división `CUSTOM` separó entrenamiento (enero-agosto) y validación (septiembre-octubre); la división `SEQ` ordenó por `fecha_orden_split` y destinó el 20 % final a evaluación interna. BigQuery ML utiliza la columna de split para particionar los registros, no como predictor del modelo. El conjunto externo de prueba consistió en 6,449 viajes de noviembre de 2022 y permaneció excluido de todos los entrenamientos.

## Configuraciones completadas

| Modelo de BigQuery ML | Método de split | Fracción interna de evaluación | L2 | Iteraciones máximas |
|---|---|---|---:|---:|
| `modelo_lineal` | CUSTOM (`es_validacion`) | Definida por fechas, no por fracción | 0.1 | 30 |
| `modelo_lineal_custom_l2_1` | CUSTOM (`es_validacion`) | Definida por fechas, no por fracción | 1.0 | 30 |
| `modelo_lineal_seq_eval20` | SEQ (`fecha_orden_split`) | 0.20 | 0.1 | 30 |

Los tres modelos finalizaron correctamente y fueron evaluados mediante el mismo conjunto externo. La regresión logística `modelo_logistico` permanece como segundo algoritmo de la comparación principal del proyecto; no se modificó durante estos experimentos.

## Evaluación externa sobre noviembre

| Variante lineal | MAE (USD) ↓ | RMSE (USD) ↓ | R² ↑ |
|---|---:|---:|---:|
| Original: CUSTOM, L2=0.1 | 4.94586 | 7.32200 | 0.69204 |
| CUSTOM, L2=1.0 | 4.95013 | **7.31267** | **0.69282** |
| SEQ, evaluación=0.20, L2=0.1 | **4.94262** | 7.32104 | 0.69212 |

La configuración `SEQ` presentó el menor error absoluto promedio; la variante `CUSTOM` con regularización L2=1.0 produjo el menor RMSE y el mayor R². En términos absolutos, las diferencias entre las tres variantes fueron muy pequeñas. Este resultado no justifica afirmar superioridad estadística ni seleccionar un modelo definitivo mediante el conjunto de prueba. La elección de hiperparámetros para un uso productivo exigiría valorar sus métricas de validación y, preferiblemente, repetir experimentos temporales en varias ventanas.

La comparación entre los dos modelos `CUSTOM` aísla el cambio de regularización. La comparación entre los modelos original y `SEQ` examina la estrategia de split manteniendo los hiperparámetros, pero cambia los períodos efectivos de entrenamiento/validación; sus diferencias no pueden atribuirse de forma causal únicamente al algoritmo de particionado.

## Validación de integridad y prevención de fuga de información

- Los predictores no contienen la propia tarifa ni componentes monetarios derivados de ella.
- Se excluyó noviembre del SQL de entrenamiento para todas las configuraciones.
- Las métricas del informe proceden de la misma prueba externa de 6,449 viajes.
- Las variables distancia recorrida y destino observado corresponden a viajes concluidos; su uso restringe la interpretación a estimaciones retrospectivas, no a una predicción con información disponible antes de iniciar un viaje.
- `DATA_SPLIT_EVAL_FRACTION=0.20` quedó validado mediante un entrenamiento `SEQ` exitoso, además de la estrategia temporal `CUSTOM` ejecutada previamente.

## Evidencia reproducible

Las consultas del experimento se encuentran en `sql/04_bigquery_ml/07_lineal_custom_l2_1.sql`, `08_lineal_seq_eval20.sql` y `09_comparacion_experimentos.sql`. Los registros de entrenamiento y comparación de métricas corresponden a `evidencias/logs/20261027_entrenamiento_custom_l2_1.log`, `20261027_entrenamiento_seq_eval20.log` y `20261027_comparacion_modelos_lineales.log`. La configuración de tablas optimizadas se documenta mediante `evidencias/capturas/bigquery_tabla_particiones_clustering_20261027.png`.

## Conclusión

Los experimentos aportan evidencia ejecutada de división personalizada, división secuencial mediante `DATA_SPLIT_EVAL_FRACTION`, evaluación independiente y variación controlada de regularización. Los resultados confirman desempeños externos próximos entre sí; la configuración más conveniente depende de la métrica seleccionada y de la evidencia adicional de validación, no solo del mínimo de una métrica en el conjunto de prueba.
