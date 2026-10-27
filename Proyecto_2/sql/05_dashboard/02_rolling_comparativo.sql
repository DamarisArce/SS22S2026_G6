-- Comparación temporal de dos modelos sobre TEST independiente.
-- Ventana móvil de 7 días; NO se reentrenan los modelos.
CREATE VIEW IF NOT EXISTS
  `__PROJECT_ID__.__DATASET__.vw_rolling_comparativo`
OPTIONS(
  description='Predicciones fuera de muestra con ventana movil de 7 dias'
) AS
WITH diarios AS (
  SELECT
    pickup_date,
    COUNT(*) AS viajes,
    COUNTIF(clase_real = 1) AS reales,
    COUNTIF(clase_lineal = 1) AS lineal,
    COUNTIF(clase_logistica = 1) AS logistica
  FROM `__PROJECT_ID__.__DATASET__.predicciones_comparadas`
  WHERE pickup_date >= DATE '2022-11-01'
    AND pickup_date < DATE '2022-12-01'
  GROUP BY pickup_date
)
SELECT
  pickup_date,
  viajes,
  ROUND(SAFE_DIVIDE(reales, viajes), 4) AS tasa_real_dia,
  ROUND(SAFE_DIVIDE(lineal, viajes), 4) AS tasa_lineal_dia,
  ROUND(SAFE_DIVIDE(logistica, viajes), 4) AS tasa_logistica_dia,
  ROUND(
    SAFE_DIVIDE(
      SUM(reales) OVER ventana,
      SUM(viajes) OVER ventana
    ), 4
  ) AS tasa_real_ma7,
  ROUND(
    SAFE_DIVIDE(
      SUM(lineal) OVER ventana,
      SUM(viajes) OVER ventana
    ), 4
  ) AS tasa_lineal_ma7,
  ROUND(
    SAFE_DIVIDE(
      SUM(logistica) OVER ventana,
      SUM(viajes) OVER ventana
    ), 4
  ) AS tasa_logistica_ma7
FROM diarios
WINDOW ventana AS (
  ORDER BY pickup_date
  ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
);
