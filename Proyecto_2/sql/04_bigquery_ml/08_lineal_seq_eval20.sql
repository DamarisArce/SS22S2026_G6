-- Experimento B: division secuencial por instante del viaje con EVAL_FRACTION=20%.
-- Hiperparametros iguales a los del modelo lineal original (L2=0.1, 30 iteraciones).
-- Los datos de noviembre siguen excluidos del entrenamiento y de la validacion.
-- La columna fecha_orden_split es SOLO para dividir; BigQuery ML la excluye de features.
CREATE MODEL `__PROJECT_ID__.__DATASET__.modelo_lineal_seq_eval20`
OPTIONS (
  MODEL_TYPE='LINEAR_REG',
  INPUT_LABEL_COLS=['tarifa'],
  DATA_SPLIT_METHOD='SEQ',
  DATA_SPLIT_COL='fecha_orden_split',
  DATA_SPLIT_EVAL_FRACTION=0.20,
  MAX_ITERATIONS=30,
  L2_REG=0.1
) AS
SELECT
  tarifa, distancia_millas, pasajeros, hora_utc, dia_semana_utc,
  mes_utc, proveedor, origen, destino,
  CAST(fecha_orden AS TIMESTAMP) AS fecha_orden_split
FROM `__PROJECT_ID__.__DATASET__.datos_ml`
WHERE pickup_date >= DATE '2022-01-01'
  AND pickup_date < DATE '2022-11-01'
  AND tarifa BETWEEN 2.0 AND 250.0;
