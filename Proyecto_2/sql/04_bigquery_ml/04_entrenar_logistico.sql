-- Modelo B: clasificacion binaria de tarifas altas (>= USD 20).
-- Diferente algoritmo y objetivo del LINEAR_REG existente; mismas variables operativas.
-- No usar datos de noviembre en entrenamiento ni validacion interna.
-- Umbral del negocio fijado antes de usar el conjunto TEST; no deriva de TEST.
CREATE MODEL `__PROJECT_ID__.__DATASET__.modelo_logistico`
OPTIONS (
  MODEL_TYPE='LOGISTIC_REG', INPUT_LABEL_COLS=['tarifa_alta'],
  DATA_SPLIT_METHOD='CUSTOM', DATA_SPLIT_COL='es_validacion',
  MAX_ITERATIONS=20, L2_REG=0.1, EARLY_STOP=TRUE
) AS
SELECT
  IF(tarifa >= 20.0, 1, 0) AS tarifa_alta,
  distancia_millas, pasajeros, hora_utc, dia_semana_utc,
  mes_utc, proveedor, origen, destino, es_validacion
FROM `__PROJECT_ID__.__DATASET__.datos_ml`
WHERE pickup_date >= DATE '2022-01-01'
  AND pickup_date < DATE '2022-11-01'
  AND tarifa BETWEEN 2.0 AND 250.0;
