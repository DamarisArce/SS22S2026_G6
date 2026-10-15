# Dimensión calendario — `marts.dim_fecha`

## Propósito y grano

[`dim_fecha`](../dbt/models/marts/dim_fecha.sql) publica **una fila por día calendario**, identificada por `fecha` (`DATE`). Su rango se deriva dinámicamente de las fechas de `stg_oltp_venta` y los periodos de `int_ventas_mensuales_sucursal`; `generate_series` produce todos los días intermedios, incluso si alguno no registra ventas.

## Atributos de calendario

| Campo | Semántica |
|---|---|
| `fecha` | Clave natural del día |
| `anio`, `trimestre`, `mes`, `dia_mes` | Descomposición gregoriana |
| `anio_iso`, `numero_semana` | Año y semana según ISO-8601 |
| `dia_semana` | Lunes=1 a domingo=7 |
| `inicio_mes`, `fin_mes` | Límites del mes gregoriano |
| `inicio_trimestre`, `inicio_anio` | Inicios de periodos |
| `es_fin_semana` | Verdadero para sábado o domingo |

## Calidad y reconciliación

Para las fuentes académicas la vista cubrió **243 días**, desde `2026-01-01` hasta `2026-08-31`, con **243 fechas únicas**, continuidad sin huecos, columnas tipadas correctamente y atributos temporales consistentes. Las pruebas verifican año ISO, semanas, periodos, días bisiestos y cobertura de fechas de ventas; el join con ventas conserva **3,209 líneas**, **19,174 unidades** y **838,452.07** de subtotal.

Evidencias: [run 31](../resultados/31-dbt-marts-dim-fecha-run.txt), [tests 32](../resultados/32-dbt-marts-dim-fecha-tests.txt), [validación 33](../resultados/33-validacion-marts-dim-fecha-independiente.txt).

## Limitaciones

El modelo emplea calendario gregoriano e ISO-8601; no incorpora calendario fiscal personalizado, feriados ni zonas horarias comerciales no definidas. Su rango depende de los datos de entrada, no de fechas codificadas de manera fija.
