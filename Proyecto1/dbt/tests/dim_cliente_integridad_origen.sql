with staging as (
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
), dimension as (
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
    from {{ ref('dim_cliente') }}
), staging_minus_dimension as (
    select * from staging
    except all
    select * from dimension
), dimension_minus_staging as (
    select * from dimension
    except all
    select * from staging
)
select 'staging_vs_dimension' as violation_direction, difference.*
from staging_minus_dimension as difference
union all
select 'dimension_vs_staging' as violation_direction, difference.*
from dimension_minus_staging as difference
