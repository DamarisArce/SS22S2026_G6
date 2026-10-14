with fact as (
    select
        id_detalle,
        id_cliente,
        cantidad,
        subtotal
    from {{ ref('fct_ventas_detalle') }}
), validated_details as (
    select
        fact.id_detalle,
        fact.id_cliente,
        fact.cantidad,
        fact.subtotal,
        count(dimension.id_cliente) as dimension_matches
    from fact
    left join {{ ref('dim_cliente') }} as dimension
        on fact.id_cliente = dimension.id_cliente
    group by fact.id_detalle, fact.id_cliente, fact.cantidad, fact.subtotal
), fact_totals as (
    select
        count(*) as detail_count,
        sum(cantidad) as quantity_sum,
        sum(subtotal) as subtotal_sum
    from fact
), validated_totals as (
    select
        count(*) as detail_count,
        sum(cantidad) as quantity_sum,
        sum(subtotal) as subtotal_sum
    from validated_details
)
select
    validated_details.id_detalle,
    validated_details.id_cliente,
    validated_details.dimension_matches,
    'invalid_client_key_or_fanout' as violation
from validated_details
where validated_details.dimension_matches <> 1
union all
select
    null as id_detalle,
    null as id_cliente,
    null as dimension_matches,
    'fact_totals_changed' as violation
from fact_totals
cross join validated_totals
where fact_totals.detail_count is distinct from validated_totals.detail_count
   or fact_totals.quantity_sum is distinct from validated_totals.quantity_sum
   or fact_totals.subtotal_sum is distinct from validated_totals.subtotal_sum
