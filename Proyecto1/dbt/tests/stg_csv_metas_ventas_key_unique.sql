select periodo, id_sucursal, count(*) as duplicate_count
from {{ ref('stg_csv_metas_ventas') }}
group by periodo, id_sucursal
having count(*) > 1
