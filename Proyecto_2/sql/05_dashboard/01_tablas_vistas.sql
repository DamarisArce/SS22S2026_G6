-- Materializa EDA una sola vez; las vistas leen tablas pequenas.
CREATE OR REPLACE TABLE `__PROJECT_ID__.__DATASET__.resumen_eda_dashboard`
OPTIONS(description='Agregados compactos enero-noviembre 2022') AS
WITH fuente AS (
 SELECT EXTRACT(MONTH FROM pickup_date) AS mes_2022,
        pickup_location_id AS zona_origen,
        pickup_hour_utc AS hora_utc,
        fare_amount, total_amount, trip_distance
 FROM `__PROJECT_ID__.__DATASET__.viajes_optimizada`
 WHERE pickup_date >= DATE '2022-01-01' AND pickup_date < DATE '2022-12-01'
)
SELECT
 CASE WHEN GROUPING(mes_2022)=0 THEN 'MES'
      WHEN GROUPING(zona_origen)=0 THEN 'ZONA'
      ELSE 'HORA' END AS tipo_dimension,
 mes_2022, zona_origen, hora_utc,
 COUNT(*) AS viajes,
 ROUND(AVG(CAST(fare_amount AS FLOAT64)),2) AS tarifa_media,
 ROUND(AVG(CAST(total_amount AS FLOAT64)),2) AS gasto_medio,
 ROUND(AVG(CAST(trip_distance AS FLOAT64)),2) AS millas_media
FROM fuente
GROUP BY GROUPING SETS (mes_2022, zona_origen, hora_utc);

CREATE OR REPLACE VIEW `__PROJECT_ID__.__DATASET__.vw_viajes_mes` AS
SELECT mes_2022, viajes, tarifa_media, millas_media
FROM `__PROJECT_ID__.__DATASET__.resumen_eda_dashboard`
WHERE tipo_dimension = 'MES';

CREATE OR REPLACE VIEW `__PROJECT_ID__.__DATASET__.vw_zonas` AS
SELECT zona_origen, viajes, gasto_medio
FROM `__PROJECT_ID__.__DATASET__.resumen_eda_dashboard`
WHERE tipo_dimension = 'ZONA';

CREATE OR REPLACE VIEW `__PROJECT_ID__.__DATASET__.vw_horas` AS
SELECT hora_utc, viajes, millas_media
FROM `__PROJECT_ID__.__DATASET__.resumen_eda_dashboard`
WHERE tipo_dimension = 'HORA';

-- Predicciones agregadas por dia, no solamente por mes (TEST=noviembre).
CREATE OR REPLACE VIEW `__PROJECT_ID__.__DATASET__.vw_predicciones_diarias` AS
SELECT pickup_date, COUNT(*) AS evaluados,
 ROUND(AVG(valor_real),2) AS tarifa_real_media,
 ROUND(AVG(pred_lineal),2) AS tarifa_estimada_lineal,
 ROUND(AVG(prob_tarifa_alta),4) AS probabilidad_media_tarifa_alta,
 ROUND(AVG(IF(clase_logistica=clase_real, 1.0, 0.0)),4) AS accuracy_logistica
FROM `__PROJECT_ID__.__DATASET__.predicciones_comparadas`
GROUP BY pickup_date;

-- Comparativa de calidad en decision binaria "tarifa >= USD 20".
CREATE OR REPLACE VIEW `__PROJECT_ID__.__DATASET__.vw_comparacion_clasificacion` AS
SELECT * FROM `__PROJECT_ID__.__DATASET__.metricas_comparacion_clasificacion`;

CREATE OR REPLACE VIEW `__PROJECT_ID__.__DATASET__.vw_metricas_modelos` AS
SELECT * FROM `__PROJECT_ID__.__DATASET__.metricas_modelos`;

-- Promedios moviles de siete dias; esto NO constituye reentrenamiento rolling-origin.
CREATE OR REPLACE VIEW `__PROJECT_ID__.__DATASET__.vw_rolling_7dias` AS
SELECT pickup_date, evaluados, tarifa_real_media, tarifa_estimada_lineal,
       probabilidad_media_tarifa_alta, accuracy_logistica,
       ROUND(AVG(tarifa_real_media) OVER (
         ORDER BY pickup_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW),2) AS real_ma_7dias,
       ROUND(AVG(tarifa_estimada_lineal) OVER (
         ORDER BY pickup_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW),2) AS lineal_ma_7dias,
       ROUND(AVG(probabilidad_media_tarifa_alta) OVER (
         ORDER BY pickup_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW),4) AS probabilidad_alta_ma_7dias
FROM `__PROJECT_ID__.__DATASET__.vw_predicciones_diarias`;
