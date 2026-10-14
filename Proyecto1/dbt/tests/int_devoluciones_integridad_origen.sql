with staging as (
    select
        id_devolucion,
        fecha,
        id_venta,
        id_producto,
        cantidad,
        motivo,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_name,
        _etl_source_sha256,
        _etl_row_number
    from {{ ref('stg_csv_devoluciones') }}
), intermediate as (
    select
        id_devolucion,
        fecha,
        id_venta,
        id_producto,
        cantidad,
        motivo,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_name,
        _etl_source_sha256,
        _etl_row_number
    from {{ ref('int_devoluciones_enriquecida') }}
), staging_minus_intermediate as (
    select
        id_devolucion,
        fecha,
        id_venta,
        id_producto,
        cantidad,
        motivo,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_name,
        _etl_source_sha256,
        _etl_row_number
    from staging
    except all
    select
        id_devolucion,
        fecha,
        id_venta,
        id_producto,
        cantidad,
        motivo,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_name,
        _etl_source_sha256,
        _etl_row_number
    from intermediate
), intermediate_minus_staging as (
    select
        id_devolucion,
        fecha,
        id_venta,
        id_producto,
        cantidad,
        motivo,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_name,
        _etl_source_sha256,
        _etl_row_number
    from intermediate
    except all
    select
        id_devolucion,
        fecha,
        id_venta,
        id_producto,
        cantidad,
        motivo,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_name,
        _etl_source_sha256,
        _etl_row_number
    from staging
)
select 'staging_vs_intermediate' as violation_direction, difference.*
from staging_minus_intermediate as difference
union all
select 'intermediate_vs_staging' as violation_direction, difference.*
from intermediate_minus_staging as difference
