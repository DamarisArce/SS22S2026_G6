select
    id_producto,
    count(*) as duplicate_count
from {{ ref('dim_producto') }}
group by id_producto
having count(*) > 1
