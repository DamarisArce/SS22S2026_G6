-- Dataset de modelado: 0.2% determinista (aprox 71,000 viajes) de enero-noviembre 2022.
-- La pertenencia a la muestra se reproduce por hash; UUID identifica registros solo dentro de esta materialización.
-- Las columnas extra sobre resultados finales se dejan FUERA de features de entrenamiento.
CREATE OR REPLACE TABLE `__PROJECT_ID__.__DATASET__.datos_ml`
PARTITION BY pickup_date
OPTIONS(description='Muestra reproducible de entrenamiento y prueba temporal sin variables de fuga') AS
SELECT
  GENERATE_UUID() AS id_registro,
  pickup_date,
  pickup_datetime AS fecha_orden,
  CAST(fare_amount AS FLOAT64) AS tarifa,
  CAST(trip_distance AS FLOAT64) AS distancia_millas,
  CAST(passenger_count AS FLOAT64) AS pasajeros,
  pickup_hour_utc AS hora_utc,
  pickup_weekday_utc AS dia_semana_utc,
  EXTRACT(MONTH FROM pickup_date) AS mes_utc,
  vendor_id AS proveedor,
  pickup_location_id AS origen,
  dropoff_location_id AS destino,
  (pickup_date >= DATE '2022-09-01' AND pickup_date < DATE '2022-11-01') AS es_validacion
FROM `__PROJECT_ID__.__DATASET__.viajes_optimizada`
WHERE pickup_date >= DATE '2022-01-01' AND pickup_date < DATE '2022-12-01'
  AND MOD(
        FARM_FINGERPRINT(CONCAT(
          CAST(pickup_datetime AS STRING), '|',
          CAST(trip_distance AS STRING), '|',
          pickup_location_id, '|', dropoff_location_id
        )),
        500
      ) = 0;
