-- Derivación de base para análisis, limpieza mínima justificable y benchmark.
-- No cortar arbitrariamente distancias altas / importes altos antes de estudiar cuantiles.
-- Se descartan faltantes/valores incompatibles con viaje normal positivo.
CREATE OR REPLACE TABLE `__PROJECT_ID__.__DATASET__.viajes_base`
OPTIONS(description='Viajes NYC 2022 UTC válidos, referencia sin particiones para el benchmark') AS
SELECT
  DATE(pickup_datetime) AS pickup_date,
  pickup_datetime,
  dropoff_datetime,
  vendor_id,
  COALESCE(passenger_count, 0) AS passenger_count,
  trip_distance,
  rate_code,
  store_and_fwd_flag,
  payment_type,
  fare_amount,
  total_amount,
  tip_amount,
  pickup_location_id,
  dropoff_location_id,
  EXTRACT(HOUR FROM pickup_datetime) AS pickup_hour_utc,
  EXTRACT(DAYOFWEEK FROM pickup_datetime) AS pickup_weekday_utc,
  TIMESTAMP_DIFF(dropoff_datetime, pickup_datetime, SECOND) AS duracion_segundos
FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022`
WHERE pickup_datetime >= TIMESTAMP('2022-01-01 00:00:00+00')
  AND pickup_datetime < TIMESTAMP('2023-01-01 00:00:00+00')
  AND dropoff_datetime > pickup_datetime
  AND trip_distance > 0
  AND fare_amount > 0
  AND total_amount > 0
  AND pickup_location_id IS NOT NULL AND pickup_location_id != ''
  AND dropoff_location_id IS NOT NULL AND dropoff_location_id != '';
