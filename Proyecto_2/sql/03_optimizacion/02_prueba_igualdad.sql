-- Invariantes de integridad: conteo y sumatorias entre tablas equivalentes.
WITH a AS (
  SELECT COUNT(*) n, SUM(fare_amount) suma_tarifas, SUM(total_amount) suma_total
  FROM `__PROJECT_ID__.__DATASET__.viajes_base`
), b AS (
  SELECT COUNT(*) n, SUM(fare_amount) suma_tarifas, SUM(total_amount) suma_total
  FROM `__PROJECT_ID__.__DATASET__.viajes_optimizada`
  WHERE pickup_date >= DATE '2022-01-01' AND pickup_date < DATE '2023-01-01'
)
SELECT a.n AS base_filas, b.n AS optimizada_filas,
 a.n=b.n AS conteos_iguales,
 a.n >= 1000000 AS cumple_minimo_millon,
 a.suma_tarifas=b.suma_tarifas AS tarifas_iguales,
 a.suma_total=b.suma_total AS totales_iguales
FROM a CROSS JOIN b;
