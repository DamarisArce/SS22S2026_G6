select id_proveedor, id_producto, fecha_vigencia
from {{ ref('stg_csv_proveedores_precios') }}
where id_proveedor is null
   or id_producto is null
   or fecha_vigencia is null
