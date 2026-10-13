select
    nullif(btrim(id_devolucion), '')::bigint as id_devolucion,
    nullif(btrim(fecha), '')::date as fecha,
    nullif(btrim(id_venta), '')::bigint as id_venta,
    nullif(btrim(id_producto), '')::integer as id_producto,
    nullif(btrim(cantidad), '')::numeric as cantidad,
    nullif(btrim(motivo), '') as motivo,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_name,
    _etl_source_sha256,
    _etl_row_number
from {{ source('raw', 'csv_devoluciones') }}
