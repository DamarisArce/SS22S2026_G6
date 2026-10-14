select
    fecha_corte,
    id_sucursal,
    id_producto,
    lote,
    count(*) as duplicate_count
from {{ ref('int_inventario_snapshot') }}
group by fecha_corte, id_sucursal, id_producto, lote
having count(*) > 1
