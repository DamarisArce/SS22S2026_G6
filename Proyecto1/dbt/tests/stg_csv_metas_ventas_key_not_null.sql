select periodo, id_sucursal
from {{ ref('stg_csv_metas_ventas') }}
where periodo is null
   or id_sucursal is null
