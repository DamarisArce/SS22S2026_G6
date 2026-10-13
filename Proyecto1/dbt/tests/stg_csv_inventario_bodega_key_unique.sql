select fecha_corte, id_sucursal, id_producto, lote, count(*) as duplicate_count
from {{ ref('stg_csv_inventario_bodega') }}
group by fecha_corte, id_sucursal, id_producto, lote
having count(*) > 1
