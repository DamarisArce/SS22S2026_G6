select
    nullif(btrim(id_proveedor), '')::bigint as id_proveedor,
    nullif(btrim(proveedor), '') as proveedor,
    nullif(btrim(id_producto), '')::integer as id_producto,
    nullif(btrim(costo_proveedor), '')::numeric as costo_proveedor,
    nullif(btrim(plazo_dias), '')::integer as plazo_dias,
    nullif(btrim(fecha_vigencia), '')::date as fecha_vigencia,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_name,
    _etl_source_sha256,
    _etl_row_number
from {{ source('raw', 'csv_proveedores_precios') }}
