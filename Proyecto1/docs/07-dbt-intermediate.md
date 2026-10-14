# Bloque 2B2B — primer modelo intermediate

Estado: **MODELO IMPLEMENTADO Y VALIDADO EN POSTGRESQL** (13 de octubre de 2026).

## Objetivo y grano

`int_venta_detalle_enriquecida` conserva la granularidad de `venta_detalle`: una fila por `id_detalle`. Enriquece cada línea con atributos de su venta y producto padre sin alterar `cantidad`, `precio_unitario`, `descuento` ni `subtotal`.

El lote académico original contiene **3,209 líneas de detalle**. Ese conteo es una referencia esperada para auditoría del lote, no una condición permanente de las pruebas.

## Fuentes y joins

El modelo usa exclusivamente estos modelos staging:

- `stg_oltp_venta_detalle`, tabla conductora.
- `stg_oltp_venta`, unido con `LEFT JOIN` por `id_venta`.
- `stg_oltp_producto`, unido con `LEFT JOIN` por `id_producto`.

Los `LEFT JOIN` conservan el detalle aunque falte un padre. Las relaciones, las claves y los atributos no nulos de los padres se comprueban mediante tests dbt para hacer visible una correspondencia faltante.

## Columnas de salida

Se proyectan explícitamente:

- Del detalle: `id_detalle`, `id_venta`, `id_producto`, `cantidad`, `precio_unitario`, `descuento`, `subtotal`.
- De venta: `fecha`, `id_cliente`, `id_sucursal`, `canal`, `metodo_pago`, `estado`.
- De producto: `sku`, `nombre` como `nombre_producto`, `id_categoria`, `id_marca`, `unidad_medida`.
- Metadatos técnicos únicamente del detalle: `_etl_load_id`, `_etl_loaded_at`, `_etl_source_table`, `_etl_extracted_at`.

No se usa `SELECT *`, no se recalcula ni sobrescribe `subtotal`, no se derivan descuentos y no se agregan filas.

## Riesgos de fanout

El riesgo principal es multiplicar una línea si alguno de los padres deja de ser único. Las pruebas `unique` de `id_detalle` y las relaciones de `id_venta`/`id_producto` controlan el contrato; la validación de ejecución debe confirmar además los conteos y sumas. No se unen fuentes de grano múltiple.

## Decisiones comerciales no implementadas

Este modelo no filtra por estado, canal o fecha y no calcula ventas netas oficiales. No une devoluciones, inventario, metas, proveedores ni promociones. Tampoco resuelve qué estados o canales participan en indicadores, cómo se aplican devoluciones o promociones, ni qué medida monetaria oficial debe usarse; esas decisiones permanecen abiertas.

## Pruebas definidas

- En `schema.yml`: `not_null` y `unique` para `id_detalle`; relaciones con venta y producto usando `arguments`; presencia de atributos de padres declarados no nulos.
- `int_venta_detalle_reconciliacion.sql`: reconciliación dinámica de número de líneas, `SUM(cantidad)` y `SUM(subtotal)` entre staging e intermediate; devuelve filas solo ante diferencias.
- `int_venta_detalle_integridad_origen.sql`: comparación bidireccional por `id_detalle` de las siete columnas originales; devuelve filas solo ante faltantes o diferencias.
- `tests/test_dbt_intermediate_contract.py`: contrato estático del único modelo, referencias autorizadas, ausencia de fanout y filtros, preservación de medidas, configuración y pruebas.

## Ejecución y validación real

Validación realizada el **13 de octubre de 2026**.

Entorno:
- dbt Core `1.11.12`.
- dbt-postgres `1.10.2`.
- Base de datos `sgfood_dw`.
- Rol `sgfood_dbt_runner`.
- Esquema `intermediate`.

Resultados:
- `dbt parse`: aprobado; 13 modelos y 60 tests activos.
- `dbt run`: una vista creada; PASS=1, WARN=0, ERROR=0.
- `dbt test`: 19 pruebas aprobadas; WARN=0, ERROR=0.
- Pruebas Python del proyecto: 34 aprobadas.
- Vista verificada como único objeto del esquema intermediate.
- Propietario verificado: `sgfood_dbt_runner`.
- 3,209 líneas; `id_detalle` único.
- Total de unidades: 19,174.
- Suma del subtotal original: 838,452.07.
- Conteos y medidas idénticos entre raw, staging e intermediate.
- Datos originales y metadatos técnicos preservados.
- Atributos de venta y producto reconciliados.

Las cifras anteriores corresponden al lote académico validado,
no son restricciones permanentes para cargas futuras.

Evidencias:
- `resultados/10-dbt-intermediate-venta-run.txt`.
- `resultados/11-dbt-intermediate-venta-tests.txt`.
- `resultados/12-validacion-intermediate-venta-independiente.txt`.

## Pendientes

- Resto de modelos intermediate.
- Definición e implementación de marts.
- Integración con Airflow.
- Validación integral del ELT.

Este bloque no establece todavía reglas comerciales para
ventas netas, devoluciones, promociones o costos.
