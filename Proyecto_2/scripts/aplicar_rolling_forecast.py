#!/usr/bin/env python3
"""Implantacion idempotente y verificable del rolling-origin en BigQuery.

Solo crea dos VISTAS nuevas; nunca modifica tablas/modelos existentes.
Requiere P2_AUTORIZO_GCP=SI antes de ejecutar DDL.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

P = os.getenv('P2_PROJECT_ID', 'ss2-p2-g6-2026-nc-1026')
D = os.getenv('P2_DATASET', 'ss2_proyecto2_g6')
MAX_BYTES = 100_000_000
ROOT = Path(__file__).resolve().parents[1]
ARCHIVOS = [
    ('vw_forecast_origen_movil', ROOT / 'sql/05_dashboard/03_rolling_forecast_origen_movil.sql'),
    ('vw_forecast_metricas', ROOT / 'sql/05_dashboard/04_rolling_forecast_metricas.sql'),
]

if not re.fullmatch(r'[a-z][a-z0-9-]{4,62}', P) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', D):
    sys.exit('ERROR: identificadores de proyecto/dataset invalidos.')


def bq(*args: str, sql: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = ['bq', f'--project_id={P}', '--location=US', *args]
    try:
        result = subprocess.run(cmd, input=sql, text=True, capture_output=True, timeout=180)
    except FileNotFoundError:
        sys.exit('ERROR: el comando bq no esta instalado.')
    except subprocess.TimeoutExpired:
        sys.exit('ERROR: consulta local excedio 180 s. Revisar el trabajo en BigQuery ANTES de reintentar.')
    if check and result.returncode != 0:
        sys.exit('ERROR en '+ ' '.join(cmd) +'\nSTDOUT:\n'+result.stdout+'\nSTDERR:\n'+result.stderr)
    return result


def json_bq(*args: str, sql: str | None = None):
    result = bq(*args, sql=sql)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        sys.exit('ERROR: BigQuery no devolvio JSON valido. Respuesta:\n'+result.stdout+'\n'+result.stderr)


def tablas_actuales() -> dict[str, str]:
    data = json_bq('ls', '--max_results=1000', '--format=prettyjson', f'{P}:{D}')
    if isinstance(data, dict):
        data = data.get('tables', [])
    if not isinstance(data, list):
        sys.exit('ERROR: estructura imprevista al listar objetos de BigQuery.')
    resultado = {}
    for item in data:
        ref = item.get('tableReference', {})
        if 'tableId' in ref:
            resultado[ref['tableId']] = item.get('type', 'DESCONOCIDO')
    return resultado


print('========== PRERREQUISITOS ==========', flush=True)
recursos = tablas_actuales()
if 'predicciones_comparadas' not in recursos:
    sys.exit('ERROR: falta la tabla predicciones_comparadas. No se creara ninguna vista.')
print('OK: existe predicciones_comparadas.', flush=True)

meta = json_bq('show', '--format=prettyjson', f'{P}:{D}.predicciones_comparadas')
campos = {f['name'] for f in meta.get('schema', {}).get('fields', [])}
requeridos = {'pickup_date', 'clase_real', 'clase_lineal', 'clase_logistica'}
if not requeridos.issubset(campos):
    sys.exit('ERROR: columnas faltantes en predicciones_comparadas: '+str(sorted(requeridos-campos)))
print('OK: columnas historicas verificadas.', flush=True)

for nombre, ruta in ARCHIVOS:
    if not ruta.exists():
        sys.exit(f'ERROR: no existe SQL: {ruta}')
    contenido = ruta.read_text(encoding='utf-8')
    if not contenido.lstrip().startswith('--') or f'vw_forecast_' not in contenido:
        sys.exit(f'ERROR: archivo SQL inesperado: {ruta.name}')

print('\n========== ESTADO DE VISTAS ==========', flush=True)
for nombre, _ in ARCHIVOS:
    print(f'{nombre}: {recursos.get(nombre, "PENDIENTE")}', flush=True)

pendientes = [n for n, _ in ARCHIVOS if n not in recursos]
if pendientes and os.environ.get('P2_AUTORIZO_GCP') != 'SI':
    sys.exit('No se modifico GCP. Para crear las vistas exportar P2_AUTORIZO_GCP=SI.')

for nombre, ruta in ARCHIVOS:
    if nombre in recursos:
        if recursos[nombre] not in ('VIEW', 'DESCONOCIDO'):
            sys.exit(f'ERROR: {nombre} ya existe pero no es una vista: {recursos[nombre]}')
        print(f'EXISTENTE: {nombre}, sin reemplazar.', flush=True)
        continue
    sql = ruta.read_text(encoding='utf-8').replace('__PROJECT_ID__', P).replace('__DATASET__', D)
    if not re.search(r'CREATE\s+VIEW\s+IF\s+NOT\s+EXISTS', sql, flags=re.I):
        sys.exit(f'ERROR: SQL {ruta.name} no es idempotente. No se ejecuta.')
    print(f'\n========== CREANDO {nombre} ==========', flush=True)
    args = ('query', '--use_legacy_sql=false', f'--maximum_bytes_billed={MAX_BYTES}')
    bq(*args, '--dry_run', sql=sql)
    print('Dry run aceptado.', flush=True)
    result = bq(*args, sql=sql)
    print(result.stdout.strip() or 'DDL aceptada.', flush=True)
    recursos = tablas_actuales()
    if nombre not in recursos:
        sys.exit(f'ERROR: se ejecuto CREATE VIEW pero {nombre} no aparece. Verificar el trabajo antes de reintentar.')
    print(f'VALIDADA: {nombre}.', flush=True)

print('\n========== VALIDACION DE ORIGEN MOVIL ==========', flush=True)
consulta = f'''SELECT
 COUNT(*) AS dias,
 CAST(MIN(fecha_pronosticada) AS STRING) AS primera_fecha,
 CAST(MAX(fecha_pronosticada) AS STRING) AS ultima_fecha,
 COUNTIF(dias_historial != 7 OR horizonte_dias != 1 OR
         fin_historial != fecha_origen OR
         inicio_historial != DATE_SUB(fecha_pronosticada, INTERVAL 7 DAY) OR
         fecha_origen != DATE_SUB(fecha_pronosticada, INTERVAL 1 DAY)) AS ventanas_incorrectas,
 COUNTIF(tasa_real IS NULL OR pronostico_lineal IS NULL OR
         pronostico_logistico IS NULL OR referencia_historica IS NULL OR
         tasa_real NOT BETWEEN 0 AND 1 OR pronostico_lineal NOT BETWEEN 0 AND 1 OR
         pronostico_logistico NOT BETWEEN 0 AND 1 OR referencia_historica NOT BETWEEN 0 AND 1) AS tasas_invalidas
FROM `{P}.{D}.vw_forecast_origen_movil`'''
rows = json_bq('query', '--use_legacy_sql=false', f'--maximum_bytes_billed={MAX_BYTES}', '--format=prettyjson', consulta)
if len(rows) != 1:
    sys.exit('ERROR: esperado un unico resultado de control.')
r = rows[0]
print(json.dumps(r, ensure_ascii=False, indent=2), flush=True)
if int(r['dias']) != 23 or r['primera_fecha'] != '2022-11-08' or r['ultima_fecha'] != '2022-11-30' or int(r['ventanas_incorrectas']) != 0 or int(r['tasas_invalidas']) != 0:
    sys.exit('ERROR: la comprobacion temporal fallo. NO conectar la vista al informe.')

print('\n========== METRICAS DE PRONOSTICO ==========', flush=True)
rows = json_bq('query', '--use_legacy_sql=false', f'--maximum_bytes_billed={MAX_BYTES}', '--format=prettyjson',
    f'SELECT * FROM `{P}.{D}.vw_forecast_metricas` ORDER BY modelo')
print(json.dumps(rows, ensure_ascii=False, indent=2), flush=True)
if len(rows) != 3 or {x['modelo'] for x in rows} != {'LINEAL','LOGISTICA','BASELINE_HISTORICO'} or any(int(x['dias_evaluados']) != 23 for x in rows):
    sys.exit('ERROR: metricas inesperadas. Revisar antes de actualizar el dashboard.')

print('\nROLLING-ORIGIN VALIDADO: 23 pronosticos de 1 dia, 7 dias historicos, 2 modelos ML + baseline.', flush=True)
