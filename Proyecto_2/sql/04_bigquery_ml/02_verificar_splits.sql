-- Verifica tamaños de entrenamiento/validación/test por fecha UTC.
SELECT
  CASE WHEN pickup_date < DATE '2022-09-01' THEN 'TRAIN'
       WHEN pickup_date < DATE '2022-11-01' THEN 'VALIDACION'
       ELSE 'TEST' END AS split,
  COUNT(*) AS filas, MIN(pickup_date) AS desde, MAX(pickup_date) AS hasta,
  MIN(tarifa) AS minima_tarifa,MAX(tarifa) AS maxima_tarifa
FROM `__PROJECT_ID__.__DATASET__.datos_ml`
WHERE pickup_date >= DATE '2022-01-01' AND pickup_date < DATE '2022-12-01'
GROUP BY 1 ORDER BY CASE split WHEN 'TRAIN' THEN 1 WHEN 'VALIDACION' THEN 2 ELSE 3 END;
