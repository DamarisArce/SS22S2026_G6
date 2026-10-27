#!/usr/bin/env python3
"""Actualización documental local, idempotente. No accede a GCP ni a GitHub."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
readme = root / 'README.md'
doc = root / 'docs' / 'RESULTADOS_ROLLING_FORECAST_20261027.md'
assert readme.is_file(), 'Falta Proyecto_2/README.md'
assert doc.is_file(), 'Falta docs/RESULTADOS_ROLLING_FORECAST_20261027.md'
content = readme.read_text(encoding='utf-8')
marker = '<!-- P2-G6-ROLLING-20261027 -->'
if marker in content:
    print('README: ya actualizado. No se repite.')
    raise SystemExit(0)
backup = Path.home() / 'Descargas' / 'Proyecto2_README_antes_rolling_20261027.md'
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    shutil.copy2(readme, backup)
content = content.replace(
    'Dos páginas: *Análisis exploratorio* y *Modelos BigQuery ML*.',
    'Tres páginas: *Análisis exploratorio*, *Modelos BigQuery ML* y *Rolling Forecast — origen móvil*.'
)
old = ('**Limitación esencial:** la gráfica de siete días utiliza medias móviles de predicciones '
       'fuera de muestra sobre noviembre con **modelos fijos**. No demuestra pronóstico '
       '*rolling-origin* con reentrenamiento sucesivo. Documentar esta distinción ante el '
       'criterio "Rolling Forecast" del enunciado.')
new = ('**Validación temporal:** además de la media móvil descriptiva, se implementó '
       '**backtesting rolling-origin** de horizonte un día sobre 23 fechas. Los modelos '
       'permanecen fijos y el baseline histórico presenta menor error. Ver '
       '[resultados Rolling Forecast](docs/RESULTADOS_ROLLING_FORECAST_20261027.md).')
content = content.replace(old, new)
section = """

<!-- P2-G6-ROLLING-20261027 -->
## Rolling Forecast con origen móvil — validación real del 27/10/2026

Se agregó la tercera página **«Rolling Forecast — origen móvil»** al [dashboard](https://datastudio.google.com/reporting/45e788e9-a2c3-4606-8721-4ba456c08a19). El análisis presenta **23 pronósticos** diarios del 8 al 30 de noviembre de 2022, con **siete días históricos** y **un día de horizonte**. La verificación registró **0 ventanas incorrectas** y **0 tasas inválidas**. Los modelos BigQuery ML son fijos, sin reentrenamiento diario.

| Método | MAE (pp) ↓ | RMSE (pp) ↓ | Sesgo firmado (pp) |
|---|---:|---:|---:|
| Baseline histórico | **2.2079** | **2.5633** | -0.5161 |
| Logística | 5.2465 | 5.7875 | -5.2465 |
| Lineal | 5.9523 | 6.4231 | -5.9523 |

**Hallazgo:** el baseline histórico presenta menor error de pronóstico que las dos alternativas derivadas de ML. No debe confundirse la comparación a nivel viaje con el pronóstico de la proporción diaria.

[Metodología, limitaciones y evidencias](docs/RESULTADOS_ROLLING_FORECAST_20261027.md).
"""
readme.write_text(content.rstrip() + section, encoding='utf-8')
print('README sincronizado. Respaldo:', backup)
