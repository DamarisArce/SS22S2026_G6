# Síntesis de resultados experimentales

**Fecha de consolidación:** 27 de octubre de 2026.

## Fuente, depuración y optimización

| Indicador | Valor observado |
|---|---:|
| Registros de la fuente pública | 36,256,539 |
| Registros en cada tabla comparable | 35,526,984 |
| Bytes procesados en consulta estándar | 1,024,262,123 |
| Bytes procesados en consulta optimizada | 93,941,224 |
| Reducción porcentual de lectura | 90.83 % |
| Filas de la muestra BigQuery ML | 70,753 |
| Registros del conjunto de prueba | 6,449 |

El benchmark produjo resultados equivalentes en 138,162 viajes y suma tarifaria 1,722,680.9. Las mediciones corresponden a trabajos con caché no utilizada. En el análisis de calidad identificamos datos atípicos y cobertura temporal insuficiente en diciembre; no interpretamos las categorías de anomalías como mutuamente excluyentes.

## Evaluación de modelos

| Indicador | Valor |
|---|---:|
| MAE lineal | USD 4.9459 |
| RMSE lineal | USD 7.3220 |
| R² lineal | 0.6920 |
| Accuracy logística | 91.2545 % |
| F1 logística | 75.1542 % |
| ROC-AUC logística | 0.9062 |

Al transformar la predicción lineal en clasificación con umbral de USD 20, su F1 fue de 73.0700 %, frente a 75.1542 % del modelo logístico. La comparación se efectuó sobre los mismos 6,449 viajes de noviembre. La matriz logística presentó 5,032 verdaderos negativos, 133 falsos positivos, 431 falsos negativos y 853 verdaderos positivos.

## Rolling Forecast

Entre el 8 y el 30 de noviembre se evaluaron 23 pronósticos diarios con siete días históricos y horizonte de un día. El MAE de la referencia histórica fue **2.2079 pp**, frente a **5.2465 pp** de logística y **5.9523 pp** de lineal. La referencia histórica fue la más precisa de las tres aproximaciones para este objetivo agregado.

## Fuentes documentales

Las salidas registradas en `evidencias/logs/20261026_145616_estadisticas.log`, `metricas_modelos_resultado.json`, `recuperacion_predicciones_v2.log` y `rolling_forecast_20261027.log` sustentan las cifras centrales. El [informe técnico](INFORME_TECNICO.md) expone la interpretación y las limitaciones correspondientes.
