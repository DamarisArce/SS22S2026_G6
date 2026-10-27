#!/usr/bin/env python3
"""Exporta evidencia factual de metadatos BigQuery mediante operaciones bq show (sin queries)."""
from __future__ import annotations
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidencias' / 'bigquery'
PROJECT = 'ss2-p2-g6-2026-nc-1026'
DATASET = 'ss2_proyecto2_g6'

TABLES = ('viajes_base', 'viajes_optimizada', 'datos_ml',
          'metricas_modelos', 'predicciones_comparadas')
MODELS = ('modelo_lineal', 'modelo_logistico',
          'modelo_lineal_custom_l2_1', 'modelo_lineal_seq_eval20')


def listar_modelos():
    args = ['bq', f'--project_id={PROJECT}', 'ls', '--models', '--format=prettyjson',
            f'{PROJECT}:{DATASET}']
    p = subprocess.run(args, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError('No se pudieron listar los modelos: ' + (p.stderr + '\n' + p.stdout).strip())
    try:
        datos = json.loads(p.stdout.strip() or '[]')
    except ValueError as exc:
        raise RuntimeError('Respuesta no JSON de bq ls --models') from exc
    if not isinstance(datos, list):
        raise RuntimeError('Formato inesperado al listar los modelos')
    nombres = set()
    for item in datos:
        if not isinstance(item, dict):
            raise RuntimeError('Entrada inesperada al listar los modelos')
        ref = item.get('modelReference') or {}
        nombre = ref.get('modelId') if isinstance(ref, dict) else None
        nombre = nombre or item.get('modelId')
        if not nombre:
            raise RuntimeError('No se pudo identificar un modelo listado')
        nombres.add(nombre)
    return nombres


def show(target: str, model: bool = False, optional: bool = False):
    if model and optional and target.split('.')[-1] not in listar_modelos():
        return None
    args = ['bq', f'--project_id={PROJECT}', 'show', '--format=prettyjson']
    if model:
        args += ['--model']
    args += [target]
    p = subprocess.run(args, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(f'No se pudo leer {target}: {(p.stderr + chr(10) + p.stdout).strip()}')
    return json.loads(p.stdout)


def table_view(data: dict) -> dict:
    cols = data.get('schema', {}).get('fields', [])
    return {
        'id': data.get('id'),
        'tipo': data.get('type'),
        'registros': data.get('numRows'),
        'bytes_almacenados': data.get('numBytes'),
        'particionamiento': data.get('timePartitioning'),
        'clustering': data.get('clustering'),
        'columnas': [{'nombre': f.get('name'), 'tipo': f.get('type')} for f in cols]
    }


def model_view(data: dict) -> dict:
    runs = data.get('trainingRuns', [])
    return {
        'id': data.get('id'),
        'tipo_modelo': data.get('modelType'),
        'entrenamientos_registrados': len(runs),
        'opciones_entrenamiento': [r.get('trainingOptions', {}) for r in runs],
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = {'origen': table_view(show('bigquery-public-data:new_york_taxi_trips.tlc_yellow_trips_2022')),
            'tablas': {}, 'modelos': {}}
    for name in TABLES:
        data['tablas'][name] = table_view(show(f'{PROJECT}:{DATASET}.{name}'))
    for name in MODELS:
        result = show(f'{PROJECT}:{DATASET}.{name}', model=True, optional=name not in MODELS[:2])
        data['modelos'][name] = model_view(result) if result is not None else None
    target = OUT / 'metadatos_fuente_tablas_modelos.json'
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print('EVIDENCIA METADATOS BIGQUERY:')
    print(f'  Fuente pública: {data["origen"].get("registros")} registros')
    for k, v in data['tablas'].items():
        print(f'  Tabla {k}: {v.get("registros")} registros')
    for k, v in data['modelos'].items():
        print(f'  Modelo {k}: {"existe" if v is not None else "no existe"}')
    print(f'Guardado: {target}')
    print('Nota: evidencia de metadatos, sin sustituir capturas del editor de BigQuery.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
