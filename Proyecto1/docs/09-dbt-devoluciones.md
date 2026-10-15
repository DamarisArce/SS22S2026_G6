# Devoluciones — `int_devoluciones_enriquecida`

## Propósito y granularidad

[`int_devoluciones_enriquecida`](../dbt/models/intermediate/int_devoluciones_enriquecida.sql) representa **una devolución por `id_devolucion`**. Parte de `stg_csv_devoluciones` y agrega información de la venta y el producto mediante relaciones de referencia a staging, sin adjudicar cada devolución a una línea concreta del hecho de ventas.

## Datos y enriquecimiento

Se preservan fecha de devolución, venta, producto, cantidad, motivo y metadatos de fuente. Desde la cabecera se incorporan fecha de venta, cliente, sucursal, canal, método de pago y estado; desde producto se añaden SKU, nombre, categoría, marca y unidad de medida. Las uniones son `LEFT JOIN` contra padres únicos para conservar el grano de devolución.

Las pruebas verifican claves no nulas y únicas, relaciones hacia venta/producto y ausencia de multiplicación de registros. El archivo académico contiene **80 registros** de devoluciones. El modelo mantiene las medidas originales sin restarlas automáticamente a `fct_ventas_detalle`.

## Interpretación de negocio

El enunciado no determina si una devolución debe reducir ventas netas, en qué fecha registrar su impacto ni cómo asignarla cuando una venta contiene varias líneas del mismo producto. Por ello el dato permanece separado: cualquier indicador de ventas netas requeriría reglas explícitas de negocio y un modelo que garantice cardinalidad.

## Evidencias

- [Construcción](../resultados/16-dbt-devoluciones-run.txt).
- [Pruebas de calidad](../resultados/17-dbt-devoluciones-tests.txt).
- [Validación PostgreSQL independiente](../resultados/18-validacion-devoluciones-independiente.txt).
- [Contrato dbt](../dbt/models/intermediate/schema.yml).
