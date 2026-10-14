with staging as (
    select
        count(*) as line_count,
        coalesce(sum(cantidad), 0) as quantity_sum,
        coalesce(sum(subtotal), 0) as subtotal_sum
    from {{ ref('stg_oltp_venta_detalle') }}
), intermediate as (
    select
        count(*) as line_count,
        coalesce(sum(cantidad), 0) as quantity_sum,
        coalesce(sum(subtotal), 0) as subtotal_sum
    from {{ ref('int_venta_detalle_enriquecida') }}
)
select
    staging.line_count as staging_line_count,
    intermediate.line_count as intermediate_line_count,
    staging.quantity_sum as staging_quantity_sum,
    intermediate.quantity_sum as intermediate_quantity_sum,
    staging.subtotal_sum as staging_subtotal_sum,
    intermediate.subtotal_sum as intermediate_subtotal_sum
from staging
cross join intermediate
where staging.line_count <> intermediate.line_count
   or staging.quantity_sum <> intermediate.quantity_sum
   or staging.subtotal_sum <> intermediate.subtotal_sum
