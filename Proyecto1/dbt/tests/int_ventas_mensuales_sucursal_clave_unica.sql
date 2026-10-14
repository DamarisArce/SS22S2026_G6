select
    periodo,
    id_sucursal,
    count(*) as duplicate_count
from {{ ref('int_ventas_mensuales_sucursal') }}
group by periodo, id_sucursal
having count(*) > 1
