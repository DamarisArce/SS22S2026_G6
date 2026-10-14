# Bloque 2B2F — ventas mensuales por sucursal

Estado: **IMPLEMENTADO Y VALIDADO EN POSTGRESQL** (13 de octubre de 2026).

## Objetivo analítico

`int_ventas_mensuales_sucursal` prepara una agregación descriptiva de las
ventas registradas por sucursal y mes. Sus medidas describen registros del
sistema; no calculan ventas oficiales, ventas netas, cumplimiento comercial,
ingresos contables, costos ni ganancias.

## Fuente, fecha y grano

La fuente única es `int_venta_detalle_enriquecida`, mediante un único `ref`.
El grano es una fila por `(periodo, id_sucursal)`. `periodo` se deriva como
`date_trunc('month', fecha)::date`, por lo que representa el mes en que se
registró la venta. No depende del reloj actual y no filtra por estado ni canal.

El DDL revisado declara `fecha` como `DATE NOT NULL`, `id_sucursal` como
`INTEGER NOT NULL`, `cantidad` como `INTEGER NOT NULL` y `subtotal` como
`NUMERIC(14,2) NOT NULL`. Por ello, el esquema declara no nulas las cuatro
medidas resultantes y la sucursal, condición verificada mediante las pruebas dbt.

## Medidas

| Columna | Fórmula | Significado |
|---|---|---|
| `lineas_registradas` | `COUNT(*)` | Líneas de detalle registradas en el mes y sucursal. |
| `ventas_distintas_registradas` | `COUNT(DISTINCT id_venta)` | Ventas distintas presentes en esas líneas. |
| `cantidad_registrada` | `SUM(cantidad)` | Cantidad original registrada en las líneas. |
| `subtotal_registrado` | `SUM(subtotal)` | Subtotal original registrado en las líneas. |

No se redondean ni modifican `cantidad` o `subtotal`. Un subtotal registrado
no equivale por sí solo a ingreso oficial: todavía no se han definido reglas
de estados, devoluciones, descuentos efectivos, impuestos, conciliación ni
contabilidad.

## Límites y compatibilidad futura

El modelo no incluye devoluciones, metas, promociones ni precios de
proveedores, y no aplica filtros comerciales. Las devoluciones no reducen
estas medidas. Para comparar posteriormente con metas de ventas, la
agregación mensual por sucursal deja ambos lados en un grano compatible.
Unir metas mensuales directamente al detalle de ventas repite la meta
por cada línea correspondiente. Aunque no necesariamente aumenta el número
de líneas, sumar después las metas repetidas distorsiona el objetivo.
La comparación debe realizarse a un grano mensual–sucursal compatible.

La referencia académica revisada contiene 48 combinaciones de periodo y
sucursal en `metas_ventas.csv` (8 periodos por 6 sucursales). Ese conteo es
descriptivo del lote auditado, no una regla permanente del modelo; la
distribución de ventas se valida dinámicamente contra su fuente.

## Tests definidos

- `int_ventas_mensuales_sucursal_clave_unica.sql` detecta duplicaciones del
  grano `(periodo, id_sucursal)`.
- `int_ventas_mensuales_sucursal_reconciliacion.sql` recalcula desde la fuente
  `COUNT(*)`, `COUNT(DISTINCT id_venta)`, `SUM(cantidad)` y `SUM(subtotal)`.
  Su `FULL OUTER JOIN` detecta grupos faltantes, adicionales, duplicación de
  líneas y alteraciones de las cuatro medidas con comparaciones NULL-safe.
- `int_ventas_mensuales_sucursal_periodo.sql` verifica el primer día del mes
  y que las combinaciones periodo-sucursal coincidan con la fuente, sin fijar
  una cantidad de meses o sucursales.
- `tests/test_dbt_sales_monthly_contract.py` verifica estáticamente el modelo,
  los tests singulares y el esquema.

## Limitaciones comerciales

La implementación no determina ventas oficiales, ventas netas, avance contra
metas, descuentos aplicados, costos, margen, ganancias ni atribución de
promociones. Esas reglas requieren decisiones y fuentes adicionales.

## Ejecución y validación

Validación completada el **13 de octubre de 2026**.

### Entorno y construcción

- dbt Core: `1.11.12`.
- dbt-postgres: `1.10.2`.
- Base de datos: `sgfood_dw`.
- Rol de ejecución: `sgfood_dbt_runner`.
- Destino: `intermediate.int_ventas_mensuales_sucursal`.
- Materialización: `VIEW`.
- `dbt parse`: aprobado; 16 modelos y 111 tests declarados.
- `dbt run --select int_ventas_mensuales_sucursal`:
  PASS=1, ERROR=0.
- `dbt test --select int_ventas_mensuales_sucursal`:
  PASS=10, ERROR=0.
- Suite Python: 60 pruebas aprobadas.

Los 10 tests dbt incluyen siete genéricos y tres singulares:
unicidad de clave, período y reconciliación.

### Validación independiente PostgreSQL

La validación se ejecutó mediante una transacción
`REPEATABLE READ, READ ONLY`.

Resultados del lote académico:

| Métrica | Resultado |
|---|---:|
| Grupos mes–sucursal | 48 |
| Líneas registradas | 3,209 |
| Ventas distintas por mes–sucursal | 1,200 |
| Cantidad registrada | 19,174 |
| Subtotal registrado | 838,452.07 |
| Diferencias bidireccionales | 0 |
| Grupos duplicados | 0 |

Se confirmó la igualdad bidireccional de las seis columnas
del modelo, incluidas las cuatro medidas agregadas.

También se verificó que las cuatro vistas `intermediate`
están presentes y que los modelos anteriores de ventas,
inventario y devoluciones conservan sus medidas.

Los conteos anteriores describen el lote académico validado;
no son restricciones permanentes del modelo.

### Evidencias

- `resultados/19-dbt-ventas-mensuales-run.txt`.
- `resultados/20-dbt-ventas-mensuales-tests.txt`.
- `resultados/21-validacion-ventas-mensuales-independiente.txt`.

### Alcance y pendientes

El modelo contiene medidas descriptivas de ventas registradas.

No determina ventas oficiales, ventas netas, ingresos
contables, descuentos efectivos, cumplimiento de metas,
costos, márgenes ni ganancias.

La comparación comercial con metas y los futuros modelos
`marts` requieren definir las reglas de negocio pertinentes.
