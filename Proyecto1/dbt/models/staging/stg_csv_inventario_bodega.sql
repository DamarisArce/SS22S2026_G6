select
    nullif(btrim(fecha_corte), '')::date as fecha_corte,
    nullif(btrim(id_sucursal), '')::integer as id_sucursal,
    nullif(btrim(id_producto), '')::integer as id_producto,
    nullif(btrim(stock_disponible), '')::numeric as stock_disponible,
    nullif(btrim(stock_minimo), '')::numeric as stock_minimo,
    nullif(btrim(stock_maximo), '')::numeric as stock_maximo,
    nullif(btrim(lote), '') as lote,
    nullif(btrim(fecha_vencimiento), '')::date as fecha_vencimiento,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_name,
    _etl_source_sha256,
    _etl_row_number
from {{ source('raw', 'csv_inventario_bodega') }}
