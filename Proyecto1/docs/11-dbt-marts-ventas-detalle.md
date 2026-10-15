# Hecho de ventas — `marts.fct_ventas_detalle`

## Propósito dimensional

La vista [`marts.fct_ventas_detalle`](../dbt/models/marts/fct_ventas_detalle.sql) es el hecho central del Data Warehouse SG-Food. Su **grano es una fila por `id_detalle`** de `oltp_sgfood.venta_detalle`. Se alimenta exclusivamente de [`int_venta_detalle_enriquecida`](../dbt/models/intermediate/int_venta_detalle_enriquecida.sql), evitando uniones adicionales que podrían multiplicar filas.

![Modelo dimensional de ventas](diagramas/03-modelo-dimensional.svg)

[Diagrama editable draw.io](diagramas/03-modelo-dimensional.drawio)

## Claves, medidas y linaje

| Columnas | Función |
|---|---|
| `id_detalle` | Identificador natural de la línea de venta; clave lógica del hecho |
| `id_venta` | Referencia a la cabecera OLTP; no es dimensión independiente en el mart |
| `id_producto` | Relación lógica con `dim_producto` |
| `id_cliente` | Relación lógica con `dim_cliente` a través de la cabecera |
| `id_sucursal` | Relación lógica con `dim_sucursal` a través de la cabecera |
| `fecha` | Relación lógica con `dim_fecha` |
| `cantidad` | Cantidad registrada en origen |
| `precio_unitario`, `descuento`, `subtotal` | Valores monetarios originales, sin recálculo comercial |
| `_etl_load_id`, `_etl_loaded_at`, `_etl_source_table`, `_etl_extracted_at` | Linaje técnico de carga |

La vista publica **14 columnas**. Las dimensiones se relacionan de manera lógica; los tests dbt comprueban no nulidad, unicidad, integridad de relaciones y preservación de medidas. Al tratarse de una vista PostgreSQL, **no existen PK/FK físicas** declaradas sobre el objeto.

## Verificación independiente

| Control sobre conjunto validado | Resultado |
|---|---:|
| Filas de detalle | 3,209 |
| Identificadores `id_detalle` únicos | 3,209 |
| Unidades registradas | 19,174 |
| Subtotal registrado | 838,452.07 |
| Diferencias bidireccionales con la fuente enriquecida | 0 |

No se mezclan inventario, devoluciones, metas ni promociones en el grano del hecho. Esto evita cambiar el total de líneas por relaciones uno-a-muchos no definidas.

## Evidencias

- [Construcción del hecho](../resultados/22-dbt-marts-ventas-detalle-run.txt).
- [Pruebas dbt](../resultados/23-dbt-marts-ventas-detalle-tests.txt).
- [Validación independiente](../resultados/24-validacion-marts-ventas-detalle-independiente.txt).
- [Definiciones y tests del mart](../dbt/models/marts/schema.yml).
