select
    fecha,
    count(*) as repeticiones
from {{ ref('dim_fecha') }}
group by fecha
having count(*) > 1
