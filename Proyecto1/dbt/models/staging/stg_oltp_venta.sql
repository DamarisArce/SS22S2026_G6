select
    id_venta,
    fecha,
    id_cliente,
    id_sucursal,
    canal,
    metodo_pago,
    estado,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_table,
    _etl_extracted_at
from {{ source('raw', 'oltp_venta') }}
