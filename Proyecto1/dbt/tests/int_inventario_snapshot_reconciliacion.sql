with staging as (
    select
        count(*) as row_count,
        coalesce(sum(stock_disponible), 0) as stock_disponible_sum,
        coalesce(sum(stock_minimo), 0) as stock_minimo_sum,
        coalesce(sum(stock_maximo), 0) as stock_maximo_sum
    from {{ ref('stg_csv_inventario_bodega') }}
), intermediate as (
    select
        count(*) as row_count,
        coalesce(sum(stock_disponible), 0) as stock_disponible_sum,
        coalesce(sum(stock_minimo), 0) as stock_minimo_sum,
        coalesce(sum(stock_maximo), 0) as stock_maximo_sum
    from {{ ref('int_inventario_snapshot') }}
)
select
    staging.row_count as staging_row_count,
    intermediate.row_count as intermediate_row_count,
    staging.stock_disponible_sum as staging_stock_disponible_sum,
    intermediate.stock_disponible_sum as intermediate_stock_disponible_sum,
    staging.stock_minimo_sum as staging_stock_minimo_sum,
    intermediate.stock_minimo_sum as intermediate_stock_minimo_sum,
    staging.stock_maximo_sum as staging_stock_maximo_sum,
    intermediate.stock_maximo_sum as intermediate_stock_maximo_sum
from staging
cross join intermediate
where staging.row_count is distinct from intermediate.row_count
   or staging.stock_disponible_sum is distinct from intermediate.stock_disponible_sum
   or staging.stock_minimo_sum is distinct from intermediate.stock_minimo_sum
   or staging.stock_maximo_sum is distinct from intermediate.stock_maximo_sum
