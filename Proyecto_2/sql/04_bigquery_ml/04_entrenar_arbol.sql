-- Modelo B: boosted tree, split secuencial por TIMESTAMP y 20% final para validación.
-- Esta alternativa satisface uso documentado de DATA_SPLIT_EVAL_FRACTION sin mezcla temporal aleatoria.
-- Misma ventana enero-octubre de datos candidatos. Test externo: noviembre.
CREATE OR REPLACE MODEL `__PROJECT_ID__.__DATASET__.modelo_arbol`
OPTIONS (
  MODEL_TYPE='BOOSTED_TREE_REGRESSOR', INPUT_LABEL_COLS=['tarifa'],
  DATA_SPLIT_METHOD='SEQ', DATA_SPLIT_COL='fecha_orden',
  DATA_SPLIT_EVAL_FRACTION=0.2,
  MAX_ITERATIONS=15, MAX_TREE_DEPTH=5, LEARN_RATE=0.2,
  EARLY_STOP=TRUE
) AS
SELECT tarifa, distancia_millas, pasajeros, hora_utc, dia_semana_utc,
       mes_utc, proveedor, origen, destino, fecha_orden
FROM `__PROJECT_ID__.__DATASET__.datos_ml`
WHERE pickup_date >= DATE '2022-01-01' AND pickup_date < DATE '2022-11-01'
  AND tarifa BETWEEN 2.0 AND 250.0;
