with staging as (
    select
        fecha_corte,
        id_sucursal,
        id_producto,
        lote,
        stock_disponible,
        stock_minimo,
        stock_maximo,
        fecha_vencimiento,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_name,
        _etl_source_sha256,
        _etl_row_number
    from {{ ref('stg_csv_inventario_bodega') }}
), intermediate as (
    select
        fecha_corte,
        id_sucursal,
        id_producto,
        lote,
        stock_disponible,
        stock_minimo,
        stock_maximo,
        fecha_vencimiento,
        _etl_load_id,
        _etl_loaded_at,
        _etl_source_name,
        _etl_source_sha256,
        _etl_row_number
    from {{ ref('int_inventario_snapshot') }}
)
select
    'staging_vs_intermediate' as violation_direction,
    staging.fecha_corte,
    staging.id_sucursal,
    staging.id_producto,
    staging.lote,
    intermediate.fecha_corte as intermediate_fecha_corte,
    intermediate.id_sucursal as intermediate_id_sucursal,
    intermediate.id_producto as intermediate_id_producto,
    intermediate.lote as intermediate_lote
from staging
full outer join intermediate
    on staging.fecha_corte = intermediate.fecha_corte
   and staging.id_sucursal = intermediate.id_sucursal
   and staging.id_producto = intermediate.id_producto
   and staging.lote = intermediate.lote
where staging.fecha_corte is null
   or intermediate.fecha_corte is null
   or staging.stock_disponible is distinct from intermediate.stock_disponible
   or staging.stock_minimo is distinct from intermediate.stock_minimo
   or staging.stock_maximo is distinct from intermediate.stock_maximo
   or staging.fecha_vencimiento is distinct from intermediate.fecha_vencimiento
   or staging._etl_load_id is distinct from intermediate._etl_load_id
   or staging._etl_loaded_at is distinct from intermediate._etl_loaded_at
   or staging._etl_source_name is distinct from intermediate._etl_source_name
   or staging._etl_source_sha256 is distinct from intermediate._etl_source_sha256
   or staging._etl_row_number is distinct from intermediate._etl_row_number
