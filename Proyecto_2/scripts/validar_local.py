#!/usr/bin/env python3
"""Comprobaciones estáticas locales; NO ejecuta consultas ni crea recursos en GCP."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
required = [
    'ejecutar.sh',
    'sql/02_transformaciones/01_base_comparable.sql',
    'sql/03_optimizacion/01_particionado_clustering.sql',
    'sql/03_optimizacion/03_benchmark_base.sql',
    'sql/03_optimizacion/04_benchmark_optimizada.sql',
    'sql/04_bigquery_ml/01_crear_muestra.sql',
    'sql/04_bigquery_ml/02_verificar_splits.sql',
    'sql/04_bigquery_ml/03_entrenar_lineal.sql',
    'sql/04_bigquery_ml/04_entrenar_arbol.sql',
    'sql/04_bigquery_ml/04_entrenar_logistico.sql',
    'sql/04_bigquery_ml/05_evaluacion.sql',
    'sql/04_bigquery_ml/06_predicciones.sql',
    'sql/05_dashboard/01_tablas_vistas.sql',
]
errors = []
for item in required:
    path = root / item
    if not path.is_file():
        errors.append(f'Archivo faltante: {item}')

if not errors:
    get = lambda rel: (root / rel).read_text(encoding='utf-8')
    sample = get('sql/04_bigquery_ml/01_crear_muestra.sql')
    model1 = get('sql/04_bigquery_ml/03_entrenar_lineal.sql')
    model2 = get('sql/04_bigquery_ml/04_entrenar_logistico.sql')
    metricas = get('sql/04_bigquery_ml/05_evaluacion.sql')
    preds = get('sql/04_bigquery_ml/06_predicciones.sql')
    dash = get('sql/05_dashboard/01_tablas_vistas.sql')
    runner = get('ejecutar.sh')
    expected = {
        "Sample deterministic 0.2%": 'FARM_FINGERPRINT' in sample and '500\n' in sample,
        "Sampling uses partition range": "pickup_date < DATE '2022-12-01'" in sample,
        "Two different ML algorithm types": "MODEL_TYPE='LINEAR_REG'" in model1 and "MODEL_TYPE='LOGISTIC_REG'" in model2,
        "Time-custom splits": "DATA_SPLIT_METHOD='CUSTOM'" in model1 and "DATA_SPLIT_METHOD='CUSTOM'" in model2,
        "External test November": all("pickup_date < DATE '2022-12-01'" in x for x in (metricas,preds)),
        "Materialized dashboard summary": 'CREATE OR REPLACE TABLE' in dash and 'GROUP BY GROUPING SETS' in dash,
        "Duplicate execution protections": 'no_repetir()' in runner and 'P2_FORZAR_REEMPLAZO' in runner,
        "No hard-coded foreign project in SQL": all('yousac-sa-2s2026-d27cf0' not in get(rel) for rel in required if rel.endswith('.sql')),
    }
    errors.extend(name for name, ok in expected.items() if not ok)
if errors:
    print('ERROR: validacion estatica fallida:')
    for msg in errors:
        print(' -', msg)
    sys.exit(1)
print('OK: archivos requeridos y controles estaticos presentes.')
print('AVISO: esta prueba no sustituye la validacion de SQL en BigQuery ni el entrenamiento.')
