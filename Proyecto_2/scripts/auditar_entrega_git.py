#!/usr/bin/env python3
"""Audita archivos locales Proyecto_2 sin hacer add/commit/push ni llamar GCP."""
from pathlib import Path
import subprocess, re, sys
root = Path(__file__).resolve().parents[1]
repo = root.parent
required = [
    'README.md', 'ejecutar.sh', '.gitignore',
    'docs/MODELADO.md', 'docs/DASHBOARD.md', 'docs/MATRIZ_RUBRICA.md',
    'docs/RESULTADOS_ROLLING_FORECAST_20261027.md',
    'docs/CIERRE_Y_EVIDENCIAS_20261027.md',
    'sql/04_bigquery_ml/03_entrenar_lineal.sql',
    'sql/04_bigquery_ml/04_entrenar_logistico.sql',
    'sql/04_bigquery_ml/05_evaluacion.sql',
    'sql/04_bigquery_ml/06_predicciones.sql',
    'sql/05_dashboard/03_rolling_forecast_origen_movil.sql',
    'sql/05_dashboard/04_rolling_forecast_metricas.sql',
    'evidencias/capturas/dashboard_01_exploracion.png',
    'evidencias/capturas/dashboard_02_modelos_bqml.png',
    'evidencias/capturas/dashboard_03_rolling_forecast_editor.png',
]
print('=== Archivos esenciales ===')
missing = []
for name in required:
    ok = (root/name).is_file()
    print(('OK    ' if ok else 'FALTA ') + name)
    if not ok: missing.append(name)
readme = (root/'README.md').read_text(encoding='utf8') if (root/'README.md').is_file() else ''
for label,needle in [
    ('URL dashboard', '45e788e9-a2c3-4606-8721-4ba456c08a19'),
    ('Rolling validado', '23 pronósticos'),
    ('Documento resultados', 'RESULTADOS_ROLLING_FORECAST_20261027.md'),
]:
    print(('OK    ' if needle in readme else 'REVISAR ') + label)
print('=== Búsqueda preventiva de posibles secretos ===')
# Solo informa archivos, nunca imprime el contenido de credenciales.
probes = [re.compile(x,re.I) for x in [
    r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    r'\bghp_[A-Za-z0-9_]{20,}',
    r'\bgithub_pat_[A-Za-z0-9_]{20,}',
    r'\bAIza[0-9A-Za-z_-]{30,}',
    r'\bsk-[A-Za-z0-9_-]{20,}',
    r'(?i)(?:client_secret|api_key|access_token|password)\s*[=:]\s*["\']?[A-Za-z0-9_/+=.-]{18,}',
]]
flagged=[]
for folder in ['sql','scripts','docs','evidencias']:
    base=root/folder
    if not base.exists():continue
    for path in base.rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts or path.suffix in ('.png','.jpg','.jpeg','.pyc'):continue
        if path.stat().st_size > 2_000_000:continue
        content=path.read_text(encoding='utf8',errors='replace')
        if any(p.search(content) for p in probes):flagged.append(str(path.relative_to(root)))
for path in flagged:print('REVISAR POSIBLE SECRETO:',path)
if not flagged:print('No se detectaron patrones comunes de secretos (NO garantiza ausencia).')
print('=== Archivos finales del dashboard ===')
print('Captura final vista página 3:', 'PRESENTE' if (root/'evidencias/capturas/dashboard_03_rolling_forecast.png').is_file() else 'PENDIENTE')
print('=== Git ===')
p=subprocess.run(['git','-C',str(repo),'status','--short','--untracked-files=normal'],capture_output=True,text=True)
print(p.stdout[:4000] if p.returncode==0 else p.stderr)
if missing or flagged:
    print('AUDITORÍA CON OBSERVACIONES: revisar antes de stage/commit')
    sys.exit(1)
print('AUDITORÍA LOCAL COMPLETADA. Pendientes externos: capturas BigQuery y permisos del dashboard.')
