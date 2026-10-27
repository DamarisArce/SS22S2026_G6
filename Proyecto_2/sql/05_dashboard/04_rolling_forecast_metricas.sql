-- Evaluacion uniforme de pronosticos rolling-origin a un dia.
-- Comparar MAE y RMSE expresados en puntos porcentuales (pp).
-- La referencia historica usa la tasa REAL de los siete dias ANTERIORES;
-- es un baseline causal, NO un tercer modelo BigQuery ML.
CREATE VIEW IF NOT EXISTS `__PROJECT_ID__.__DATASET__.vw_forecast_metricas`
OPTIONS(description='Metricas de rolling forecast a un dia: lineal, logistica y baseline historico') AS
WITH pronosticos AS (
  SELECT
    fecha_pronosticada, tasa_real,
    'LINEAL' AS modelo, pronostico_lineal AS tasa_pronosticada
  FROM `__PROJECT_ID__.__DATASET__.vw_forecast_origen_movil`
  UNION ALL
  SELECT
    fecha_pronosticada, tasa_real,
    'LOGISTICA' AS modelo, pronostico_logistico AS tasa_pronosticada
  FROM `__PROJECT_ID__.__DATASET__.vw_forecast_origen_movil`
  UNION ALL
  SELECT
    fecha_pronosticada, tasa_real,
    'BASELINE_HISTORICO' AS modelo, referencia_historica AS tasa_pronosticada
  FROM `__PROJECT_ID__.__DATASET__.vw_forecast_origen_movil`
)
SELECT
  modelo,
  COUNT(*) AS dias_evaluados,
  MIN(fecha_pronosticada) AS primera_fecha,
  MAX(fecha_pronosticada) AS ultima_fecha,
  ROUND(AVG(ABS(tasa_pronosticada - tasa_real))*100, 4) AS mae_puntos_porcentuales,
  ROUND(SQRT(AVG(POW(tasa_pronosticada - tasa_real, 2)))*100, 4) AS rmse_puntos_porcentuales,
  ROUND(AVG(tasa_pronosticada - tasa_real)*100, 4) AS sesgo_puntos_porcentuales
FROM pronosticos
GROUP BY modelo;
