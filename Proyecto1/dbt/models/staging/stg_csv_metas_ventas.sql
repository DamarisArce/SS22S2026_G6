select
    case
        when nullif(btrim(periodo), '') is null then null
        else (btrim(periodo) || '-01')::date
    end as periodo,
    nullif(btrim(id_sucursal), '')::integer as id_sucursal,
    nullif(btrim(meta_ventas), '')::numeric as meta_ventas,
    nullif(btrim(meta_unidades), '')::numeric as meta_unidades,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_name,
    _etl_source_sha256,
    _etl_row_number
from {{ source('raw', 'csv_metas_ventas') }}
