# Bloque 2B2D — intermediate de devoluciones

Estado: **MODELO IMPLEMENTADO Y VALIDADO EN POSTGRESQL** (13 de octubre de 2026).

## Objetivo y grano

`int_devoluciones_enriquecida` conserva una fila por `id_devolucion`. La
fuente conductora es `stg_csv_devoluciones`, con la devolución como unidad
de análisis. El conteo académico esperado del lote revisado es **80**; es una
referencia del lote académico, no una restricción permanente del sistema.

## Relaciones autorizadas

El modelo usa exactamente dos enriquecimientos mediante `LEFT JOIN`:

- `stg_oltp_venta`, por `id_venta`, para `fecha` como `fecha_venta`,
  `id_cliente`, `id_sucursal`, `canal`, `metodo_pago` y `estado`.
- `stg_oltp_producto`, por `id_producto`, para `sku`, `nombre` como
  `nombre_producto`, `id_categoria`, `id_marca` y `unidad_medida`.

Las claves de venta y producto son únicas en sus contratos staging, por lo
que no se introduce un fanout conocido. La prueba de enriquecimiento debe
confirmar la correspondencia y la cardinalidad después de construir la vista.

## Columnas y preservación

Se conservan sin alteración las seis columnas originales: `id_devolucion`,
`fecha`, `id_venta`, `id_producto`, `cantidad` y `motivo`. También se
conservan los cinco metadatos del CSV: `_etl_load_id`, `_etl_loaded_at`,
`_etl_source_name`, `_etl_source_sha256` y `_etl_row_number`.

`fecha` mantiene el significado y nombre de fecha de devolución; la fecha de
venta se expone separadamente como `fecha_venta`. No se normaliza `motivo`, no
se reemplazan nulos y no se filtra por fecha, motivo o estado.

## Diferencia frente al detalle de venta

Una devolución se identifica por `id_devolucion` y proviene del CSV de
devoluciones. No se une con `venta_detalle`, no se introduce `id_detalle` y
no se asume que (`id_venta`, `id_producto`) sea único. Por ello, puede haber
múltiples devoluciones para una misma combinación de venta y producto; esa
condición no es una invariante aprobada del modelo.

No se calculan importes, reembolsos, ventas netas, porcentajes ni indicadores
comerciales: el alcance es preservar el hecho original y añadir atributos
descriptivos de sus padres. La efectividad económica de una devolución y su
relación con cantidades vendidas requieren reglas comerciales posteriores.

## Tests definidos

- `int_devoluciones_reconciliacion.sql` compara dinámicamente `COUNT(*)` y
  `SUM(cantidad)` entre staging e intermediate con `IS DISTINCT FROM`; no
  fija el conteo 80.
- `int_devoluciones_integridad_origen.sql` usa `EXCEPT ALL` en ambas
  direcciones sobre las seis columnas funcionales y cinco metadatos. Detecta
  faltantes, adicionales, alteraciones, nulos y duplicaciones.
- `int_devoluciones_integridad_enriquecimiento.sql` reconstruye el
  enriquecimiento desde venta y producto y compara todos sus atributos con
  semántica NULL-safe; también detecta filas faltantes o adicionales.
- `schema.yml` declara grano, clave, relaciones y no nulidad sustentada por
  el DDL y los contratos staging.
- `tests/test_dbt_returns_intermediate_contract.py` comprueba estáticamente
  las referencias, joins, preservación, restricciones y tests.

## Riesgos y limitaciones comerciales

La multiplicidad futura de venta o producto podría multiplicar devoluciones;
debe verificarse la unicidad de las claves padre antes de la ejecución real.
No se aprueban todavía reglas sobre fecha de devolución frente a fecha de
venta, cantidad devuelta frente a cantidad vendida, estado de venta,
reembolsos, descuentos o ventas netas. Esos temas pueden estudiarse como
diagnósticos, pero no son invariantes bloqueantes de este modelo.

## Ejecución y validación real

Validación completada el **13 de octubre de 2026**.

### Entorno y construcción

- dbt Core: `1.11.12`.
- dbt-postgres: `1.10.2`.
- Base de datos: `sgfood_dw`.
- Rol: `sgfood_dbt_runner`.
- Materialización: `VIEW` en `intermediate`.
- `dbt parse`: aprobado; 15 modelos y 101 tests declarados.
- `dbt run --select int_devoluciones_enriquecida`:
  PASS=1, ERROR=0.
- `dbt test --select int_devoluciones_enriquecida`:
  PASS=28, ERROR=0.
- Pruebas Python: 52 aprobadas.

Los 28 tests comprenden 25 pruebas genéricas y tres singulares:
reconciliación, integridad de origen e integridad de enriquecimiento.

### Validación independiente PostgreSQL

Ejecutada mediante el rol `sgfood_dbt_runner` en una
transacción de solo lectura.

Resultados del lote académico:

- 80 devoluciones.
- 80 identificadores `id_devolucion` únicos.
- Suma de cantidades devueltas: 149 unidades.
- Igualdad bidireccional de las 11 columnas originales.
- Atributos enriquecidos de venta y producto correctos.
- Sin pérdidas de filas ni fanout.
- 80 pares `(id_venta, id_producto)` distintos.
- Exactamente tres vistas en `intermediate`, con propietarios correctos.
- Modelos anteriores de ventas e inventario preservados.

El conteo de 80 y la suma de 149 unidades describen el
lote validado, sin constituir restricciones permanentes.
La unicidad de `(id_venta, id_producto)` tampoco se impone
como regla para futuras devoluciones.

### Evidencias

- `resultados/16-dbt-devoluciones-run.txt`.
- `resultados/17-dbt-devoluciones-tests.txt`.
- `resultados/18-validacion-devoluciones-independiente.txt`.

### Limitaciones de negocio

No se calcula importe de devolución ni ventas netas.
El origen no registra el importe efectivamente reembolsado
ni un estado que permita establecer la efectividad económica
de una devolución.

La correspondencia con el detalle de venta continúa
pendiente de reglas y garantías adicionales de cardinalidad.

### Pendientes generales

- Otros modelos intermediate que resulten necesarios.
- Modelos marts.
- Integración con Airflow.
- Validación integral del ELT.
