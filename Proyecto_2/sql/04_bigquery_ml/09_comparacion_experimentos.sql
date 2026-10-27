-- Comparacion justa: los tres modelos sobre el MISMO conjunto externo TEST: noviembre.
-- No modifica tablas ni modelos. Solo lectura de metricas existentes y ML.EVALUATE.
WITH metricas AS (
  SELECT
    'LINEAL_ORIGINAL_CUSTOM_L2_0_1' AS modelo,
    CAST(mae AS FLOAT64) AS mae_usd,
    CAST(rmse AS FLOAT64) AS rmse_usd,
    CAST(r2 AS FLOAT64) AS r2
  FROM `__PROJECT_ID__.__DATASET__.metricas_modelos`
  WHERE modelo='LINEAL'
  UNION ALL
  SELECT 'LINEAL_CUSTOM_L2_1_0',
    CAST(mean_absolute_error AS FLOAT64),
    SQRT(CAST(mean_squared_error AS FLOAT64)),
    CAST(r2_score AS FLOAT64)
  FROM ML.EVALUATE(MODEL `__PROJECT_ID__.__DATASET__.modelo_lineal_custom_l2_1`, (
    SELECT tarifa, distancia_millas, pasajeros, hora_utc, dia_semana_utc,
      mes_utc, proveedor, origen, destino
    FROM `__PROJECT_ID__.__DATASET__.datos_ml`
    WHERE pickup_date >= DATE '2022-11-01'
      AND pickup_date < DATE '2022-12-01'
  ))
  UNION ALL
  SELECT 'LINEAL_SEQ_EVAL20_L2_0_1',
    CAST(mean_absolute_error AS FLOAT64),
    SQRT(CAST(mean_squared_error AS FLOAT64)),
    CAST(r2_score AS FLOAT64)
  FROM ML.EVALUATE(MODEL `__PROJECT_ID__.__DATASET__.modelo_lineal_seq_eval20`, (
    SELECT tarifa, distancia_millas, pasajeros, hora_utc, dia_semana_utc,
      mes_utc, proveedor, origen, destino
    FROM `__PROJECT_ID__.__DATASET__.datos_ml`
    WHERE pickup_date >= DATE '2022-11-01'
      AND pickup_date < DATE '2022-12-01'
  ))
)
SELECT modelo, ROUND(mae_usd, 5) AS mae_usd,
  ROUND(rmse_usd, 5) AS rmse_usd,
  ROUND(r2, 5) AS r2
FROM metricas
ORDER BY mae_usd, modelo;
