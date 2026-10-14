with origen as (
    select
        count(*) as row_count,
        count(distinct id_sucursal) as distinct_key_count
    from {{ ref('stg_oltp_sucursal') }}
), dimension as (
    select
        count(*) as row_count,
        count(distinct id_sucursal) as distinct_key_count
    from {{ ref('dim_sucursal') }}
)
select
    origen.row_count as origen_row_count,
    dimension.row_count as dimension_row_count,
    origen.distinct_key_count as origen_distinct_key_count,
    dimension.distinct_key_count as dimension_distinct_key_count
from origen
cross join dimension
where origen.row_count is distinct from dimension.row_count
   or origen.distinct_key_count is distinct from dimension.distinct_key_count
