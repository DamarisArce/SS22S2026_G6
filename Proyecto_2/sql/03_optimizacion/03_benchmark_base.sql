-- P2_BENCH_BASE
-- Consulta idéntica a la optimizada salvo tabla fuente. Caché desactivado desde runner.
SELECT COUNT(*) viajes,
       ROUND(AVG(CAST(fare_amount AS FLOAT64)),2) tarifa_media,
       SUM(fare_amount) suma_tarifas
FROM `__PROJECT_ID__.__DATASET__.viajes_base`
WHERE pickup_date >= DATE '2022-06-01'
  AND pickup_date < DATE '2022-07-01'
  AND pickup_location_id = '161';
