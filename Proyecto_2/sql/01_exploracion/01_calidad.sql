-- Comprobación inicial de calidad; no modifica datos.
-- El recuento total metadata conocido es 36,256,539; comparar con ejecución real.
SELECT
  COUNT(*) AS total_registros,
  COUNTIF(pickup_datetime IS NULL) AS pickup_nulo,
  COUNTIF(dropoff_datetime IS NULL) AS dropoff_nulo,
  COUNTIF(dropoff_datetime <= pickup_datetime) AS duracion_invalida,
  COUNTIF(pickup_datetime < TIMESTAMP('2022-01-01 00:00:00+00')
       OR pickup_datetime >= TIMESTAMP('2023-01-01 00:00:00+00')) AS fuera_2022_utc,
  COUNTIF(trip_distance IS NULL OR trip_distance <= 0) AS distancia_no_positiva,
  COUNTIF(fare_amount IS NULL OR fare_amount <= 0) AS tarifa_no_positiva,
  COUNTIF(total_amount IS NULL OR total_amount <= 0) AS total_no_positivo,
  COUNTIF(pickup_location_id IS NULL OR pickup_location_id = '') AS origen_faltante,
  COUNTIF(dropoff_location_id IS NULL OR dropoff_location_id = '') AS destino_faltante,
  COUNTIF(passenger_count IS NULL) AS pasajeros_nulos,
  MIN(pickup_datetime) AS primer_pickup,
  MAX(pickup_datetime) AS ultimo_pickup
FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2022`;
