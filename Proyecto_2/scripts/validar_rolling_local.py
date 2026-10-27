#!/usr/bin/env python3
"""Prueba independiente (sin GCP) del principio temporal usado en el SQL."""
from datetime import date, timedelta
from pathlib import Path

raiz = Path(__file__).resolve().parents[1]
sql = (raiz / 'sql/05_dashboard/03_rolling_forecast_origen_movil.sql').read_text()
assert 'ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING' in sql
assert 'inicio_historial = DATE_SUB(fecha_pronosticada, INTERVAL 7 DAY)' in sql
assert 'fin_historial = DATE_SUB(fecha_pronosticada, INTERVAL 1 DAY)' in sql
assert 'CREATE VIEW IF NOT EXISTS' in sql

base = date(2022, 11, 1)
dias = [{'fecha':base+timedelta(days=i), 'total':100+i, 'lineal':20+i%7,
         'logistica':22+i%7, 'real':23+i%7} for i in range(30)]

def rolling(rows):
    result=[]
    for i in range(7, len(rows)):
        prev = rows[i-7:i]
        assert len(prev) == 7
        assert all(x['fecha'] < rows[i]['fecha'] for x in prev)
        assert prev[-1]['fecha'] == rows[i]['fecha']-timedelta(days=1)
        den = sum(x['total'] for x in prev)
        result.append((rows[i]['fecha'], sum(x['lineal'] for x in prev)/den,
                       sum(x['logistica'] for x in prev)/den, rows[i]['real']/rows[i]['total']))
    return result

original = rolling(dias)
assert len(original) == 23
assert original[0][0] == date(2022,11,8)
assert original[-1][0] == date(2022,11,30)
# Alterar datos del futuro NO puede cambiar el pronostico emitido el dia anterior.
mutados = [dict(x) for x in dias]
mutados[7]['lineal'] = 100
mutados[7]['logistica'] = 100
mutados[7]['real'] = 100
assert rolling(mutados)[0][:3] == original[0][:3]
print('OK local: 23 origenes, horizonte 1 dia, ventana historica excluye objetivo.')
print('AVISO: prueba sintetica; es necesario ejecutar validacion real en BigQuery.')
