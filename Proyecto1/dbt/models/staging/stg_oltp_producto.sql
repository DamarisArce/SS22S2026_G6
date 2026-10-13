select
    id_producto,
    sku,
    nombre,
    id_categoria,
    id_marca,
    unidad_medida,
    costo_base,
    precio_lista,
    activo,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_table,
    _etl_extracted_at
from {{ source('raw', 'oltp_producto') }}
