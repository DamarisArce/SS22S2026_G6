select
    nullif(btrim(id_promocion), '')::bigint as id_promocion,
    nullif(btrim(nombre), '') as nombre,
    nullif(btrim(fecha_inicio), '')::date as fecha_inicio,
    nullif(btrim(fecha_fin), '')::date as fecha_fin,
    nullif(btrim(id_categoria), '')::integer as id_categoria,
    nullif(btrim(porcentaje_descuento), '')::numeric as porcentaje_descuento,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_name,
    _etl_source_sha256,
    _etl_row_number
from {{ source('raw', 'csv_promociones') }}
