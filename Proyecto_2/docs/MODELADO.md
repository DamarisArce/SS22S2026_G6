# Modelado predictivo con BigQuery ML

## Objetivo del modelado

Planteamos dos tareas complementarias sobre viajes ya concluidos: estimar la tarifa monetaria mediante regresión lineal y clasificar los viajes según si la tarifa alcanza USD 20 mediante regresión logística. La elección de modelos distintos permitió evaluar tanto error numérico como calidad de clasificación, sin confundir las métricas propias de cada tarea.

## Población analítica y separación temporal

Las tablas derivadas contienen 35,526,984 viajes. Para entrenar BigQuery ML seleccionamos 70,753 registros mediante una muestra determinista aproximada de 0.2 %, materializada en `datos_ml`. El período se dividió cronológicamente:

| Subconjunto | Fechas | Registros originales | Registros utilizados por el modelo |
|---|---|---:|---:|
| Entrenamiento | enero-agosto 2022 | 51,204 | 51,199 |
| Validación | septiembre-octubre 2022 | 13,100 | 13,096 |
| Prueba externa | noviembre 2022 | 6,449 | 6,449 |

El análisis de valores extremos en entrenamiento llevó a excluir del entrenamiento y de la validación tarifas fuera del rango USD 2–250. El conjunto TEST permaneció completo. Ambos modelos emplearon `DATA_SPLIT_METHOD='CUSTOM'` y `DATA_SPLIT_COL='es_validacion'`; noviembre se reservó exclusivamente para inferencia y evaluación externa.

## Variables y riesgos de información

Las entradas fueron distancia en millas, pasajeros, hora UTC, día de semana UTC, mes, proveedor, zona de origen y zona de destino. No se utilizaron importes totales, propinas ni variables monetarias derivadas de la tarifa como predictores. Los valores de pasajeros desconocidos se representaron con cero en la preparación original, decisión que puede confundir información faltante con ausencia real de pasajeros.

La distancia registrada y la zona de destino pueden conocerse plenamente solo tras concluir el recorrido. Por tanto, la estimación a nivel viaje es retrospectiva, útil para analizar y auditar tarifas, no una predicción ex ante garantizada. La división temporal previene el uso directo de noviembre en el entrenamiento, aunque no elimina por sí sola las restricciones de disponibilidad de características en un eventual sistema operativo.

## Configuraciones evaluadas

| Algoritmo | Tipo BigQuery ML | Objetivo | Parámetros implementados |
|---|---|---|---|
| Regresión lineal | `LINEAR_REG` | `tarifa` en USD | `MAX_ITERATIONS=30`, `L2_REG=0.1` |
| Regresión logística | `LOGISTIC_REG` | `tarifa_alta` (USD 20 o más) | `MAX_ITERATIONS=20`, `L2_REG=0.1`, `EARLY_STOP=TRUE` |

Se configuró una alternativa `BOOSTED_TREE_REGRESSOR` con separación secuencial y `DATA_SPLIT_EVAL_FRACTION=0.2`, pero los trabajos de entrenamiento correspondientes finalizaron con error por límite de bytes facturables. Ese modelo no se considera entrenado ni evaluado. Los dos modelos exitosos utilizan división `CUSTOM`; tampoco se realizó una comparación empírica de múltiples configuraciones exitosas de un mismo algoritmo.

## Evaluación externa de noviembre

| Métrica | Regresión lineal |
|---|---:|
| MAE (USD) | 4.9459 |
| MSE | 53.6117 |
| RMSE (USD) | 7.3220 |
| R² | 0.6920 |

| Métrica | Regresión logística |
|---|---:|
| Accuracy | 91.2545 % |
| Precision | 86.5112 % |
| Recall | 66.4330 % |
| F1 | 75.1542 % |
| ROC-AUC | 0.9062 |
| Log loss | 0.2652 |

La matriz logística comprende TN = 5,032; FP = 133; FN = 431; TP = 853. Para una comparación bajo el mismo objetivo convertimos la tarifa estimada por el modelo lineal a clasificación binaria con umbral de USD 20. Esta conversión produjo F1 de 73.07 %, frente a 75.15 % del modelo logístico; el modelo lineal discretizado obtuvo 130 falsos positivos, frente a 133 del logístico.

## Interpretación

La regresión logística identifica más casos positivos reales y mejora ligeramente la F1 en la tarea binaria. La regresión lineal proporciona una predicción monetaria en dólares. Los modelos subestiman la tasa agregada de positivos en el conjunto de prueba, circunstancia que se analiza adicionalmente en la evaluación de pronóstico temporal. Los resultados proceden de 6,449 viajes de muestra y no permiten inferir, sin estudios adicionales, el mismo error para toda la población anual.
