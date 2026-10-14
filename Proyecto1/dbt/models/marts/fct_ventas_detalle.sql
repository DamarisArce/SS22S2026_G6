{{ config(materialized='view', schema='marts') }}

select
    id_detalle,
    id_venta,
    id_producto,
    id_cliente,
    id_sucursal,
    fecha,
    cantidad,
    precio_unitario,
    descuento,
    subtotal,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_table,
    _etl_extracted_at
from {{ ref('int_venta_detalle_enriquecida') }}
