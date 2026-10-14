{{ config(materialized='view', schema='marts') }}

select
    id_cliente,
    nit,
    nombre,
    tipo_cliente,
    municipio,
    departamento,
    fecha_alta,
    _etl_load_id,
    _etl_loaded_at,
    _etl_source_table,
    _etl_extracted_at
from {{ ref('stg_oltp_cliente') }}
