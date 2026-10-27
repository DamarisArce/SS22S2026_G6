-- Predicciones de TEST independiente en noviembre de 2022, sin reentrenar.
-- La regresion devuelve tarifa estimada; la logistica, clase y probabilidad de >= USD 20.
CREATE OR REPLACE TABLE `__PROJECT_ID__.__DATASET__.predicciones_lineal` AS
SELECT id_registro, pickup_date, tarifa AS valor_real,
       CAST(predicted_tarifa AS FLOAT64) AS prediccion,
       ABS(CAST(predicted_tarifa AS FLOAT64) - tarifa) AS error_absoluto
FROM ML.PREDICT(MODEL `__PROJECT_ID__.__DATASET__.modelo_lineal`, (
  SELECT id_registro, pickup_date, tarifa, distancia_millas, pasajeros,
         hora_utc, dia_semana_utc, mes_utc, proveedor, origen, destino
  FROM `__PROJECT_ID__.__DATASET__.datos_ml`
  WHERE pickup_date >= DATE '2022-11-01'
    AND pickup_date < DATE '2022-12-01'
));

CREATE OR REPLACE TABLE `__PROJECT_ID__.__DATASET__.predicciones_logistica` AS
SELECT id_registro, pickup_date,
       CAST(predicted_tarifa_alta AS INT64) AS clase_predicha,
       (SELECT CAST(p.prob AS FLOAT64)
          FROM UNNEST(predicted_tarifa_alta_probs) AS p
         WHERE SAFE_CAST(p.label AS INT64) = 1 LIMIT 1) AS prob_tarifa_alta
FROM ML.PREDICT(MODEL `__PROJECT_ID__.__DATASET__.modelo_logistico`, (
  SELECT id_registro, pickup_date,
         IF(tarifa >= 20.0, 1, 0) AS tarifa_alta,
         distancia_millas, pasajeros, hora_utc, dia_semana_utc,
         mes_utc, proveedor, origen, destino
  FROM `__PROJECT_ID__.__DATASET__.datos_ml`
  WHERE pickup_date >= DATE '2022-11-01'
    AND pickup_date < DATE '2022-12-01'
));

CREATE OR REPLACE TABLE `__PROJECT_ID__.__DATASET__.predicciones_comparadas` AS
SELECT l.id_registro, l.pickup_date, l.valor_real,
       l.prediccion AS pred_lineal,
       l.error_absoluto AS error_lineal,
       IF(l.valor_real >= 20.0, 1, 0) AS clase_real,
       IF(l.prediccion >= 20.0, 1, 0) AS clase_lineal,
       g.clase_predicha AS clase_logistica,
       g.prob_tarifa_alta
FROM `__PROJECT_ID__.__DATASET__.predicciones_lineal` AS l
JOIN `__PROJECT_ID__.__DATASET__.predicciones_logistica` AS g
USING (id_registro, pickup_date);

-- Comparacion justa: las DOS predicciones sobre el MISMO objetivo binario y mismo TEST.
-- No comparar RMSE de regresion directamente con ROC_AUC de clasificacion.
CREATE OR REPLACE TABLE `__PROJECT_ID__.__DATASET__.metricas_comparacion_clasificacion` AS
WITH datos AS (
  SELECT 'LINEAL' AS modelo, clase_real, clase_lineal AS clase_predicha
  FROM `__PROJECT_ID__.__DATASET__.predicciones_comparadas`
  UNION ALL
  SELECT 'LOGISTICA', clase_real, clase_logistica
  FROM `__PROJECT_ID__.__DATASET__.predicciones_comparadas`
), conteos AS (
  SELECT modelo, COUNT(*) AS evaluados,
    COUNTIF(clase_real=1 AND clase_predicha=1) AS tp,
    COUNTIF(clase_real=0 AND clase_predicha=0) AS tn,
    COUNTIF(clase_real=0 AND clase_predicha=1) AS fp,
    COUNTIF(clase_real=1 AND clase_predicha=0) AS fn
  FROM datos GROUP BY modelo
)
SELECT modelo, evaluados, tp, tn, fp, fn,
  SAFE_DIVIDE(tp+tn, evaluados) AS accuracy,
  SAFE_DIVIDE(tp, tp+fp) AS precision,
  SAFE_DIVIDE(tp, tp+fn) AS recall,
  SAFE_DIVIDE(2*tp,2*tp+fp+fn) AS f1
FROM conteos;
