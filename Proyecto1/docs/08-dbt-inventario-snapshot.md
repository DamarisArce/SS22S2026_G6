# Bloque 2B2C — modelo intermediate de inventario histórico

Estado: **MODELO IMPLEMENTADO Y VALIDADO EN POSTGRESQL** (13 de octubre de 2026).

## Objetivo y grano

`int_inventario_snapshot` conserva el inventario histórico sin convertirlo en existencias actuales. Su grano obligatorio es exactamente una fila por:

`fecha_corte + id_sucursal + id_producto + lote`.

La fuente conductora es `stg_csv_inventario_bodega`. El conteo académico esperado para el lote revisado es **3,840 filas**: ocho cortes por 480 registros. Este valor documenta el lote de referencia y no se codifica como condición permanente del modelo ni de la reconciliación.

## Fuentes y enriquecimiento

El modelo usa exclusivamente tres modelos staging:

- `stg_csv_inventario_bodega`: fuente conductora, con stocks, vencimiento y metadatos técnicos del archivo.
- `stg_oltp_producto`: `LEFT JOIN` por `id_producto`, para `sku` y `nombre_producto`.
- `stg_oltp_sucursal`: `LEFT JOIN` por `id_sucursal`, para `nombre_sucursal`.

Los `LEFT JOIN` permiten conservar una fila del inventario si falta un registro padre; las relaciones y los atributos obligatorios de los padres se controlan mediante el contrato dbt. No se incorporan proveedores, precios, ventas, devoluciones, promociones ni otras fuentes que puedan introducir fanout.

## Snapshot histórico y columnas

Un snapshot es la fotografía del inventario en una `fecha_corte`; cada corte es una observación independiente. Por ello, no se suman snapshots de fechas distintas ni se calculan existencias actuales.

Se conservan sin sustitución `stock_disponible`, `stock_minimo`, `stock_maximo` y `fecha_vencimiento`. También se conservan `_etl_load_id`, `_etl_loaded_at`, `_etl_source_name`, `_etl_source_sha256` y `_etl_row_number` para trazabilidad hasta el archivo cargado.

La clave compuesta se documenta y se prueba con un test singular de duplicados. Los stocks permanecen en el grano original: no se agrupan lotes, sucursales, productos ni cortes y no se aplican reglas comerciales sobre mínimos o máximos.

## Reglas de vencimiento

`es_vencido_en_corte` es `TRUE` únicamente cuando `fecha_vencimiento < fecha_corte`; si la fecha de vencimiento es `NULL`, el resultado es `NULL`. Un vencimiento en el mismo día del corte produce `FALSE`.

`dias_para_vencer` se calcula como `fecha_vencimiento - fecha_corte`. Admite valores negativos, produce cero en la misma fecha y queda `NULL` cuando la fecha de vencimiento es desconocida. Estas reglas son históricas y no usan `CURRENT_DATE` ni `NOW()`.

No se agrega `proximo_a_vencer`: su horizonte temporal aún no está definido. “Vencido en corte” y “próximo a vencer” son conceptos distintos y el segundo requiere una regla de negocio aprobada.

## Tests definidos

- `int_inventario_snapshot_clave_unica.sql`: detecta duplicados en la clave compuesta.
- `int_inventario_snapshot_reconciliacion.sql`: compara dinámicamente conteo y sumas de los tres stocks entre staging e intermediate con semántica NULL-safe; solo devuelve diferencias.
- `int_inventario_snapshot_integridad_origen.sql`: comparación bidireccional por la clave compuesta para faltantes, adicionales, stocks, vencimiento y metadatos técnicos; usa `IS DISTINCT FROM`.
- `int_inventario_snapshot_vencimiento.sql`: recalcula de forma independiente las dos derivaciones, incluyendo fechas NULL y vencimiento en el mismo día del corte.

El esquema agrega no nulidad para las cuatro partes de la clave, relaciones de producto y sucursal, y no nulidad para `sku`, `nombre_producto` y `nombre_sucursal`, porque el DDL de sus tablas padre los declara obligatorios.

## Relación con ventas

El modelo de ventas existente, `int_venta_detalle_enriquecida`, conserva una fila por `id_detalle` y sus medidas originales. Inventario histórico es un modelo independiente: no se une a ventas, no atribuye precios, costos o ventas a lotes y no modifica el contrato ni las pruebas SQL de ventas.

## Ejecución y validación real

La validación se completó el **13 de octubre de 2026**.

### Entorno y ejecución

- dbt Core: `1.11.12`.
- dbt-postgres: `1.10.2`.
- Base de datos: `sgfood_dw`.
- Rol: `sgfood_dbt_runner`.
- Materialización: `VIEW` en `intermediate`.
- `dbt parse`: aprobado; 14 modelos y 73 tests declarados.
- `dbt run --select int_inventario_snapshot`: PASS=1, ERROR=0.
- `dbt test --select int_inventario_snapshot`: PASS=13, ERROR=0.
- Pruebas Python del proyecto: 44 aprobadas.

Los 13 tests de inventario incluyen cuatro pruebas singulares:
unicidad de clave compuesta, reconciliación, integridad del origen
y derivaciones de vencimiento.

### Reconciliación independiente

Comprobación realizada mediante PostgreSQL en una transacción
de solo lectura, con resultados:

- 3,840 filas y 3,840 claves compuestas únicas.
- Ocho cortes históricos, cada uno con 480 registros.
- Suma de `stock_disponible`: 179,654.
- Suma de `stock_minimo`: 63,228.
- Suma de `stock_maximo`: 311,724.
- Igualdad bidireccional de las 13 columnas originales
  entre staging e intermediate.
- Enriquecimiento de producto y sucursal sin fanout.
- Exactamente dos vistas intermediate, con propietario correcto.
- Modelo de ventas existente preservado y reconciliado.

Las sumas de stocks se utilizan exclusivamente para verificar
la conservación de los datos entre capas. No representan
existencias actuales, pues incluyen diferentes fechas de corte.

### Distribución de vencimientos del lote validado

- Vencimiento desconocido: 0 registros.
- Vencidos antes del corte: 0 registros.
- Vencimiento igual a fecha de corte: 0 registros.
- Vencimiento posterior al corte: 3,840 registros.

La implementación contempla fechas nulas, vencimientos anteriores
y vencimientos en el mismo día, pero el lote académico actual no
contiene esos casos. La ejecución real no demuestra todavía su
comportamiento con datos representativos de esos escenarios.

### Evidencias

- `resultados/13-dbt-inventario-snapshot-run.txt`.
- `resultados/14-dbt-inventario-snapshot-tests.txt`.
- `resultados/15-validacion-inventario-snapshot-independiente.txt`.

### Pendientes generales

Permanecen pendientes otros modelos intermediate, marts,
integración con Airflow y validación integral del ELT.

Este bloque no establece reglas comerciales adicionales sobre
existencias actuales, ventas, costos o próximos vencimientos.
