select
    id_sucursal,
    count(*) as duplicate_count
from {{ ref('dim_sucursal') }}
group by id_sucursal
having count(*) > 1
