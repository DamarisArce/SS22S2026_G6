-- Evaluacion externa (noviembre). No pertenece a ningun CREATE MODEL.
-- Metrica distinta por tarea, por ello los campos que no aplican quedan NULL.
CREATE OR REPLACE TABLE `__PROJECT_ID__.__DATASET__.metricas_modelos` AS
SELECT
  'LINEAL' AS modelo, 'REGRESION' AS tarea,
  CAST(mean_absolute_error AS FLOAT64) AS mae,
  CAST(SQRT(mean_squared_error) AS FLOAT64) AS rmse,
  CAST(mean_squared_error AS FLOAT64) AS mse,
  CAST(r2_score AS FLOAT64) AS r2,
  CAST(NULL AS FLOAT64) AS precision,
  CAST(NULL AS FLOAT64) AS recall,
  CAST(NULL AS FLOAT64) AS accuracy,
  CAST(NULL AS FLOAT64) AS f1,
  CAST(NULL AS FLOAT64) AS roc_auc,
  CAST(NULL AS FLOAT64) AS log_loss
FROM ML.EVALUATE(MODEL `__PROJECT_ID__.__DATASET__.modelo_lineal`, (
  SELECT tarifa, distancia_millas, pasajeros, hora_utc, dia_semana_utc,
         mes_utc, proveedor, origen, destino
  FROM `__PROJECT_ID__.__DATASET__.datos_ml`
  WHERE pickup_date >= DATE '2022-11-01'
    AND pickup_date < DATE '2022-12-01'
))
UNION ALL
SELECT
  'LOGISTICA' AS modelo, 'CLASIFICACION' AS tarea,
  CAST(NULL AS FLOAT64),CAST(NULL AS FLOAT64),
  CAST(NULL AS FLOAT64),CAST(NULL AS FLOAT64),
  CAST(precision AS FLOAT64),
  CAST(recall AS FLOAT64),
  CAST(accuracy AS FLOAT64),
  CAST(f1_score AS FLOAT64),
  CAST(roc_auc AS FLOAT64),
  CAST(log_loss AS FLOAT64)
FROM ML.EVALUATE(MODEL `__PROJECT_ID__.__DATASET__.modelo_logistico`, (
  SELECT
    IF(tarifa >= 20.0, 1, 0) AS tarifa_alta,
    distancia_millas, pasajeros, hora_utc, dia_semana_utc,
    mes_utc, proveedor, origen, destino
  FROM `__PROJECT_ID__.__DATASET__.datos_ml`
  WHERE pickup_date >= DATE '2022-11-01'
    AND pickup_date < DATE '2022-12-01'
));

CREATE OR REPLACE TABLE `__PROJECT_ID__.__DATASET__.matriz_confusion_logistica` AS
SELECT *
FROM ML.CONFUSION_MATRIX(MODEL `__PROJECT_ID__.__DATASET__.modelo_logistico`, (
  SELECT
    IF(tarifa >= 20.0, 1, 0) AS tarifa_alta,
    distancia_millas, pasajeros, hora_utc, dia_semana_utc,
    mes_utc, proveedor, origen, destino
  FROM `__PROJECT_ID__.__DATASET__.datos_ml`
  WHERE pickup_date >= DATE '2022-11-01'
    AND pickup_date < DATE '2022-12-01'
));
