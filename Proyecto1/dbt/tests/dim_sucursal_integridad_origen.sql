with origen as (
    select
        id_sucursal,
        nombre,
        ciudad,
        departamento,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_table,
        _etl_extracted_at
    from {{ ref('stg_oltp_sucursal') }}
), dimension as (
    select
        id_sucursal,
        nombre,
        ciudad,
        departamento,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_table,
        _etl_extracted_at
    from {{ ref('dim_sucursal') }}
), origen_minus_dimension as (
    select
        id_sucursal,
        nombre,
        ciudad,
        departamento,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_table,
        _etl_extracted_at
    from origen
    except all
    select
        id_sucursal,
        nombre,
        ciudad,
        departamento,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_table,
        _etl_extracted_at
    from dimension
), dimension_minus_origen as (
    select
        id_sucursal,
        nombre,
        ciudad,
        departamento,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_table,
        _etl_extracted_at
    from dimension
    except all
    select
        id_sucursal,
        nombre,
        ciudad,
        departamento,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_table,
        _etl_extracted_at
    from origen
)
select 'origen_minus_dimension' as violation_direction, difference.*
from origen_minus_dimension as difference
union all
select 'dimension_minus_origen' as violation_direction, difference.*
from dimension_minus_origen as difference
