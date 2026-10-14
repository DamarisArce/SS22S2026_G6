with staging as (
    select
        count(*) as row_count,
        sum(cantidad) as quantity_sum
    from {{ ref('stg_csv_devoluciones') }}
), intermediate as (
    select
        count(*) as row_count,
        sum(cantidad) as quantity_sum
    from {{ ref('int_devoluciones_enriquecida') }}
)
select
    staging.row_count as staging_row_count,
    intermediate.row_count as intermediate_row_count,
    staging.quantity_sum as staging_quantity_sum,
    intermediate.quantity_sum as intermediate_quantity_sum
from staging
cross join intermediate
where staging.row_count is distinct from intermediate.row_count
   or staging.quantity_sum is distinct from intermediate.quantity_sum
