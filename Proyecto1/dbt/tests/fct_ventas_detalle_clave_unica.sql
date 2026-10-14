select
    id_detalle,
    count(*) as duplicate_count
from {{ ref('fct_ventas_detalle') }}
group by id_detalle
having count(*) > 1
