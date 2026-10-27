-- Modelo A: regresión lineal, split temporal personalizado (CUSTOM).
-- Entrenamiento enero-agosto; validación septiembre-octubre; prueba externa noviembre.
CREATE OR REPLACE MODEL `__PROJECT_ID__.__DATASET__.modelo_lineal`
OPTIONS (
  MODEL_TYPE='LINEAR_REG', INPUT_LABEL_COLS=['tarifa'],
  DATA_SPLIT_METHOD='CUSTOM', DATA_SPLIT_COL='es_validacion',
  MAX_ITERATIONS=30, L2_REG=0.1
) AS
SELECT tarifa, distancia_millas, pasajeros, hora_utc, dia_semana_utc,
       mes_utc, proveedor, origen, destino, es_validacion
FROM `__PROJECT_ID__.__DATASET__.datos_ml`
WHERE pickup_date >= DATE '2022-01-01' AND pickup_date < DATE '2022-11-01'
  AND tarifa BETWEEN 2.0 AND 250.0;
