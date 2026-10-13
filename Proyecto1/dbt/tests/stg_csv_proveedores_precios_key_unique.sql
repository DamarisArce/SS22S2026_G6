select id_proveedor, id_producto, fecha_vigencia, count(*) as duplicate_count
from {{ ref('stg_csv_proveedores_precios') }}
group by id_proveedor, id_producto, fecha_vigencia
having count(*) > 1
