#!/usr/bin/env python3
"""Checks estáticos: sin conexión ni procesamiento de Google Cloud."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
folder = root / "sql/04_bigquery_ml"
original = "modelo_lineal"
custom = (folder / "07_lineal_custom_l2_1.sql").read_text()
seq = (folder / "08_lineal_seq_eval20.sql").read_text()
comparison = (folder / "09_comparacion_experimentos.sql").read_text()
runner = (root / "scripts/experimento_ml_controlado.py").read_text()
assert "CREATE OR REPLACE" not in custom.upper()
assert "CREATE OR REPLACE" not in seq.upper()
assert "DATA_SPLIT_METHOD='CUSTOM'" in custom and "L2_REG=1.0" in custom
assert "MAX_ITERATIONS=30" in custom and "DATA_SPLIT_EVAL_FRACTION" not in custom
assert "DATA_SPLIT_METHOD='SEQ'" in seq and "DATA_SPLIT_EVAL_FRACTION=0.20" in seq
assert "DATA_SPLIT_COL='fecha_orden_split'" in seq and "L2_REG=0.1" in seq
assert "CAST(fecha_orden AS TIMESTAMP)" in seq
for source in (custom, seq):
    assert "pickup_date < DATE '2022-11-01'" in source
    assert ('CREATE MODEL `__PROJECT_ID__.__DATASET__.' + original + '`') not in source
assert comparison.count("FROM ML.EVALUATE(") == 2
assert comparison.count("pickup_date >= DATE '2022-11-01'") == 2
assert "P2_AUTORIZO_ENTRENAMIENTO_EXTRA" in runner
assert (root / "scripts/recolectar_evidencias_bq.py").is_file()
assert "--dry_run" in runner
assert "--maximum_bytes_billed=1073741824" in runner
print("OK: dos modelos nuevos, split SEQ 20%, L2 alternativo, TEST noviembre y puertas de autorizacion.")
