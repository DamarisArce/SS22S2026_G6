#!/usr/bin/env python3
"""Crea agregados y vistas de Looker Studio sin sobrescribir objetos existentes.

Ejecutar desde Proyecto_2. BigQuery en US. No entrena modelos.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

P = 'ss2-p2-g6-2026-nc-1026'
D = 'ss2_proyecto2_g6'
MAX_BYTES = int(os.environ.get('P2_MAX_BYTES', '6000000000'))
OBJECTS = [
    ('TABLE', 'resumen_eda_dashboard'),
    ('VIEW', 'vw_viajes_mes'),
    ('VIEW', 'vw_zonas'),
    ('VIEW', 'vw_horas'),
    ('VIEW', 'vw_predicciones_diarias'),
    ('VIEW', 'vw_comparacion_clasificacion'),
    ('VIEW', 'vw_metricas_modelos'),
    ('VIEW', 'vw_rolling_7dias'),
]
SQL_PATH = Path('sql/05_dashboard/01_tablas_vistas.sql')


def cmd(args, entrada=None):
    r = subprocess.run(args, input=entrada, text=True, capture_output=True)
    if r.returncode:
        raise RuntimeError(
            'Error en comando: ' + ' '.join(args) + '\n'
            + 'Salida:\n' + r.stdout + '\nError:\n' + r.stderr
        )
    return r.stdout


def inventory():
    out = cmd(['bq', f'--project_id={P}', 'ls', '--format=prettyjson',
               '--max_results=1000', f'{P}:{D}'])
    data = json.loads(out)
    if not isinstance(data, list) or len(data) >= 1000:
        raise RuntimeError('Inventario inesperado o incompleto. No crear nada.')
    return {x.get('tableReference', {}).get('tableId'): x.get('type')
            for x in data}


def metadata(name):
    data = json.loads(cmd(['bq', f'--project_id={P}', 'show',
                           '--format=prettyjson', f'{P}:{D}.{name}']))
    return data


def sql_parts():
    if not SQL_PATH.is_file():
        raise RuntimeError('No encuentro sql/05_dashboard/01_tablas_vistas.sql. Entrar a Proyecto_2.')
    original = SQL_PATH.read_text(encoding='utf-8')
    blocks = [s.strip() for s in re.split(r';\s*(?:\n|$)', original) if s.strip()]
    if len(blocks) != len(OBJECTS):
        raise RuntimeError(f'Se esperaban 8 sentencias SQL, encontradas {len(blocks)}.')
    queries = []
    for (kind, name), block in zip(OBJECTS, blocks):
        rendered = block.replace('__PROJECT_ID__', P).replace('__DATASET__', D)
        expected = f'CREATE OR REPLACE {kind} `{P}.{D}.{name}`'
        if rendered.count(expected) != 1:
            raise RuntimeError(f'Sentencia incorrecta/duplicada: {kind} {name}.')
        # La proteccion final es del propio BigQuery: CREATE sin OR REPLACE.
        rendered = rendered.replace(expected, f'CREATE {kind} `{P}.{D}.{name}`', 1)
        queries.append(rendered + ';')
    return queries


def run_query(sql, dry_run):
    args = [
        'bq', f'--project_id={P}', '--location=US', 'query',
        '--use_legacy_sql=false', f'--maximum_bytes_billed={MAX_BYTES}',
        '--format=prettyjson', '--quiet'
    ]
    if dry_run:
        args.append('--dry_run')
    return cmd(args, entrada=sql)


def main():
    if os.environ.get('P2_AUTORIZO_GCP') != 'SI':
        raise RuntimeError('Es obligatorio exportar P2_AUTORIZO_GCP=SI.')
    if not 100_000_000 <= MAX_BYTES <= 10_000_000_000:
        raise RuntimeError('P2_MAX_BYTES debe estar entre 100 MB y 10 GB.')
    queries = sql_parts()  # valida TODO antes de consultar GCP
    initial = inventory()
    print('========== PRERREQUISITOS ==========', flush=True)
    required = ('viajes_optimizada', 'predicciones_comparadas',
                'metricas_modelos', 'metricas_comparacion_clasificacion')
    for name in required:
        if name not in initial:
            raise RuntimeError(f'Falta objeto obligatorio: {name}.')
        print(f'OK: {name}', flush=True)

    print('\n========== RECURSOS DEL DASHBOARD ==========', flush=True)
    for kind, name in OBJECTS:
        print(f'{name}: {"EXISTE" if name in initial else "PENDIENTE"}', flush=True)

    for (kind, name), sql in zip(OBJECTS, queries):
        print(f'\n========== {name} ==========', flush=True)
        available = inventory()
        if name in available:
            data = metadata(name)
            actual_kind = data.get('type')
            if actual_kind != kind:
                raise RuntimeError(f'{name}: se esperaba {kind}, se obtuvo {actual_kind}.')
            if kind == 'TABLE':
                rows = int(data.get('numRows', -1))
                if not 35 <= rows <= 2000:
                    raise RuntimeError(f'{name}: conteo sospechoso {rows}.')
                print(f'EXISTE: {rows} filas, no se modifica.', flush=True)
            else:
                print('EXISTE: vista verificada, no se modifica.', flush=True)
            continue

        print(f'Dry run con limite de {MAX_BYTES:,} bytes...', flush=True)
        dry = json.loads(run_query(sql, dry_run=True))
        estimate = dry.get('statistics', {}).get('totalBytesProcessed')
        print('Bytes estimados:', estimate if estimate is not None else 'no disponibles', flush=True)
        if estimate is not None and int(estimate) > MAX_BYTES:
            raise RuntimeError(f'Estimacion {estimate} supera el maximo autorizado.')

        print(f'Creando {kind} {name} sin OR REPLACE...', flush=True)
        print(run_query(sql, dry_run=False).strip()[:900], flush=True)
        after = inventory()
        if name not in after:
            raise RuntimeError(f'{name}: no aparece tras la creacion.')
        got = metadata(name)
        if got.get('type') != kind:
            raise RuntimeError(f'{name}: tipo inesperado: {got.get("type")}')
        if kind == 'TABLE':
            rows = int(got.get('numRows', -1))
            if not 35 <= rows <= 2000:
                raise RuntimeError(f'{name}: resultado {rows} filas fuera de rango esperado.')
            print(f'TABLA VERIFICADA: {rows} filas.', flush=True)
        else:
            print('VISTA VERIFICADA.', flush=True)

    print('\nDASHBOARD LISTO EN BIGQUERY: 1 tabla y 7 vistas.', flush=True)
    print('Pendiente: crear el informe visual en Looker Studio y compartir enlace.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as e:
        print('ERROR: ' + str(e), file=sys.stderr, flush=True)
        sys.exit(1)
