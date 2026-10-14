with staging_without_sales as (
    select cliente.id_cliente
    from {{ ref('stg_oltp_cliente') }} as cliente
    where not exists (
        select 1
        from {{ ref('stg_oltp_venta') }} as venta
        where venta.id_cliente = cliente.id_cliente
    )
), dimension_without_sales as (
    select cliente.id_cliente
    from {{ ref('dim_cliente') }} as cliente
    where not exists (
        select 1
        from {{ ref('stg_oltp_venta') }} as venta
        where venta.id_cliente = cliente.id_cliente
    )
), staging_minus_dimension as (
    select id_cliente from staging_without_sales
    except all
    select id_cliente from dimension_without_sales
), dimension_minus_staging as (
    select id_cliente from dimension_without_sales
    except all
    select id_cliente from staging_without_sales
)
select 'staging_vs_dimension' as violation_direction, difference.id_cliente
from staging_minus_dimension as difference
union all
select 'dimension_vs_staging' as violation_direction, difference.id_cliente
from dimension_minus_staging as difference
