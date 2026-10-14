# `marts.dim_fecha`

## Estado

**IMPLEMENTADO Y VALIDADO EN POSTGRESQL** (14 de octubre de 2026).

La dimensión se construyó mediante dbt, superó sus 21 pruebas
y fue reconciliada independientemente contra las fuentes autorizadas
mediante una transacción PostgreSQL de solo lectura.

## Objetivo y grano

`marts.dim_fecha` es una vista calendario con una fila por día calendario.
Este grano permite relacionar hechos por `fecha` y conservar también los días
sin ventas, sin confundir ausencia de transacciones con ausencia de fecha.
La clave natural es `fecha`, de tipo `DATE`, porque representa directamente el
día de negocio y evita introducir una clave sustituta no solicitada.

## Rango y algoritmo

El rango se determina únicamente con las fechas no nulas de:

- `ref('stg_oltp_venta').fecha`, cuyo origen OLTP declara `fecha DATE`.
- `ref('int_ventas_mensuales_sucursal').periodo`, construido como el primer
  día del mes mediante `date_trunc('month', fecha)::date`.

Las dos fuentes se combinan con `UNION ALL`; después se calculan `MIN` y
`MAX`. Esos límites `DATE` se convierten explícitamente a
`timestamp without time zone` para la sobrecarga de PostgreSQL de
`generate_series`, con un intervalo de un día. Cada valor generado vuelve a
convertirse a `DATE`. Por ello se incluyen los días intermedios sin ventas y no
se generan días fuera de los límites autorizados.

Si las dos fuentes carecen de fechas válidas, ambos límites son `NULL` y la
serie no produce filas. No se crea un calendario de respaldo ni se inventan
fechas.

La materialización `VIEW` mantiene el calendario derivado de las fuentes y
evita persistir una tabla adicional en esta implementación.

## Columnas

| Columna | Tipo | Definición |
| --- | --- | --- |
| `fecha` | `DATE` | Clave natural y día calendario. |
| `anio` | `INTEGER` | Año gregoriano de `fecha`. |
| `anio_iso` | `INTEGER` | Año ISO-8601 de la semana de `fecha`. |
| `trimestre` | `SMALLINT` | Trimestre gregoriano, 1 a 4. |
| `mes` | `SMALLINT` | Mes gregoriano, 1 a 12. |
| `dia_mes` | `SMALLINT` | Día del mes. |
| `dia_semana` | `SMALLINT` | Día ISO: lunes 1 a domingo 7. |
| `numero_semana` | `SMALLINT` | Semana ISO-8601. |
| `inicio_mes` | `DATE` | Primer día del mes gregoriano. |
| `fin_mes` | `DATE` | Último día del mes gregoriano. |
| `inicio_trimestre` | `DATE` | Primer día del trimestre gregoriano. |
| `inicio_anio` | `DATE` | Primer día del año gregoriano. |
| `es_fin_semana` | `BOOLEAN` | `TRUE` para ISO 6 y 7; `FALSE` para ISO 1 a 5. |

`anio` y `anio_iso` pueden diferir en los días cercanos al cambio de año:
`anio` usa el año gregoriano de la fecha, mientras `anio_iso` usa el año de
la semana ISO. La semana ISO comienza en lunes y la primera semana es la que
contiene el primer jueves del año ISO.

El campo `periodo` mensual se interpreta como el primer día de su mes. No se
expande cada registro mensual como si fuera observación diaria.

## Relaciones y limitaciones

`fct_ventas_detalle.fecha` puede relacionarse con `dim_fecha.fecha`; la
dimensión también puede usarse en consultas que necesiten mostrar días sin
ventas. No se agrega una relación inversa obligatoria desde la dimensión hacia
el hecho.

El rango no usa devoluciones ni `int_devoluciones_enriquecida`, por lo que una
devolución fuera del rango de ventas no amplía la cobertura. Tampoco usa
snapshots de inventario, fechas de corte, vencimientos ni fechas futuras de
vencimiento. Las fechas técnicas `_etl_*` quedan excluidas. No se implementan
feriados, días hábiles, nombres localizados ni calendarios fiscales.

## Ejecución y validación real

Validación completada el **14 de octubre de 2026**.

### Entorno

- dbt Core: `1.11.12`.
- dbt-postgres: `1.10.2`.
- Base de datos: `sgfood_dw`.
- Rol ejecutor: `sgfood_dbt_runner`.
- Relación: `marts.dim_fecha`.
- Materialización: `VIEW`.
- Grano: una fila por día calendario.
- Clave natural: `fecha DATE`.

### Ejecución dbt

- `dbt parse --no-partial-parse`: aprobado.
- Modelos dbt declarados: 20.
- Fuentes declaradas: 12.
- Tests dbt declarados: 188.
- `dbt run --select dim_fecha`: PASS=1, ERROR=0.
- Tests específicos del bloque: PASS=21, ERROR=0.
- Tests genéricos: 13 `not_null` y un `unique`.
- Tests singulares: siete.
- El fixture `dim_fecha_iso_bisiesto` se ejecutó explícitamente,
  porque no depende directamente de `dim_fecha` en el grafo dbt.
- Suite Python: 91 pruebas aprobadas en la fase estática.

Los 188 tests son el inventario declarado del proyecto.
No se afirma que los 188 hayan sido ejecutados juntos.

### Reconciliación PostgreSQL independiente

Se utilizó el rol `sgfood_dbt_runner` y una transacción
`REPEATABLE READ, READ ONLY`.

| Comprobación | Resultado |
| --- | ---: |
| Fecha mínima | 2026-01-01 |
| Fecha máxima | 2026-08-31 |
| Días calendario | 243 |
| Claves DATE únicas | 243 |
| Columnas con tipos correctos | 13 |
| Campos NULL | 0 |
| Diferencias EXCEPT ALL bidireccionales | 0 |
| Días faltantes o adicionales | 0 |
| Atributos derivados inconsistentes | 0 |
| Ventas sin fecha calendario | 0 |
| Detalles de ventas preservados | 3,209 |
| Cantidad registrada preservada | 19,174 |
| Subtotal registrado preservado | 838,452.07 |
| Grupos mensuales por sucursal | 48 |
| Períodos mensuales sin correspondencia | 0 |

Se comprobaron también las convenciones ISO y el tratamiento
de años bisiestos mediante fixtures deterministas.

Las relaciones con ventas y períodos mensuales no produjeron
multiplicación de registros. Se preservaron `fct_ventas_detalle`,
`dim_sucursal`, `dim_producto` y las cuatro vistas `intermediate`.

Los conteos corresponden al lote académico de esta validación.
No representan límites permanentes del calendario.

### Evidencias

- `resultados/31-dbt-marts-dim-fecha-run.txt`.
- `resultados/32-dbt-marts-dim-fecha-tests.txt`.
- `resultados/33-validacion-marts-dim-fecha-independiente.txt`.

## Limitaciones y próximos pasos

El calendario deriva su rango de las fechas de ventas y
los períodos mensuales autorizados.

No garantiza cobertura de devoluciones, inventarios,
vencimientos ni otras fechas comerciales que estén fuera
de dicho rango.

No utiliza fechas técnicas ETL ni implementa calendarios
fiscales, feriados o historización artificial.

Continúan pendientes otros componentes analíticos,
la orquestación y la validación integral del pipeline ELT.
