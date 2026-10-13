select
    id_detalle,
    id_venta,
    id_producto,
    cantidad,
    precio_unitario,
    descuento,
    subtotal,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_table,
    _etl_extracted_at
from {{ source('raw', 'oltp_venta_detalle') }}
