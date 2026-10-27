-- Proyecto 2, Grupo 6: rolling-origin forecasting (backtesting ex post).
-- Horizonte = 1 dia. Ventana = 7 dias CALENDARIO anteriores al objetivo.
-- Cada pronostico usa UNICAMENTE predicciones de viajes ya observados
-- hasta la fecha_origen (dia anterior a fecha_pronosticada).
-- Nunca se incluyen el dia objetivo ni fechas posteriores en el calculo.
-- Se reutilizan las predicciones de dos modelos BigQuery ML entrenados
-- antes de noviembre; NO hay reentrenamiento ni atributos futuros.
-- La tasa diaria observada se usa SOLO como etiqueta para evaluar despues.
CREATE VIEW IF NOT EXISTS `__PROJECT_ID__.__DATASET__.vw_forecast_origen_movil`
OPTIONS(description='Backtesting rolling-origin de un dia: siete dias previos de predicciones ML, noviembre 2022') AS
WITH diarios AS (
  SELECT
    pickup_date AS fecha_pronosticada,
    COUNT(*) AS viajes_objetivo,
    COUNTIF(clase_real = 1) AS positivos_reales,
    COUNTIF(clase_lineal = 1) AS positivos_lineal,
    COUNTIF(clase_logistica = 1) AS positivos_logistica
  FROM `__PROJECT_ID__.__DATASET__.predicciones_comparadas`
  WHERE pickup_date >= DATE '2022-11-01'
    AND pickup_date < DATE '2022-12-01'
  GROUP BY pickup_date
), ventanas AS (
  SELECT
    *,
    DATE_SUB(fecha_pronosticada, INTERVAL 1 DAY) AS fecha_origen,
    COUNT(*) OVER w AS dias_historial,
    MIN(fecha_pronosticada) OVER w AS inicio_historial,
    MAX(fecha_pronosticada) OVER w AS fin_historial,
    SUM(viajes_objetivo) OVER w AS viajes_historial,
    SUM(positivos_lineal) OVER w AS predichos_lineal_historial,
    SUM(positivos_logistica) OVER w AS predichos_logistica_historial,
    SUM(positivos_reales) OVER w AS positivos_reales_historial
  FROM diarios
  WINDOW w AS (
    ORDER BY fecha_pronosticada
    ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
  )
)
SELECT
  fecha_origen,
  fecha_pronosticada,
  inicio_historial,
  fin_historial,
  dias_historial,
  1 AS horizonte_dias,
  viajes_historial,
  viajes_objetivo,
  SAFE_DIVIDE(positivos_reales, viajes_objetivo) AS tasa_real,
  SAFE_DIVIDE(predichos_lineal_historial, viajes_historial) AS pronostico_lineal,
  SAFE_DIVIDE(predichos_logistica_historial, viajes_historial) AS pronostico_logistico,
  SAFE_DIVIDE(positivos_reales_historial, viajes_historial) AS referencia_historica
FROM ventanas
WHERE dias_historial = 7
  AND inicio_historial = DATE_SUB(fecha_pronosticada, INTERVAL 7 DAY)
  AND fin_historial = DATE_SUB(fecha_pronosticada, INTERVAL 1 DAY)
  AND fecha_pronosticada >= DATE '2022-11-08'
  AND fecha_pronosticada < DATE '2022-12-01';
