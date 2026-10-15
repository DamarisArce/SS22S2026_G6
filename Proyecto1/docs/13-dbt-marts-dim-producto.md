# Dimensión de productos — `marts.dim_producto`

## Definición y grano

[`dim_producto`](../dbt/models/marts/dim_producto.sql) representa **un producto por `id_producto`**, desde `stg_oltp_producto`. Incluye 13 columnas: `id_producto`, `sku`, `nombre`, `id_categoria`, `id_marca`, `unidad_medida`, `costo_base`, `precio_lista`, `activo` y cuatro metadatos técnicos (`_etl_load_id`, `_etl_loaded_at`, `_etl_source_table`, `_etl_extracted_at`). La materialización es una vista.

## Relaciones analíticas

El hecho de ventas referencia `id_producto`; las claves `id_categoria` e `id_marca` se conservan como atributos de origen con sus relaciones comprobadas en staging. El diseño no construye dimensiones de categoría o marca separadas en marts. `costo_base` y `precio_lista` se exponen como atributos registrados, no como una tabla histórica de precios ni como una medida de utilidad neta.

## Integridad del modelo

En el conjunto validado se obtuvieron **80 productos**, **80 claves y SKU únicos**, 13 columnas y ninguna referencia inválida a categoría o marca. La reconciliación con staging no presentó diferencias; el enlace lógico con ventas conservó **3,209 filas**, **19,174 unidades** y **838,452.07** de subtotal original.

Evidencias: [run 28](../resultados/28-dbt-marts-dim-producto-run.txt), [tests 29](../resultados/29-dbt-marts-dim-producto-tests.txt), [reconciliación 30](../resultados/30-validacion-marts-dim-producto-independiente.txt).

## Alcance histórico

No se realizan reconstrucciones de precios anteriores ni historización SCD2. La vista reproduce el estado proporcionado por el origen y el identificador técnico del lote de carga.
