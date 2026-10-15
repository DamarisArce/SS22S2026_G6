# Capa `intermediate` — integración y enriquecimiento

## Función y modelos

La capa intermediate implementa **cuatro vistas** para preparar datos reutilizables. No es una nueva copia del sistema transaccional ni un hecho dimensional final; concentra las relaciones y agregaciones controladas que alimentan el mart y las validaciones auxiliares.

| Modelo | Fuente conductora | Grano conservado | Uso |
|---|---|---|---|
| [`int_venta_detalle_enriquecida`](../dbt/models/intermediate/int_venta_detalle_enriquecida.sql) | `stg_oltp_venta_detalle` | Una fila por `id_detalle` | Detalle con atributos de venta y producto |
| [`int_inventario_snapshot`](../dbt/models/intermediate/int_inventario_snapshot.sql) | `stg_csv_inventario_bodega` | Corte–sucursal–producto–lote | Existencias y vencimiento histórico |
| [`int_devoluciones_enriquecida`](../dbt/models/intermediate/int_devoluciones_enriquecida.sql) | `stg_csv_devoluciones` | Una fila por `id_devolucion` | Devolución con cabecera y producto |
| [`int_ventas_mensuales_sucursal`](../dbt/models/intermediate/int_ventas_mensuales_sucursal.sql) | `int_venta_detalle_enriquecida` | Mes–sucursal | Agregados registrados de ventas |

## Enriquecimiento de detalle de ventas

El detalle se relaciona mediante `LEFT JOIN` con la cabecera `stg_oltp_venta` por `id_venta` y con `stg_oltp_producto` por `id_producto`. Expone fecha, cliente, sucursal, canal, método de pago, estado y atributos del producto, conservando cantidad, precio, descuento y subtotal original. No une inventario, devoluciones ni promociones a ese grano.

Las pruebas de unicidad del detalle y las referencias a entidades padre evitan **fanout**: multiplicar filas al combinar relaciones uno-a-muchos. En la muestra académica se conservaron **3,209 filas**, **19,174 unidades** y **838,452.07** de subtotal registrado, sin diferencias bidireccionales identificadas.

## Relación con marts y modelos complementarios

[`fct_ventas_detalle`](../dbt/models/marts/fct_ventas_detalle.sql) se construye desde el modelo enriquecido, mientras que las dimensiones de cliente, sucursal y producto se derivan de staging. `dim_fecha` construye su calendario a partir de ventas y periodos mensuales. Inventario, devoluciones y agregación mensual permanecen disponibles como modelos intermedios, sin alterar la granularidad de ventas.

## Evidencias

- [Construcción intermediate de ventas](../resultados/10-dbt-intermediate-venta-run.txt).
- [Tests de ventas enriquecidas](../resultados/11-dbt-intermediate-venta-tests.txt).
- [Reconciliación independiente](../resultados/12-validacion-intermediate-venta-independiente.txt).
- [Schema y pruebas](../dbt/models/intermediate/schema.yml).

Los detalles de cada modelo complementario se documentan en [inventario](08-dbt-inventario-snapshot.md), [devoluciones](09-dbt-devoluciones.md) y [ventas mensuales](10-dbt-ventas-mensuales.md).
