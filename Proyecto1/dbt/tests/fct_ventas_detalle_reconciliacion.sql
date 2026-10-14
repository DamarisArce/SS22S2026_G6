with origen as (
    select
        count(*) as row_count,
        count(distinct id_detalle) as distinct_detail_count,
        sum(cantidad) as quantity_sum,
        sum(subtotal) as subtotal_sum
    from {{ ref('int_venta_detalle_enriquecida') }}
), mart as (
    select
        count(*) as row_count,
        count(distinct id_detalle) as distinct_detail_count,
        sum(cantidad) as quantity_sum,
        sum(subtotal) as subtotal_sum
    from {{ ref('fct_ventas_detalle') }}
)
select
    origen.row_count as origen_row_count,
    mart.row_count as mart_row_count,
    origen.distinct_detail_count as origen_distinct_detail_count,
    mart.distinct_detail_count as mart_distinct_detail_count,
    origen.quantity_sum as origen_quantity_sum,
    mart.quantity_sum as mart_quantity_sum,
    origen.subtotal_sum as origen_subtotal_sum,
    mart.subtotal_sum as mart_subtotal_sum
from origen
cross join mart
where origen.row_count is distinct from mart.row_count
   or origen.distinct_detail_count is distinct from mart.distinct_detail_count
   or origen.quantity_sum is distinct from mart.quantity_sum
   or origen.subtotal_sum is distinct from mart.subtotal_sum
