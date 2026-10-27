-- Métricas mensuales y distribución de pagos (2 consultas comentadas).
SELECT
  EXTRACT(MONTH FROM pickup_datetime) AS mes_utc,
  COUNT(*) AS viajes,
  ROUND(AVG(CAST(trip_distance AS FLOAT64)), 2) AS millas_promedio,
  ROUND(AVG(CAST(fare_amount AS FLOAT64)), 2) AS tarifa_promedio,
  ROUND(AVG(CAST(total_amount AS FLOAT64)), 2) AS total_promedio,
  ROUND(APPROX_QUANTILES(CAST(fare_amount AS FLOAT64), 100)[OFFSET(50)], 2) AS mediana_tarifa_aprox
FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022`
WHERE pickup_datetime >= TIMESTAMP('2022-01-01 00:00:00+00')
  AND pickup_datetime < TIMESTAMP('2023-01-01 00:00:00+00')
  AND trip_distance > 0 AND fare_amount > 0
GROUP BY 1 ORDER BY 1;

SELECT
  payment_type,
  COUNT(*) AS viajes,
  ROUND(AVG(CAST(tip_amount AS FLOAT64)), 2) AS propina_media_registrada,
  ROUND(AVG(CAST(total_amount AS FLOAT64)), 2) AS total_medio
FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022`
WHERE pickup_datetime >= TIMESTAMP('2022-01-01 00:00:00+00')
  AND pickup_datetime < TIMESTAMP('2023-01-01 00:00:00+00')
GROUP BY 1 ORDER BY viajes DESC;
