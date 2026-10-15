# Inventario histórico — `int_inventario_snapshot`

## Objetivo y grano

[`int_inventario_snapshot`](../dbt/models/intermediate/int_inventario_snapshot.sql) conforma una vista de inventario por **fecha de corte, sucursal, producto y lote**. El conjunto de referencia incluye **3,840 filas** distribuidas en ocho cortes mensuales, con 480 registros por corte. El modelo es histórico: un lote puede figurar en diferentes fechas sin ser duplicado semántico.

## Transformación aplicada

La vista conserva `fecha_corte`, `id_sucursal`, `id_producto`, `lote`, `stock_disponible`, `stock_minimo`, `stock_maximo` y `fecha_vencimiento`; añade SKU y nombre de producto, nombre de sucursal y metadatos de extracción. Mediante referencias únicas a staging enriquece el inventario sin cambiar su grano.

Se calculan dos campos históricos:

- **`es_vencido_en_corte`**: `fecha_vencimiento < fecha_corte` cuando hay fecha de vencimiento; en caso contrario, `NULL`.
- **`dias_para_vencer`**: diferencia entre vencimiento y fecha de corte, sin utilizar la fecha actual.

Por ello, los 658 registros con vencimiento anterior a `2026-08-31` **no se consideran vencidos automáticamente**: cada registro se evalúa contra su propio corte.

## Controles y resultados

| Control | Resultado de referencia |
|---|---:|
| Filas y claves compuestas únicas | 3,840 |
| Suma `stock_disponible` | 179,654 |
| Suma `stock_minimo` | 63,228 |
| Suma `stock_maximo` | 311,724 |
| Registros con vencimiento posterior a su corte | 3,840 |

Los controles dbt y una reconciliación SQL independiente verificaron unicidad, cobertura de sucursales/productos, preservación y reglas de vencimiento. Evidencias: [run 13](../resultados/13-dbt-inventario-snapshot-run.txt), [tests 14](../resultados/14-dbt-inventario-snapshot-tests.txt), [reconciliación 15](../resultados/15-validacion-inventario-snapshot-independiente.txt).

## Interpretación y restricciones

Los campos de stock se preservan como observaciones operativas, no como movimientos reconstruidos. Los 265 casos observados con stock disponible superior al máximo no son eliminados ni modificados sin una regla de negocio. Este modelo no se incorpora mediante join directo al hecho de ventas, porque los cortes y lotes tienen una cardinalidad incompatible con una línea de venta.
