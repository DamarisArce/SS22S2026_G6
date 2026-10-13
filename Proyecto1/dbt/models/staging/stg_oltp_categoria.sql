select
    id_categoria,
    nombre,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_table,
    _etl_extracted_at
from {{ source('raw', 'oltp_categoria') }}
